"""Unit tests for Job104Client with respx mocked HTTP requests."""

import pytest
import respx
import httpx

from hermes_104_hunter.client import Job104Client, resolve_area_code
from hermes_104_hunter.config import SEARCH_API_URL, DETAIL_API_URL, APPLY_ANALYSIS_API_URL


def test_resolve_area_code():
    assert resolve_area_code("台北市") == "6001001000"
    assert resolve_area_code("台北") == "6001001000"
    assert resolve_area_code("新竹市") == "6001006001"
    assert resolve_area_code("6001001000") == "6001001000"
    assert resolve_area_code("台北市,新北市") == "6001001000,6001002000"
    assert resolve_area_code(None) is None


@pytest.mark.asyncio
@respx.mock
async def test_client_search_jobs():
    client = Job104Client()
    mock_response = {
        "data": [
            {
                "jobNo": "14526905",
                "jobName": "Python 開發者",
                "custName": "測試科技",
                "jobAddrNoDesc": "台北市大安區",
                "salaryDesc": "月薪 70,000~90,000 元",
                "salaryLow": "70000",
                "salaryHigh": "90000",
                "link": {"job": "https://www.104.com.tw/job/8nd15"},
            },
            {
                "jobNo": "12345678",
                "jobName": "實習生",
                "custName": "測試科技2",
                "salaryDesc": "面議",
                "salaryLow": "0",
                "link": {"job": "https://www.104.com.tw/job/7xxxx"},
            },
        ],
        "metadata": {"pagination": {"total": 2, "lastPage": 1}},
    }

    respx.get(SEARCH_API_URL).mock(return_value=httpx.Response(200, json=mock_response))

    # Normal search
    resp = await client.search_jobs("Python", area="台北市")
    assert resp.total_count == 2
    assert len(resp.jobs) == 2
    assert resp.jobs[0].job_id == "8nd15"

    # Filter exclude_negotiable
    filtered_resp = await client.search_jobs("Python", exclude_negotiable=True)
    assert len(filtered_resp.jobs) == 1
    assert filtered_resp.jobs[0].title == "Python 開發者"

    # Filter min_salary
    salary_resp = await client.search_jobs("Python", min_salary=80000)
    assert len(salary_resp.jobs) == 1

    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_client_get_job_detail():
    client = Job104Client()
    mock_detail = {
        "data": {
            "header": {
                "jobName": "資深演算法工程師",
                "custName": "棠元宗",
                "jobNo": "14526905",
                "analysisType": 2,
            },
            "jobDetail": {
                "jobDescription": "負責核心模型訓練與數學推導。",
                "salary": "面議",
                "workTypeDesc": "全職",
                "addressRegion": "台北市",
                "addressDetail": "信義區",
            },
            "condition": {
                "workExp": "3年以上",
                "edu": "碩士",
                "skill": [{"skill": "PyTorch"}],
            },
            "welfare": {},
            "contact": {},
        }
    }
    respx.get(f"{DETAIL_API_URL}/8nd15").mock(return_value=httpx.Response(200, json=mock_detail))

    detail = await client.get_job_detail("8nd15")
    assert detail.job_id == "8nd15"
    assert detail.title == "資深演算法工程師"
    assert detail.analysis_type == 2
    assert "PyTorch" in detail.skills_req

    await client.close()
