"""Hit-in-the-Loop (HITL) application preparation and template extraction using Playwright."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from .analysis import extract_job_id
from .auth import get_active_cookies
from .config import settings
from .models import ApplicationPrepResult, CoverLetterTemplate

logger = logging.getLogger(__name__)


async def _launch_browser_with_cookies(headless: bool = True):
    from playwright.async_api import async_playwright

    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=headless,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    )

    # Inject cookies
    cookies = get_active_cookies()
    if cookies:
        playwright_cookies = [
            {"name": k, "value": v, "domain": ".104.com.tw", "path": "/"}
            for k, v in cookies.items()
        ]
        await context.add_cookies(playwright_cookies)

    return p, browser, context


async def get_cover_letter_templates(job_url_or_id: str) -> list[CoverLetterTemplate]:
    """Extract user's saved cover letter templates from 104 application modal."""
    slug = extract_job_id(job_url_or_id)
    job_url = f"https://www.104.com.tw/job/{slug}"

    p, browser, context = await _launch_browser_with_cookies(headless=True)
    try:
        page = await context.new_page()
        await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
        await asyncio.sleep(2)

        if "login" in page.url.lower():
            logger.warning("Not logged in to 104. Cannot read custom cover letters.")
            return [
                CoverLetterTemplate(
                    title="系統預設推薦信",
                    content="您好，我對貴公司的這項職缺非常有興趣，懇請惠予面試機會，謝謝！",
                    is_default=True,
                )
            ]

        # Click apply button to open modal
        apply_btn = page.locator(
            '.apply-button__button, button:has-text("我要應徵"), button:has-text("應徵")'
        ).first
        await apply_btn.wait_for(state="visible", timeout=8000)
        await apply_btn.click()
        await asyncio.sleep(2.5)

        templates: list[CoverLetterTemplate] = []
        dropdown = page.locator('.apply-msg .form-control, .apply-msg .text-region').first
        textarea = page.locator(
            '.apply-popup textarea, .apply-msg textarea, textarea.form-control:visible'
        ).first

        has_dropdown = await dropdown.is_visible()
        if has_dropdown:
            await dropdown.click()
            await asyncio.sleep(0.6)
            options = page.locator('.apply-msg .multiselect__option')
            count = await options.count()
            titles: list[str] = []
            for i in range(count):
                text = (await options.nth(i).inner_text()).strip()
                if text:
                    titles.append(text)

            for title in titles:
                # reopen dropdown if closed
                if not await page.locator('.apply-msg .multiselect__content').is_visible():
                    await dropdown.click()
                    await asyncio.sleep(0.4)
                target_opt = page.locator('.apply-msg .multiselect__option').filter(has_text=title).first
                if await target_opt.is_visible():
                    await target_opt.click()
                    await asyncio.sleep(1.0)
                    content = await textarea.input_value()
                    templates.append(
                        CoverLetterTemplate(
                            title=title,
                            content=content,
                            is_default="預設" in title or len(templates) == 0,
                        )
                    )
        else:
            content = await textarea.input_value()
            if content:
                templates.append(
                    CoverLetterTemplate(title="系統預設推薦信", content=content, is_default=True)
                )

        await page.keyboard.press("Escape")
        return templates
    finally:
        await browser.close()
        await p.stop()


