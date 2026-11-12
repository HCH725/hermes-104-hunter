"""Async HTTP client for 104 job search and analysis APIs."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .analysis import extract_job_id, normalize_apply_analysis, slug_to_job_no
from .auth import get_active_cookies
from .config import (
    APPLY_ANALYSIS_API_URL,
    BASE_104,
    DEFAULT_USER_AGENT,
    DETAIL_API_URL,
    SEARCH_API_URL,
    settings,
)
from .models import ApplyAnalysisResult, JobDetail, SearchJobsResponse
from .normalizers import normalize_job_detail, normalize_search_job

logger = logging.getLogger(__name__)

# Common Taiwan area code mappings for 104
AREA_CODES: dict[str, str] = {
    "台北市": "6001001000",
    "新北市": "6001002000",
    "基隆市": "6001003000",
    "宜蘭縣": "6001004000",
    "桃園市": "6001005000",
    "新竹市": "6001006001",
    "新竹縣": "6001006002",
    "新竹": "6001006000",
    "苗栗縣": "6001007000",
    "台中市": "6001008000",
    "彰化縣": "6001009000",
    "南投縣": "6001010000",
    "雲林縣": "6001011000",
    "嘉義市": "6001012001",
    "嘉義縣": "6001012002",
    "台南市": "6001013000",
    "高雄市": "6001014000",
    "屏東縣": "6001015000",
    "台東縣": "6001016000",
    "花蓮縣": "6001017000",
    "澎湖縣": "6001018000",
    "金門縣": "6001019000",
    "連江縣": "6001020000",
}


def resolve_area_code(area_input: str | None) -> str | None:
    if not area_input:
        return None
    area_input = area_input.strip()
    # If already a numeric code
    if area_input.isdigit():
        return area_input
    # Multi-area split by comma
    codes: list[str] = []
    for part in area_input.replace("、", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if part in AREA_CODES:
            codes.append(AREA_CODES[part])
        elif part.isdigit():
            codes.append(part)
        else:
            # Partial match (e.g. '台北' -> '台北市')
            matched = False
            for name, code in AREA_CODES.items():
                if part in name or name in part:
                    codes.append(code)
                    matched = True
                    break
            if not matched:
                logger.warning("未識別的地區名稱: %s", part)
    return ",".join(codes) if codes else None


class Job104Client:
    """High-performance, async client for 104 job search and analysis."""

    def __init__(self, cookies: dict[str, str] | None = None, timeout: float | None = None) -> None:
        self.cookies = cookies if cookies is not None else get_active_cookies()
        self.timeout = timeout or settings.timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            }
            self._client = httpx.AsyncClient(
                headers=headers,
                cookies=self.cookies,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def search_jobs(
        self,
        keyword: str,
        area: str | None = None,
        page: int = 1,
        page_size: int = 20,
        order: int = 1,  # 1 = relevance, 11 = update date
        exclude_negotiable: bool = False,
        min_salary: int | None = None,
        remote_only: bool = False,
    ) -> SearchJobsResponse:
        """Search jobs on 104 with optional fine-grained filtering."""
        client = await self._get_client()
        area_code = resolve_area_code(area)

        params: dict[str, Any] = {
            "keyword": keyword,
            "page": page,
            "pagesize": page_size,
            "mode": "s",
            "jobsource": "joblist_search",
            "searchJobs": 1,
            "order": order,
        }
        if area_code:
            params["area"] = area_code
        if remote_only:
            params["remoteWorkType"] = "1"

        referer = str(httpx.URL(f"{BASE_104}/jobs/search/").copy_merge_params({"keyword": keyword}))
        headers = {"Referer": referer}

        response = await client.get(SEARCH_API_URL, params=params, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"104 搜尋 API 呼叫失敗 (HTTP {response.status_code}): {response.text[:200]}")

        payload = response.json()
        raw_data = payload.get("data") or []
        metadata = payload.get("metadata") or {}
        pagination = metadata.get("pagination") or {}

        total_count = int(pagination.get("total", len(raw_data)))
        total_pages = int(pagination.get("lastPage", 1))

        jobs = [normalize_search_job(item) for item in raw_data]

        # 104's search API does not reliably honour `pagesize`; enforce it ourselves
        # so callers get exactly the batch size they asked for.
        if page_size and len(jobs) > page_size:
            jobs = jobs[:page_size]

        # Apply filters
        if exclude_negotiable:
            jobs = [j for j in jobs if not j.is_negotiable]
        if min_salary is not None:
            # Keep job if its salary_max is >= min_salary or if salary is stated higher
            jobs = [
                j for j in jobs
                if (j.salary_max is not None and j.salary_max >= min_salary)
                or (j.salary_min is not None and j.salary_min >= min_salary)
            ]

        return SearchJobsResponse(
            keyword=keyword,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            jobs=jobs,
        )

    async def get_job_detail(self, job_url_or_id: str) -> JobDetail:
        """Fetch clean job detail for a given 104 job URL or slug."""
        slug = extract_job_id(job_url_or_id)
        client = await self._get_client()

        url = f"{DETAIL_API_URL}/{slug}"
        referer = f"{BASE_104}/job/{slug}"
        headers = {"Referer": referer}

        response = await client.get(url, headers=headers)
        if response.status_code == 404:
            raise ValueError(f"職缺不存在或已下架 (404): {job_url_or_id}")
        elif response.status_code != 200:
            raise RuntimeError(f"獲取職缺詳情失敗 (HTTP {response.status_code}): {response.text[:200]}")

        payload = response.json()
        return normalize_job_detail(slug, payload)

    async def get_apply_analysis(self, job_url_or_id: str) -> ApplyAnalysisResult:
        """Fetch competitor apply analysis and mathematically infer applicant count."""
        slug = extract_job_id(job_url_or_id)
        job_no = slug_to_job_no(slug)
        client = await self._get_client()

        # 1. Fetch job header to get analysisType (range indicator)
        range_code: int | None = None
        try:
            detail_resp = await client.get(
                f"{DETAIL_API_URL}/{slug}",
                headers={"Referer": f"{BASE_104}/job/{slug}"},
            )
            if detail_resp.status_code == 200:
                header = (detail_resp.json().get("data") or {}).get("header") or {}
                raw_analysis_type = header.get("analysisType")
                if raw_analysis_type is not None:
                    range_code = int(raw_analysis_type)
        except Exception as e:
            logger.debug("Could not fetch analysisType header: %s", e)

        # 2. Fetch full apply analysis data
        analysis_url = f"{APPLY_ANALYSIS_API_URL}?job_no={job_no}"
        analysis_referer = f"{BASE_104}/jobs/apply/analysis/{slug}"
        headers = {"Referer": analysis_referer}

        response = await client.get(analysis_url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(
                f"獲取職缺應徵分析失敗 (HTTP {response.status_code}): {response.text[:200]}"
            )

        raw_data = response.json()
        return normalize_apply_analysis(raw_data, slug, job_no, range_code)
