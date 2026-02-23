"""
Screenshot Capture Module
-------------------------
Uses Playwright to capture screenshots of pages containing /help links,
with the matching link elements highlighted in blue.
"""

import os
import re
import logging
from typing import List, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import (
    sync_playwright,
    Page,
    TimeoutError as PlaywrightTimeout,
)

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Result of a screenshot capture."""
    page_url: str
    screenshot_path: str
    success: bool
    help_links_highlighted: int = 0
    error_message: Optional[str] = None


class ScreenshotCapture:
    """Captures screenshots with /help links highlighted."""

    DEFAULT_COOKIE_SELECTORS = [
        "#onetrust-accept-btn-handler",
        "#accept-cookie-notification",
        "button[data-testid='cookie-accept']",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
        ".cc-accept",
        "#cookie-accept",
        "button.accept-cookies",
        "[aria-label='Accept cookies']",
        "[aria-label='Accept all cookies']",
        "button:has-text('Accept All Cookies')",
        "button:has-text('Accept All')",
        "button:has-text('Accept Cookies')",
        "button:has-text('I Accept')",
        "button:has-text('Got it')",
        "button:has-text('Agree')",
    ]

    HIGHLIGHT_CSS = """
    .hlf-help-link-highlight {
        outline: 4px solid #2563EB !important;
        outline-offset: 3px !important;
        background-color: rgba(37, 99, 235, 0.12) !important;
        position: relative !important;
        z-index: 9999 !important;
    }
    .hlf-help-link-highlight::after {
        content: "HELP LINK \\2192  " attr(href) !important;
        position: absolute !important;
        top: -30px !important;
        left: 0 !important;
        background-color: #2563EB !important;
        color: white !important;
        font-size: 11px !important;
        font-weight: bold !important;
        padding: 3px 10px !important;
        border-radius: 4px !important;
        white-space: nowrap !important;
        z-index: 10000 !important;
        font-family: Arial, sans-serif !important;
        letter-spacing: 0.5px !important;
        max-width: 500px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }
    .hlf-badge {
        position: fixed !important;
        top: 10px !important;
        right: 10px !important;
        background-color: #2563EB !important;
        color: white !important;
        font-size: 14px !important;
        font-weight: bold !important;
        padding: 10px 16px !important;
        border-radius: 8px !important;
        z-index: 99999 !important;
        font-family: Arial, sans-serif !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
    }
    """

    JPEG_QUALITY = 60
    JPEG_MAX_WIDTH = 1280

    def __init__(
        self,
        output_dir: str = "screenshots",
        viewport_width: int = 1920,
        viewport_height: int = 1080,
        full_page: bool = True,
        timeout: int = 30000,
        cookie_selectors: Optional[List[str]] = None,
        dismiss_cookies: bool = True,
    ):
        self.output_dir = os.path.abspath(output_dir)
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.full_page = full_page
        self.timeout = timeout
        self.dismiss_cookies = dismiss_cookies
        self.cookie_selectors = cookie_selectors or self.DEFAULT_COOKIE_SELECTORS
        os.makedirs(self.output_dir, exist_ok=True)

    def capture_pages_with_help_links(
        self,
        page_results: list,
        progress_callback=None,
    ) -> List[ScreenshotResult]:
        """
        Capture screenshots for all pages that have /help links.

        Args:
            page_results: List of PageResult objects from PageCrawler.
            progress_callback: Optional callback(current, total, url).

        Returns:
            List of ScreenshotResult objects.
        """
        pages_with_links = [pr for pr in page_results if pr.help_links]

        if not pages_with_links:
            logger.info("No pages with help links — no screenshots needed.")
            return []

        total = len(pages_with_links)
        logger.info("Capturing screenshots for %d page(s) with help links", total)

        results = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={
                    "width": self.viewport_width,
                    "height": self.viewport_height,
                },
                ignore_https_errors=True,
            )

            for i, page_result in enumerate(pages_with_links):
                if progress_callback:
                    progress_callback(i + 1, total, page_result.page_url)

                logger.info("[%d/%d] Screenshotting: %s", i + 1, total, page_result.page_url)

                result = self._capture_single_page(
                    context, page_result.page_url, page_result.help_links,
                )
                results.append(result)

            context.close()
            browser.close()

        return results

    def _capture_single_page(
        self,
        context,
        page_url: str,
        help_links: list,
    ) -> ScreenshotResult:
        """Capture a screenshot of a single page with help links highlighted."""
        filename = self._url_to_filename(page_url)
        screenshot_path = os.path.join(self.output_dir, filename)

        page = context.new_page()

        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=self.timeout)

            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeout:
                logger.debug("  Network did not go idle within 15s, continuing")

            page.wait_for_timeout(2000)

            if self.dismiss_cookies:
                self._dismiss_cookie_banner(page)

            page.add_style_tag(content=self.HIGHLIGHT_CSS)

            highlighted = self._highlight_help_links(page, help_links)

            page.evaluate(f"""() => {{
                const badge = document.createElement('div');
                badge.className = 'hlf-badge';
                badge.textContent = '{highlighted} Help Link(s) Found on This Page';
                document.body.appendChild(badge);
            }}""")

            page.wait_for_timeout(500)

            png_path = screenshot_path.replace(".jpg", ".png")
            page.screenshot(path=png_path, full_page=self.full_page)
            self._compress_to_jpeg(png_path, screenshot_path)

            logger.info("  Screenshot saved: %s", screenshot_path)

            return ScreenshotResult(
                page_url=page_url,
                screenshot_path=screenshot_path,
                success=True,
                help_links_highlighted=highlighted,
            )

        except PlaywrightTimeout:
            error_msg = f"Timeout loading page: {page_url}"
            logger.error("  %s", error_msg)

            try:
                if self.dismiss_cookies:
                    self._dismiss_cookie_banner(page)
                page.add_style_tag(content=self.HIGHLIGHT_CSS)
                highlighted = self._highlight_help_links(page, help_links)
                page.wait_for_timeout(500)
                png_path = screenshot_path.replace(".jpg", ".png")
                page.screenshot(path=png_path, full_page=False)
                self._compress_to_jpeg(png_path, screenshot_path)
                return ScreenshotResult(
                    page_url=page_url,
                    screenshot_path=screenshot_path,
                    success=True,
                    help_links_highlighted=highlighted,
                    error_message="Partial page load (timeout)",
                )
            except Exception:
                return ScreenshotResult(
                    page_url=page_url,
                    screenshot_path="",
                    success=False,
                    error_message=error_msg,
                )

        except Exception as e:
            error_msg = f"Error capturing {page_url}: {e}"
            logger.error("  %s", error_msg)
            return ScreenshotResult(
                page_url=page_url,
                screenshot_path="",
                success=False,
                error_message=error_msg,
            )

        finally:
            page.close()

    def _dismiss_cookie_banner(self, page: Page) -> bool:
        """Attempt to dismiss cookie consent banners."""
        for selector in self.cookie_selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=2000):
                    locator.click(timeout=3000)
                    logger.info("  Cookie banner dismissed via: %s", selector)
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue

        try:
            removed = page.evaluate("""() => {
                const overlaySelectors = [
                    '#onetrust-banner-sdk',
                    '#onetrust-consent-sdk',
                    '.onetrust-pc-dark-filter',
                    '#cookie-banner',
                    '.cookie-banner',
                    '.cookie-consent',
                    '#cookieConsent',
                    '.cc-window',
                    '#CybotCookiebotDialog',
                    '#CybotCookiebotDialogBodyUnderlay',
                ];
                let count = 0;
                for (const sel of overlaySelectors) {
                    const els = document.querySelectorAll(sel);
                    els.forEach(el => { el.remove(); count++; });
                }
                document.querySelectorAll(
                    '[class*="cookie"], [id*="cookie"], [class*="consent"], [id*="consent"]'
                ).forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'sticky') {
                        el.remove();
                        count++;
                    }
                });
                return count;
            }""")
            if removed > 0:
                logger.info("  Removed %d cookie overlay element(s) via JS fallback", removed)
                page.wait_for_timeout(500)
                return True
        except Exception:
            pass

        logger.debug("  No cookie banner detected")
        return False

    def _highlight_help_links(self, page: Page, help_links: list) -> int:
        """Highlight matching help link elements on the page. Returns count highlighted."""
        highlighted = 0

        for link_info in help_links:
            try:
                url = link_info.url
                raw_href = link_info.raw_href
                parsed = urlparse(url)
                url_path = parsed.path

                # Strategy 1: match by href attribute value
                if raw_href:
                    safe_href = raw_href.replace("'", "\\'").replace('"', '\\"')
                    safe_url = url.replace("'", "\\'").replace('"', '\\"')
                    try:
                        result = page.evaluate(
                            f"""() => {{
                                const elements = document.querySelectorAll('a[href]');
                                for (const el of elements) {{
                                    const raw = el.getAttribute('href') || '';
                                    const resolved = el.href || '';
                                    if (raw === '{safe_href}' || resolved === '{safe_url}'
                                        || raw === '{safe_url}') {{
                                        el.classList.add('hlf-help-link-highlight');
                                        return true;
                                    }}
                                }}
                                return false;
                            }}"""
                        )
                        if result:
                            highlighted += 1
                            continue
                    except Exception:
                        pass

                # Strategy 2: CSS selector from crawler
                if link_info.css_selector:
                    try:
                        locator = page.locator(link_info.css_selector).first
                        if locator.count() > 0:
                            locator.evaluate(
                                """(el) => { el.classList.add('hlf-help-link-highlight'); }"""
                            )
                            highlighted += 1
                            continue
                    except Exception:
                        pass

                # Strategy 3: partial path match
                if url_path and len(url_path) > 1:
                    safe_path = url_path.replace("'", "\\'").replace('"', '\\"')
                    try:
                        result = page.evaluate(
                            f"""() => {{
                                const elements = document.querySelectorAll('a[href*="{safe_path}"]');
                                if (elements.length >= 1 && elements.length <= 5) {{
                                    elements.forEach(el => el.classList.add('hlf-help-link-highlight'));
                                    return true;
                                }}
                                return false;
                            }}"""
                        )
                        if result:
                            highlighted += 1
                    except Exception:
                        pass

            except Exception as e:
                logger.debug("Could not highlight link %s: %s", link_info.url, e)

        logger.info("  Highlighted %d/%d help links", highlighted, len(help_links))
        return highlighted

    def _compress_to_jpeg(self, png_path: str, jpeg_path: str):
        """Convert a PNG screenshot to a compressed, resized JPEG."""
        try:
            with Image.open(png_path) as img:
                img = img.convert("RGB")
                w, h = img.size
                if w > self.JPEG_MAX_WIDTH:
                    ratio = self.JPEG_MAX_WIDTH / w
                    img = img.resize(
                        (self.JPEG_MAX_WIDTH, int(h * ratio)),
                        Image.LANCZOS,
                    )
                img.save(jpeg_path, "JPEG", quality=self.JPEG_QUALITY, optimize=True)
            os.remove(png_path)
        except Exception as e:
            logger.warning(
                "JPEG compression failed for %s: %s — keeping PNG", png_path, e,
            )
            if os.path.exists(png_path) and not os.path.exists(jpeg_path):
                os.rename(png_path, jpeg_path)

    @staticmethod
    def _url_to_filename(url: str) -> str:
        """Convert a URL to a safe filename."""
        name = re.sub(r"https?://", "", url)
        name = re.sub(r"[^a-zA-Z0-9]", "_", name)
        name = name[:120].rstrip("_")
        return f"{name}.jpg"
