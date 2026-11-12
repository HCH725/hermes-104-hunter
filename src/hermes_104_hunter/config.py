"""Configuration constants and settings for hermes-104-hunter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_104 = "https://www.104.com.tw"
SEARCH_API_URL = f"{BASE_104}/jobs/search/api/jobs"
DETAIL_API_URL = f"{BASE_104}/job/ajax/content"
APPLY_ANALYSIS_API_URL = f"{BASE_104}/jb/104i/applyAnalysisToJob/all"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)

@dataclass(frozen=True)
class Settings:
    cookie_source: str = os.getenv("MCP_104_COOKIE_SOURCE", "chrome")  # chrome, file, env, none
    cookie_file: str | None = os.getenv("MCP_104_COOKIE_FILE")
    cookie_string: str | None = os.getenv("MCP_104_COOKIE")
    timeout: float = float(os.getenv("MCP_104_TIMEOUT", "15.0"))
    screenshots_dir: Path = Path(os.getenv("MCP_104_SCREENSHOTS_DIR", "./.screenshots")).resolve()

settings = Settings()
