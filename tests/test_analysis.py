"""Unit tests for competitor apply analysis and math reverse-engineering."""

import pytest
from hermes_104_hunter.analysis import (
    extract_job_id,
    fits_percent,
    infer_applicant_count,
    normalize_apply_analysis,
    parse_apply_range,
    slug_to_job_no,
)


def test_extract_job_id():
    assert extract_job_id("8nd15") == "8nd15"
    assert extract_job_id("https://www.104.com.tw/job/8nd15") == "8nd15"
    assert extract_job_id("https://www.104.com.tw/job/8nd15?jobsource=index") == "8nd15"
    assert extract_job_id("https://www.104.com.tw/jobs/apply/analysis/8nd15?channel=104rpt") == "8nd15"
    assert extract_job_id("7BSYK") == "7bsyk"


def test_slug_to_job_no():
    # '8nd15' in base 36 is 14526905
    assert slug_to_job_no("8nd15") == 14526905
    assert slug_to_job_no("https://www.104.com.tw/job/8nd15") == 14526905
    # Decimal jobNo pass-through
    assert slug_to_job_no("14526905") == 14526905


def test_parse_apply_range():
    assert parse_apply_range(1) == {"label": "0~5 人", "min": 0, "max": 5}
    assert parse_apply_range(2) == {"label": "6~10 人", "min": 6, "max": 10}
    assert parse_apply_range(3) == {"label": "11~30 人", "min": 11, "max": 30}
    assert parse_apply_range(4) == {"label": "30 人以上", "min": 31, "max": 5000}
    assert parse_apply_range(None) == {"label": "未知區間", "min": 1, "max": 5000}


def test_fits_percent():
    # If n=28, 3/28 = 10.71428% -> displayed as 10.71%
    assert fits_percent(10.71, 28) is True
    # 25/28 = 89.2857% -> displayed as 89.29%
    assert fits_percent(89.29, 28) is True
    # Should not fit n=15
    assert fits_percent(10.71, 15) is False


def test_infer_applicant_count_exact():
    # Real case from 104 job 8nd15: edu has 10.71% and 89.29%, range 11~30
    percents = [10.71, 89.29]
    dimension_groups = [[10.71, 89.29]]
    candidates = infer_applicant_count(percents, bounds=(11, 30), dimension_groups=dimension_groups)
    assert 28 in candidates
    assert candidates[0] == 28


def test_infer_applicant_count_no_match():
    # Empty percents
    assert infer_applicant_count([]) == []


def test_normalize_apply_analysis():
    raw_payload = {
        "edu": {
            "0": {"eduName": "博碩士", "count": 0, "percent": "10.71"},
            "1": {"eduName": "大學", "count": 0, "percent": "89.29"},
            "update_time": "2026-11-12 10:00:00",
            "total": 0,
        },
        "yearRange": {
            "0": {"yearRangeName": "25~29歲", "count": 0, "percent": "50.00"},
            "1": {"yearRangeName": "30~34歲", "count": 0, "percent": "50.00"},
        },
        "exp": {
            "0": {"expName": "1~3年", "count": 0, "percent": "100.00"},
        },
        "skill": {
            "0": {"skillName": "Python", "count": 0, "percent": "75.00"},
            "1": {"skillName": "FastAPI", "count": 0, "percent": "50.00"},
        },
    }

    result = normalize_apply_analysis(raw_payload, "8nd15", 14526905, range_code=3)
    assert result.job_id == "8nd15"
    assert result.job_no == 14526905
    assert result.total_applicants == 28
    assert result.total_basis == "inferred"
    assert result.apply_range == "11~30 人"
    assert len(result.education) == 2
    # Check education counts
    edu_master = next(e for e in result.education if e.name == "博碩士")
    assert edu_master.count == 3  # round(10.71 * 28 / 100) = 3
    edu_bachelor = next(e for e in result.education if e.name == "大學")
    assert edu_bachelor.count == 25  # round(89.29 * 28 / 100) = 25
    # Check skills
    assert len(result.top_skills) == 2
    assert result.top_skills[0].name == "Python"
    assert result.top_skills[0].count == 21  # round(75.00 * 28 / 100) = 21
