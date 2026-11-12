"""Authentication and cookie management for 104 requests."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

SENSITIVE_COOKIE_NAMES = {
    "remember_me",
    "session",
    "sess",
    "token",
    "auth",
    "sso",
    "sid",
    "104_session",
}


def redact_cookie_value(name: str, value: str) -> str:
    if any(k in name.lower() for k in SENSITIVE_COOKIE_NAMES):
        if len(value) <= 6:
            return "***"
        return f"{value[:2]}***{value[-2:]}"
    return value


def load_cookies_from_env() -> dict[str, str]:
    raw = settings.cookie_string
    if not raw:
        return {}
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning("Failed to parse MCP_104_COOKIE as JSON: %s", e)
    cookies: dict[str, str] = {}
    for item in raw.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def load_cookies_from_file(path_str: str | None) -> dict[str, str]:
    if not path_str:
        return {}
    path = Path(path_str).expanduser()
    if not path.is_file():
        logger.warning("Cookie file not found: %s", path)
        return {}
    try:
        content = path.read_text(encoding="utf-8").strip()
        data = json.loads(content)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
        elif isinstance(data, list):
            cookies: dict[str, str] = {}
            for item in data:
                if isinstance(item, dict) and "name" in item and "value" in item:
                    cookies[str(item["name"])] = str(item["value"])
            return cookies
    except Exception as e:
        logger.warning("Failed to load cookies from %s: %s", path, e)
    return {}


def load_cookies_from_browser(browser_name: str = "chrome") -> dict[str, str]:
    try:
        import browser_cookie3
    except ImportError:
        logger.debug("browser-cookie3 not installed, skipping browser cookie extraction")
        return {}

    cookie_jar: Any = None
    try:
        if browser_name == "chrome":
            cookie_jar = browser_cookie3.chrome(domain_name=".104.com.tw")
        elif browser_name == "brave":
            cookie_jar = browser_cookie3.brave(domain_name=".104.com.tw")
        elif browser_name == "edge":
            cookie_jar = browser_cookie3.edge(domain_name=".104.com.tw")
    except Exception as e:
        logger.debug("Could not extract %s cookies: %s", browser_name, e)
        return {}

    if not cookie_jar:
        return {}

    result: dict[str, str] = {}
    for c in cookie_jar:
        if "104.com.tw" in c.domain:
            result[c.name] = c.value
    return result


def get_active_cookies() -> dict[str, str]:
    """Load cookies according to configured strategy."""
    source = settings.cookie_source.lower()
    if source == "none":
        return {}
    if source == "env":
        return load_cookies_from_env()
    if source == "file":
        return load_cookies_from_file(settings.cookie_file)
    if source == "chrome":
        # 1. Try saved file from interactive login or settings
        default_file = Path("~/.hermes/104_cookies.json").expanduser()
        if default_file.is_file():
            file_cookies = load_cookies_from_file(str(default_file))
            if file_cookies:
                return file_cookies

        if settings.cookie_file:
            file_cookies = load_cookies_from_file(settings.cookie_file)
            if file_cookies:
                return file_cookies

        # 2. Try Chrome browser cookies
        cookies = load_cookies_from_browser("chrome")
        if not cookies and settings.cookie_string:
            cookies = load_cookies_from_env()
        return cookies
    return {}
