"""Interactive login CLI for hermes-104-hunter using Playwright."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from .config import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

DEFAULT_COOKIE_PATH = Path("~/.hermes/104_cookies.json").expanduser()


async def interactive_login(output_path: Path | None = None) -> Path:
    target_path = output_path or DEFAULT_COOKIE_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("🏹 正在啟動 104 人力銀行登入視窗...")
    print("請在彈出的瀏覽器中完成登入（支援 104 帳密、Google、LINE 等登入方式）。")
    print("=" * 65)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=DEFAULT_USER_AGENT,
        )
        page = await context.new_page()
        await page.goto("https://plus.104.com.tw/login", wait_until="domcontentloaded")

        print("\n👉 請在瀏覽器視窗中完成登入。")
        print("💡 登入成功後，請回到此處按下 [Enter] 鍵儲存憑證...", end="", flush=True)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sys.stdin.readline)

        # Retrieve all 104 cookies
        cookies_list = await context.cookies(["https://www.104.com.tw", "https://plus.104.com.tw"])
        cookies_dict = {c["name"]: c["value"] for c in cookies_list}

        if not cookies_dict:
            print("\n⚠️ 未檢測到 104 Cookies，請確認瀏覽器是否已完成登入。")
        else:
            target_path.write_text(
                json.dumps(cookies_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"\n✅ 成功擷取 {len(cookies_dict)} 個 104 登入憑證！")
            print(f"📁 憑證已儲存至：{target_path}")

        await browser.close()

    return target_path


def main():
    try:
        asyncio.run(interactive_login())
    except KeyboardInterrupt:
        print("\n登入程序已取消。")
        sys.exit(1)


if __name__ == "__main__":
    main()
