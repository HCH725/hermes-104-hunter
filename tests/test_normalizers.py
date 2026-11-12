"""Unit tests for search and detail data normalizers."""

import pytest
from hermes_104_hunter.normalizers import normalize_job_detail, normalize_search_job


def test_normalize_search_job():
    raw_item = {
        "jobNo": "14526905",
        "jobName": "<b>Python</b> 資深工程師",
        "custName": "優質科技股份有限公司",
        "jobAddrNoDesc": "台北市信義區",
        "salaryDesc": "月薪 80,000~120,000 元",
        "salaryLow": "80000",
        "salaryHigh": "120000",
        "periodDesc": "3年以上",
        "eduDesc": "大學以上",
        "tags": [{"desc": "外商公司"}, {"desc": "彈性工時"}],
        "remoteWorkType": 1,
        "appearDate": "2026-11-12",
        "link": {"job": "https://www.104.com.tw/job/8nd15"},
    }

    job = normalize_search_job(raw_item)
    assert job.job_id == "8nd15"
    assert job.job_no == 14526905
    assert job.title == "Python 資深工程師"  # stripped HTML tag
    assert job.company_name == "優質科技股份有限公司"
    assert job.area == "台北市信義區"
    assert job.salary_min == 80000
    assert job.salary_max == 120000
    assert job.is_negotiable is False
    assert "外商公司" in job.tags
    assert "遠端工作" in job.tags
    assert job.url == "https://www.104.com.tw/job/8nd15"


def test_normalize_search_job_negotiable():
    raw_item = {
        "jobNo": "12345678",
        "jobName": "實習生",
        "custName": "新創公司",
        "salaryDesc": "待遇面議",
        "salaryLow": "0",
        "link": {"job": "https://www.104.com.tw/job/7aaaa"},
    }
    job = normalize_search_job(raw_item)
    assert job.is_negotiable is True
    assert job.salary_min is None


def test_normalize_job_detail():
    raw_payload = {
        "data": {
            "header": {
                "jobName": "後端架構師",
                "custName": "棠元宗科技",
                "jobNo": "14526905",
                "analysisType": 3,
                "isApplied": False,
            },
            "jobDetail": {
                "jobDescription": "負責核心微服務架構與高併發系統設計。",
                "salary": "月薪 100,000 元以上",
                "workTypeDesc": "全職",
                "addressRegion": "台北市",
                "addressDetail": "內湖科技園區",
            },
            "condition": {
                "workExp": "5年以上",
                "edu": "大學",
                "major": [{"major": "資訊工程相關"}],
                "language": [{"language": "英文", "ability": "中等"}],
                "skill": [{"skill": "Python"}, {"skill": "PostgreSQL"}],
                "certificate": [{"cert": "AWS Certified Solutions Architect"}],
                "other": "具備分散式快取設計經驗者佳。",
            },
            "welfare": {"welfare": "零食吧、每年健檢、彈性上下班。"},
            "contact": {"hrName": "林小姐"},
        }
    }

    detail = normalize_job_detail("8nd15", raw_payload)
    assert detail.job_id == "8nd15"
    assert detail.job_no == 14526905
    assert detail.title == "後端架構師"
    assert detail.company_name == "棠元宗科技"
    assert detail.analysis_type == 3
    assert detail.is_applied is False
    assert "資訊工程相關" in detail.major_req
    assert "Python" in detail.skills_req
    assert "AWS Certified Solutions Architect" in detail.certificates_req
    assert detail.hr_contact == "林小姐"
