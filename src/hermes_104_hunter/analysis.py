"""Mathematical reverse-engineering and normalization for 104 competitor apply analysis."""

from __future__ import annotations

import math
import re
from typing import Any

from .models import ApplyAnalysisResult, DimensionItem, LanguageItem


def extract_job_id(job_url_or_id: str) -> str:
    """Extract clean job slug from 104 URL or raw slug string."""
    s = str(job_url_or_id).strip()
    # Match /job/([a-zA-Z0-9]+) or /analysis/([a-zA-Z0-9]+)
    m = re.search(r"/(?:job|analysis)/([a-zA-Z0-9]+)", s)
    if m:
        return m.group(1).lower()
    # Strip any leading URL scheme/path and queries
    s = s.split("?")[0].split("#")[0].rstrip("/")
    cleaned = s.split("/")[-1].lower()
    if re.match(r"^[a-z0-9]+$", cleaned):
        return cleaned
    raise ValueError(f"無法解析 104 職缺代碼: {job_url_or_id}")


def slug_to_job_no(slug: str) -> int:
    """Convert base-36 slug (e.g. '8nd15') to decimal job_no (e.g. 14526905)."""
    cleaned = extract_job_id(slug)
    if re.match(r"^\d{7,10}$", cleaned):
        return int(cleaned, 10)
    try:
        return int(cleaned, 36)
    except ValueError as e:
        raise ValueError(f"職缺代碼 '{slug}' 無法轉換為 104 內部編號: {e}")


def parse_apply_range(analysis_type: int | None) -> dict[str, Any]:
    """Parse 104 analysisType code to text label and search bounds."""
    if analysis_type == 1:
        return {"label": "0~5 人", "min": 0, "max": 5}
    elif analysis_type == 2:
        return {"label": "6~10 人", "min": 6, "max": 10}
    elif analysis_type == 3:
        return {"label": "11~30 人", "min": 11, "max": 30}
    elif analysis_type == 4:
        return {"label": "30 人以上", "min": 31, "max": 5000}
    else:
        label = f"未知區間(代碼: {analysis_type})" if analysis_type else "未知區間"
        return {"label": label, "min": 1, "max": 5000}


def fits_percent(percent: float, n: int) -> bool:
    """Check whether integer applicant count n can produce rounded percentage."""
    if n <= 0 or percent <= 0:
        return False
    k = round((percent * n) / 100.0)
    if k < 1 or k > n:
        return False
    return abs((k * 10000.0) / n - percent * 100.0) <= 0.5 + 1e-9


def infer_applicant_count(
    percents: list[float],
    bounds: tuple[int, int] = (1, 5000),
    dimension_groups: list[list[float]] | None = None,
    max_candidates: int = 20,
) -> list[int]:
    """
    Infer exact competitor applicant count n via mathematical constraint solving.
    Evaluates compatibility against all non-zero percentages and mutual-exclusion group sums.
    """
    informative = [p for p in percents if p > 0]
    if not informative:
        return []

    lo = max(1, bounds[0])
    hi = min(5000, bounds[1])
    candidates: list[int] = []

    for n in range(lo, hi + 1):
        if not all(fits_percent(p, n) for p in informative):
            continue

        # Mutual exclusion group verification: if group sum is close to 100%,
        # the sum of rounded integer counts should equal n.
        # ponytail: tolerance of 1 count absorbs 104's 2-decimal rounding drift across
        # categories (an observed group can sum to 100.01%). Tighten to 0 if false
        # positives ever appear; widen only with evidence.
        groups_valid = True
        if dimension_groups:
            for group in dimension_groups:
                if not group:
                    continue
                group_sum = sum(group)
                if abs(group_sum - 100.0) <= 5.0:
                    count_sum = sum(round((p * n) / 100.0) for p in group)
                    if abs(count_sum - n) > 1:
                        groups_valid = False
                        break

        if groups_valid:
            candidates.append(n)
            if len(candidates) >= max_candidates:
                break

    return candidates


def _best_effort_estimate(
    percents: list[float], bounds: tuple[int, int]
) -> tuple[int | None, float]:
    """Return (best n, mean absolute percent error) when no exact solution exists.

    This is a heuristic, never a substitute for a real inferred count.
    """
    informative = [p for p in percents if p > 0]
    if not informative:
        return None, 0.0

    lo = max(1, bounds[0])
    hi = min(5000, bounds[1])
    best_n: int | None = None
    best_err = float("inf")

    for n in range(lo, hi + 1):
        err = sum(
            abs(round(round((p * n) / 100.0) * 10000.0 / n, 2) - p) for p in informative
        ) / len(informative)
        if err < best_err:
            best_err = err
            best_n = n
            if err == 0.0:
                break

    return best_n, best_err


def _extract_items(group: Any, name_key: str) -> list[dict[str, Any]]:
    if not isinstance(group, dict):
        return []
    items: list[dict[str, Any]] = []
    for k, entry in group.items():
        if k in ("update_time", "total"):
            continue
        if isinstance(entry, dict) and entry.get(name_key):
            try:
                pct = float(entry.get("percent", 0) or 0)
                if pct > 0:
                    items.append({"name": str(entry[name_key]).strip(), "percent": pct})
            except (ValueError, TypeError):
                continue
    items.sort(key=lambda x: x["percent"], reverse=True)
    return items


