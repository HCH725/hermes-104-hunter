"""Data normalizers for 104 search and job detail responses."""

from __future__ import annotations

import re
from typing import Any

from .analysis import extract_job_id
from .models import JobDetail, JobSearchResult


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", str(text))
    return re.sub(r"\s+", " ", clean).strip()


def normalize_search_job(item: dict[str, Any]) -> JobSearchResult:
    """Normalize a raw job entry from 104 search API into JobSearchResult."""
    link_info = item.get("link") or {}
    raw_job_url = link_info.get("job", "")
    raw_job_no = item.get("jobNo")

    # Determine slug
    job_id = ""
    if raw_job_url:
        try:
            job_id = extract_job_id(raw_job_url)
        except ValueError:
            job_id = str(raw_job_no or "")
    elif raw_job_no:
        job_id = str(raw_job_no)

    job_no: int | None = None
    try:
        if raw_job_no:
            job_no = int(raw_job_no)
    except (ValueError, TypeError):
        pass

    title = _strip_html(item.get("jobName", ""))
    company_name = _strip_html(item.get("custName", ""))
    area = _strip_html(item.get("jobAddrNoDesc", ""))
    salary = _strip_html(item.get("salaryDesc", ""))

    salary_low_raw = item.get("salaryLow")
    salary_high_raw = item.get("salaryHigh")
    salary_min: int | None = None
    salary_max: int | None = None
    try:
        if salary_low_raw is not None and int(salary_low_raw) > 0:
            salary_min = int(salary_low_raw)
    except (ValueError, TypeError):
        pass
    try:
        if salary_high_raw is not None and int(salary_high_raw) > 0:
            salary_max = int(salary_high_raw)
    except (ValueError, TypeError):
        pass

    is_negotiable = "面議" in salary or (salary_min is not None and salary_min < 40000 and "面議" in salary)

    # Extract tags (e.g. remote, foreign company)
    tags: list[str] = []
    tags_raw = item.get("tags") or []
    if isinstance(tags_raw, list):
        for t in tags_raw:
            if isinstance(t, dict) and t.get("desc"):
                tags.append(str(t["desc"]).strip())
            elif isinstance(t, str) and t.strip():
                tags.append(t.strip())

    # Check remote work indicator
    remote_work = item.get("remoteWorkType")
    if remote_work in (1, "1", True):
        if "完全遠端" not in tags and "遠端工作" not in tags:
            tags.append("遠端工作")

    url = f"https://www.104.com.tw/job/{job_id}" if job_id else "https://www.104.com.tw"

    return JobSearchResult(
        job_id=job_id,
        job_no=job_no,
        title=title,
        company_name=company_name,
        area=area,
        salary=salary,
        salary_min=salary_min,
        salary_max=salary_max,
        is_negotiable=is_negotiable,
        experience=_strip_html(item.get("periodDesc", "不拘")),
        education=_strip_html(item.get("eduDesc", "不拘")),
        tags=tags,
        update_date=str(item.get("appearDate", "")),
        url=url,
    )


def normalize_job_detail(slug: str, raw_payload: dict[str, Any]) -> JobDetail:
    """Normalize 104 job/ajax/content response into JobDetail."""
    data = raw_payload.get("data") or {}
    header = data.get("header") or {}
    detail = data.get("jobDetail") or {}
    condition = data.get("condition") or {}
    welfare_data = data.get("welfare") or {}
    contact = data.get("contact") or {}

    title = _strip_html(header.get("jobName", ""))
    company_name = _strip_html(header.get("custName", ""))
    analysis_type = header.get("analysisType")
    is_applied = header.get("isApplied")

    job_no: int | None = None
    try:
        raw_job_no = header.get("jobNo")
        if raw_job_no is not None:
            job_no = int(raw_job_no)
    except (ValueError, TypeError):
        pass

    description = _strip_html(detail.get("jobDescription", ""))
    salary = _strip_html(detail.get("salary", ""))
    work_type = _strip_html(detail.get("workTypeDesc", ""))
    location = _strip_html(detail.get("addressRegion", "") + " " + detail.get("addressDetail", ""))

    exp_req = _strip_html(condition.get("workExp", "不拘"))
    edu_req = _strip_html(condition.get("edu", "不拘"))
    other_req = _strip_html(condition.get("other", ""))

    majors: list[str] = [
        str(m.get("major"))
        for m in condition.get("major", [])
        if isinstance(m, dict) and m.get("major")
    ]
    languages: list[str] = [
        f"{l.get('language')}: {l.get('ability', '')}".strip()
        for l in condition.get("language", [])
        if isinstance(l, dict) and l.get("language")
    ]
    skills: list[str] = [
        str(s.get("skill"))
        for s in condition.get("skill", [])
        if isinstance(s, dict) and s.get("skill")
    ]
    certs: list[str] = [
        str(c.get("cert"))
        for c in condition.get("certificate", [])
        if isinstance(c, dict) and c.get("cert")
    ]

    welfare = _strip_html(welfare_data.get("welfare", ""))
    hr_name = contact.get("hrName")

    return JobDetail(
        job_id=slug,
        job_no=job_no,
        title=title,
        company_name=company_name,
        description=description,
        salary=salary,
        work_type=work_type,
        location=location,
        experience_req=exp_req,
        education_req=edu_req,
        major_req=majors,
        language_req=languages,
        skills_req=skills,
        certificates_req=certs,
        other_requirements=other_req,
        welfare=welfare,
        hr_contact=str(hr_name) if hr_name else None,
        is_applied=is_applied,
        analysis_type=int(analysis_type) if analysis_type is not None else None,
        url=f"https://www.104.com.tw/job/{slug}",
    )