async def prepare_application(
    job_url_or_id: str,
    template_title: str | None = None,
    cover_letter_text: str | None = None,
    dry_run: bool = False,
    headless: bool = False,
) -> ApplicationPrepResult:
    """
    Prepare job application via Playwright with strict Hit-in-the-Loop protection.
    Fills the cover letter and leaves the modal open for human review and manual submit.
    NEVER clicks the final submit button.
    """
    slug = extract_job_id(job_url_or_id)
    job_url = f"https://www.104.com.tw/job/{slug}"

    # If dry_run is requested, we can run headless
    run_headless = True if dry_run else headless

    p, browser, context = await _launch_browser_with_cookies(headless=run_headless)
    try:
        page = await context.new_page()
        api_is_applied: bool | None = None

        async def handle_response(response):
            nonlocal api_is_applied
            if f"/ajax/content/{slug}" in response.url or f"/api/jobs/{slug}" in response.url:
                try:
                    payload = await response.json()
                    hdr = (payload.get("data") or {}).get("header") or {}
                    if isinstance(hdr.get("isApplied"), bool):
                        api_is_applied = hdr.get("isApplied")
                except Exception:
                    pass

        page.on("response", handle_response)
        await page.goto(job_url, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(1.5)

        # 1. First safety check: backend API indicator
        if api_is_applied is True:
            return ApplicationPrepResult(
                status="already_applied",
                dry_run=dry_run,
                message="您先前已應徵過此職缺（104 後端紀錄確認），無需重複應徵。",
                job_url=job_url,
                selected_template="無",
                cover_letter_filled=False,
                cover_letter_preview="無",
            )

        # 2. Second safety check: DOM text indicator
        body_text = await page.inner_text("body")
        if "已應徵" in body_text or "已投遞" in body_text:
            return ApplicationPrepResult(
                status="already_applied",
                dry_run=dry_run,
                message="您先前已應徵過此職缺，無需重複應徵。",
                job_url=job_url,
                selected_template="無",
                cover_letter_filled=False,
                cover_letter_preview="無",
            )

        if "職缺已結束" in body_text or "停止招募" in body_text or "職缺已下架" in body_text:
            return ApplicationPrepResult(
                status="job_closed",
                dry_run=dry_run,
                message="此職缺目前已結束招募或已下架。",
                job_url=job_url,
                selected_template="無",
                cover_letter_filled=False,
                cover_letter_preview="無",
            )

        # 3. Locate and click apply button
        apply_btn = page.locator(
            '.apply-button__button, button:has-text("我要應徵"), button:has-text("應徵")'
        ).first
        await apply_btn.wait_for(state="visible", timeout=8000)
        await apply_btn.click()
        await asyncio.sleep(2.5)

        selected_tpl_name = "使用 104 預設範本"
        if template_title:
            try:
                dropdown = page.locator('.apply-msg .form-control, .apply-msg .text-region').first
                if await dropdown.is_visible():
                    await dropdown.click()
                    await asyncio.sleep(0.5)
                    target_opt = page.locator('.apply-msg .multiselect__option').filter(has_text=template_title).first
                    if await target_opt.is_visible():
                        selected_tpl_name = (await target_opt.inner_text()).strip()
                        await target_opt.click()
                        await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning("Failed to select template %s: %s", template_title, e)

        textarea = page.locator(
            '.apply-popup textarea, .apply-msg textarea, textarea.form-control:visible'
        ).first
        await textarea.wait_for(state="visible", timeout=5000)

        cover_letter_filled = False
        if cover_letter_text:
            await textarea.click()
            await textarea.fill(cover_letter_text)
            await textarea.dispatch_event("input")
            await textarea.dispatch_event("change")
            cover_letter_filled = True

        preview_text = await textarea.input_value()

        # Capture screenshot
        settings.screenshots_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        mode_str = "dry_run" if dry_run else "hitl"
        screenshot_path = settings.screenshots_dir / f"apply_{mode_str}_{slug}_{ts}.png"
        await page.screenshot(path=str(screenshot_path), full_page=False)

        msg = (
            f"【DRY RUN 模擬完成】已成功載入職缺並模擬填寫推薦信，截圖已存至 {screenshot_path}。"
            if dry_run
            else f"【Hit-in-the-Loop 就緒】已開啟應徵視窗並填寫自薦信！Agent 堅守安全邊界，絕不會自動送出。請漢秦哥親自於瀏覽器點擊最後的送出按鈕！(截圖已保存: {screenshot_path})"
        )

        return ApplicationPrepResult(
            status="ready",
            dry_run=dry_run,
            message=msg,
            job_url=job_url,
            selected_template=selected_tpl_name,
            cover_letter_filled=cover_letter_filled,
            cover_letter_preview=preview_text,
            screenshot_path=str(screenshot_path),
        )
    finally:
        if dry_run or run_headless:
            await browser.close()
            await p.stop()
        else:
            # Keep the browser open for the user to review and click submit!
            logger.info("Browser kept open for user confirmation.")