def normalize_apply_analysis(
    raw: dict[str, Any],
    job_id: str,
    job_no: int,
    range_code: int | None = None,
) -> ApplyAnalysisResult:
    """Transform raw 104 apply analysis payload into structured competitor intelligence."""
    range_info = parse_apply_range(range_code)
    update_time = (
        (raw.get("edu") or {}).get("update_time")
        or raw.get("update_time")
        or "未知"
    )

    edu_items = _extract_items(raw.get("edu"), "eduName")
    age_items = _extract_items(raw.get("yearRange"), "yearRangeName")
    exp_items = _extract_items(raw.get("exp"), "expName")
    major_items = _extract_items(raw.get("major"), "majorName")
    skill_items = _extract_items(raw.get("skill"), "skillName")
    cert_items = _extract_items(raw.get("cert") or raw.get("certificate"), "certName")

    # Parse languages
    languages: list[LanguageItem] = []
    lang_group = raw.get("language")
    if isinstance(lang_group, dict):
        for k, lang in lang_group.items():
            if k in ("update_time", "total", "none") or not isinstance(lang, dict):
                continue
            lang_name = lang.get("langName")
            if not lang_name:
                continue
            try:
                lang_pct = float(lang.get("percent", 0) or 0)
            except (ValueError, TypeError):
                lang_pct = 0.0

            levels: list[DimensionItem] = []
            level_group = lang.get("level")
            if isinstance(level_group, dict):
                for lk, lvl in level_group.items():
                    if isinstance(lvl, dict) and lvl.get("levelName"):
                        try:
                            lvl_pct = float(lvl.get("percent", 0) or 0)
                            if lvl_pct > 0:
                                levels.append(
                                    DimensionItem(name=str(lvl["levelName"]).strip(), percent=lvl_pct)
                                )
                        except (ValueError, TypeError):
                            continue
            levels.sort(key=lambda x: x.percent, reverse=True)
            languages.append(
                LanguageItem(name=str(lang_name).strip(), percent=lang_pct, levels=levels)
            )

    all_percents = [
        *(i["percent"] for i in edu_items),
        *(i["percent"] for i in age_items),
        *(i["percent"] for i in exp_items),
    ]
    dimension_groups = [
        [i["percent"] for i in edu_items],
        [i["percent"] for i in age_items],
        [i["percent"] for i in exp_items],
    ]

    candidates = infer_applicant_count(
        all_percents,
        bounds=(range_info["min"], range_info["max"]),
        dimension_groups=dimension_groups,
    )

    total_applicants: int | None = None
    total_basis: Any = "unknown"
    estimated_applicants: int | None = None
    estimate_note = ""

    # 資料充分性檢查：
    # 至少要有 2 個以上非 0 且非 100 的相異百分比，或至少包含帶有小數點後精確位數的百分比，
    # 才能排除因粗粒度或巧合造成的單一假性解。
    informative_percents = [p for p in all_percents if 0.0 < p < 100.0]
    distinct_informative = set(informative_percents)
    has_fractional = any(abs(p - round(p)) > 0.01 for p in informative_percents)
    is_data_sufficient = len(distinct_informative) >= 2 or (len(distinct_informative) == 1 and has_fractional)

    if len(candidates) == 1 and is_data_sufficient:
        total_applicants = candidates[0]
        total_basis = "inferred"
        estimate_note = ""
    elif len(candidates) > 1:
        # 存在多個可能候選解：保留人數區間與不確定性，切勿任意取第一項作為精確值
        total_applicants = None
        total_basis = "ambiguous"
        candidate_summary = ", ".join(str(c) for c in candidates[:5])
        if len(candidates) > 5:
            candidate_summary += f"... (共 {len(candidates)} 個可能解)"
        estimated_applicants, best_err = _best_effort_estimate(
            all_percents, bounds=(range_info["min"], range_info["max"])
        )
        estimate_note = (
            f"存在多個符合百分比的人數解 ({candidate_summary})，無法唯一收斂，保留區間不確定性。"
            f"官方區間：{range_info['label']}。"
        )
    elif len(candidates) == 1 and not is_data_sufficient:
        total_applicants = None
        total_basis = "ambiguous"
        estimated_applicants = candidates[0]
        estimate_note = (
            f"候選解僅有 {candidates[0]}，但有效百分比資料不足以排除巧合，"
            f"保留區間不確定性。官方區間：{range_info['label']}。"
        )
    else:
        total_applicants = None
        total_basis = "unknown"
        estimated_applicants, best_err = _best_effort_estimate(
            all_percents, bounds=(range_info["min"], range_info["max"])
        )
        if estimated_applicants is not None:
            estimate_note = (
                f"無精確整數解；此為最小誤差概估（平均偏差 {best_err:.2f} 個百分點），"
                f"僅供參考，不可視為精算值。官方區間：{range_info['label']}。"
            )
        else:
            estimate_note = f"資料不足以反推人數。官方區間：{range_info['label']}。"

    def _map_dimension(items: list[dict[str, Any]]) -> list[DimensionItem]:
        res: list[DimensionItem] = []
        for it in items:
            count = (
                round((it["percent"] * total_applicants) / 100.0)
                if total_applicants is not None
                else None
            )
            res.append(DimensionItem(name=it["name"], percent=it["percent"], count=count))
        return res

    for lang in languages:
        if total_applicants is not None:
            lang.count = round((lang.percent * total_applicants) / 100.0)
            for lvl in lang.levels:
                lvl.count = round((lvl.percent * total_applicants) / 100.0)

    return ApplyAnalysisResult(
        job_id=job_id,
        job_no=job_no,
        total_applicants=total_applicants,
        total_basis=total_basis,
        estimated_applicants=estimated_applicants,
        estimate_note=estimate_note,
        candidate_counts=candidates,
        apply_range=range_info["label"],
        update_time=str(update_time),
        education=_map_dimension(edu_items),
        age_distribution=_map_dimension(age_items),
        experience_distribution=_map_dimension(exp_items),
        languages=languages,
        top_majors=_map_dimension(major_items)[:10],
        top_skills=_map_dimension(skill_items)[:10],
        certificates=_map_dimension(cert_items)[:10],
    )
