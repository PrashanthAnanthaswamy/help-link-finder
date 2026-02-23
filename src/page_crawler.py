"""
Page Crawler Module
-------------------
Crawls each page, extracts all <a> links, and identifies those whose
resolved path matches the configurable help-link pattern (default: /help*).
Uses async HTTP for fast concurrent page fetching.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


@dataclass
class HelpLinkInfo:
    """A single link on the page that matches the /help pattern."""
    url: str
    anchor_text: str
    source_page: str
    raw_href: str
    css_selector: Optional[str] = None
    element_index: int = 0


@dataclass
class PageResult:
    """Result of crawling a single page."""
    page_url: str
    total_links: int = 0
    help_links: List[HelpLinkInfo] = field(default_factory=list)
    page_status_code: Optional[int] = None
    page_error: Optional[str] = None
    crawl_duration: float = 0.0


class PageCrawler:
    """Crawls pages and identifies links matching a URL path pattern."""

    def __init__(
        self,
        pattern: str = r"(/help)(/.*)?$",
        timeout: int = 30,
        max_concurrent: int = 10,
        user_agent: str = "HelpLinkFinder/1.0",
        verify_ssl: bool = False,
        delay: float = 0.25,
    ):
        self.pattern = re.compile(pattern, re.IGNORECASE)
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.delay = delay

    def crawl_pages(
        self,
        urls: List[str],
        progress_callback=None,
    ) -> List[PageResult]:
        """
        Crawl all given URLs and return results with matched help links.

        Args:
            urls: List of page URLs to crawl.
            progress_callback: Optional callback(current, total, url).

        Returns:
            List of PageResult objects.
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls):
            logger.info("[%d/%d] Crawling: %s", i + 1, total, url)
            if progress_callback:
                progress_callback(i + 1, total, url)

            result = self._crawl_single_page(url)
            results.append(result)

            if self.delay and i < total - 1:
                time.sleep(self.delay)

        return results

    def _crawl_single_page(self, page_url: str) -> PageResult:
        """Fetch a single page and extract all help-pattern links."""
        start_time = time.time()
        result = PageResult(page_url=page_url)

        try:
            response = requests.get(
                page_url,
                timeout=self.timeout,
                headers={"User-Agent": _BROWSER_UA},
                allow_redirects=True,
                verify=self.verify_ssl,
            )
            result.page_status_code = response.status_code

            if response.status_code >= 400:
                result.page_error = f"Page returned HTTP {response.status_code}"
                result.crawl_duration = time.time() - start_time
                return result

        except requests.RequestException as e:
            result.page_error = str(e)
            result.crawl_duration = time.time() - start_time
            logger.error("Error fetching page %s: %s", page_url, e)
            return result

        links = self._extract_help_links(response.text, page_url)
        result.total_links = links["total"]
        result.help_links = links["matches"]
        result.crawl_duration = time.time() - start_time

        if result.help_links:
            logger.info(
                "  -> Found %d help link(s) out of %d total",
                len(result.help_links), result.total_links,
            )

        return result

    def _extract_help_links(self, html: str, page_url: str) -> dict:
        """Parse HTML, find all <a> tags, and filter for help-pattern matches."""
        soup = BeautifulSoup(html, "lxml")
        anchors = soup.find_all("a", href=True)
        total = len(anchors)
        matches: List[HelpLinkInfo] = []
        seen_urls: Set[str] = set()

        for idx, tag in enumerate(anchors):
            raw_href = tag["href"].strip()
            if not raw_href or raw_href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            abs_url = urljoin(page_url, raw_href)
            parsed = urlparse(abs_url)
            path = parsed.path.rstrip("/") or "/"

            if not self.pattern.search(path):
                continue

            if abs_url in seen_urls:
                continue
            seen_urls.add(abs_url)

            text = tag.get_text(strip=True) or tag.get("title", "") or "[no text]"
            selector = self._build_css_selector(tag, idx)

            matches.append(HelpLinkInfo(
                url=abs_url,
                anchor_text=text[:200],
                source_page=page_url,
                raw_href=raw_href,
                css_selector=selector,
                element_index=idx,
            ))

        return {"total": total, "matches": matches}

    @staticmethod
    def _build_css_selector(tag, idx: int) -> str:
        """Build a CSS selector that can identify this <a> element on the page."""
        if tag.get("id"):
            return f"#{tag['id']}"

        href = tag.get("href")
        if href:
            safe_href = href.replace('"', '\\"')
            return f'a[href="{safe_href}"]'

        classes = tag.get("class", [])
        if classes:
            return f"a.{'.'.join(classes)}"

        return f"a:nth-of-type({idx + 1})"
