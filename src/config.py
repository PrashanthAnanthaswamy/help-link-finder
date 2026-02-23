"""
Configuration Module
--------------------
Central configuration for the Help Link Finder framework.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FinderConfig:
    """Configuration for the Help Link Finder."""

    # ── Input ──
    csv_file: Optional[str] = None
    sitemap_url: Optional[str] = None

    # ── Batching ──
    batch: Optional[int] = None
    batch_size: int = 1000

    # ── Crawling ──
    timeout: int = 30
    max_concurrent: int = 10
    user_agent: str = "HelpLinkFinder/1.0"
    verify_ssl: bool = False
    delay: float = 0.25

    # ── Pattern ──
    pattern: str = r"(/help)(/.*)?$"

    # ── Screenshots ──
    take_screenshots: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    full_page_screenshot: bool = True
    screenshot_timeout: int = 30000
    dismiss_cookies: bool = True
    cookie_selector: Optional[str] = None

    # ── Output ──
    output_dir: str = "reports"
    screenshot_dir: str = "screenshots"
    report_filename: Optional[str] = None

    # ── Logging ──
    log_level: str = "INFO"
    verbose: bool = False
