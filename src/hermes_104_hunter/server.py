"""FastMCP / MCPServer entrypoint for hermes-104-hunter."""

from __future__ import annotations

import logging
import sys
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer  # type: ignore

from .applicant import get_cover_letter_templates, prepare_application
from .client import Job104Client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("hermes_104_hunter")

server = MCPServer(
    "hermes-104-hunter",
    instructions="""
Hermes 專屬 104 人力銀行求職特助 MCP：
1. job104_search: 輕量 API 職缺搜尋，支援地區代碼解析、薪資下限與完全遠端篩選。
2. job104_job_detail: 職缺深度結構化提取，掌握職能與技能要求。
3. job104_apply_analysis: 【獨門絕技】免瀏覽器！純 API + 數學逆推精算真實應徵人數與對手 Top 10 技能。
4. job104_get_my_templates: 讀取 104 帳號自薦信範本，繼承人類真實口吻。
5. job104_prepare_application: Hit-in-the-Loop 代填投遞視窗，留待人類親手點擊送出。
""",
)

_client: Job104Client | None = None


def get_client() -> Job104Client:
    global _client
    if _client is None:
        _client = Job104Client()
    return _client


@server.tool()
async def job104_search(
    keyword: str,
    area: str | None = None,
    page: int = 1,
    page_size: int = 20,
    order: int = 1,
    exclude_negotiable: bool = False,
    min_salary: int | None = None,
    remote_only: bool = False,
) -> dict[str, Any]:
    """搜尋 104 人力銀行職缺。支援地點中文轉換、薪資下限過濾、排除面議與完全遠端篩選，已進行三級 Token 清洗與精簡。"""
    client = get_client()
    res = await client.search_jobs(
        keyword=keyword,
        area=area,
        page=page,
        page_size=page_size,
        order=order,
        exclude_negotiable=exclude_negotiable,
        min_salary=min_salary,
        remote_only=remote_only,
    )
    return res.model_dump()


@server.tool()
async def job104_job_detail(
    job_url_or_id: str,
) -> dict[str, Any]:
    """取得 104 職缺詳細資訊。提取職缺描述、技能需求、加分條件、學歷經歷要求、公司福利與 HR 聯絡人。"""
    client = get_client()
    res = await client.get_job_detail(job_url_or_id)
    return res.model_dump()


@server.tool()
async def job104_apply_analysis(
    job_url_or_id: str,
) -> dict[str, Any]:
    """【獨門絕技】免啟動瀏覽器！透過 104 內部統計 API 與數學逆推演算法，精算出真實應徵人數（突破 30 人以上黑盒子），並分析對手學歷、年資經歷分佈與 Top 10 具備技能（找出突圍策略關鍵）。"""
    client = get_client()
    res = await client.get_apply_analysis(job_url_or_id)
    return res.model_dump()


@server.tool()
async def job104_get_my_templates(
    job_url_or_id: str,
) -> dict[str, Any]:
    """讀取使用者 104 帳號中儲存的所有自薦信/求職信範本，包含範本標題與內文。供 AI 研讀並繼承使用者口吻，撰寫客製化推薦信時徹底消除 AI 罐頭感。"""
    templates = await get_cover_letter_templates(job_url_or_id)
    return {
        "status": "success",
        "total_templates": len(templates),
        "templates": [t.model_dump() for t in templates],
    }


@server.tool()
async def job104_prepare_application(
    job_url_or_id: str,
    template_title: str | None = None,
    cover_letter_text: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """【Hit-in-the-Loop 代填應徵】以 Playwright 自動化打開真實職缺視窗、切換指定自薦信範本、填入客製推薦信並截圖。安全鐵律：絕不會替使用者按送出按鈕，視窗保留供人類肉眼驗證後手動點擊最後一步。"""
    res = await prepare_application(
        job_url_or_id=job_url_or_id,
        template_title=template_title,
        cover_letter_text=cover_letter_text,
        dry_run=dry_run,
    )
    return res.model_dump()


def main():
    """Main CLI entrypoint for stdio transport."""
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
