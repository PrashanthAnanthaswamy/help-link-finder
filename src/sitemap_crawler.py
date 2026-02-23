"""
Sitemap Crawler Module
----------------------
Fetches and recursively parses sitemap.xml files (including sitemap
index files) to extract all page URLs. Supports auto-discovery via
robots.txt and common paths.
"""

import logging
from typing import List, Optional, Set
from xml.etree import ElementTree as ET

import requests

logger = logging.getLogger(__name__)

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

_SITEMAP_PATHS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap/sitemap.xml",
    "/sitemaps/sitemap.xml",
]


def _fetch_xml(url: str, timeout: int = 30) -> Optional[str]:
    """Fetch a URL and return the response text, or None on failure."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; HelpLinkFinder/1.0; "
                    "sitemap crawler)"
                ),
                "Accept": "application/xml, text/xml, */*",
            },
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text
        logger.warning("HTTP %d fetching sitemap: %s", resp.status_code, url)
        return None
    except requests.RequestException as exc:
        logger.warning("Error fetching sitemap %s: %s", url, exc)
        return None


def _parse_sitemap(xml_text: str) -> dict:
    """
    Parse a sitemap XML string.

    Returns dict with:
        - 'type': 'index' or 'urlset'
        - 'sitemaps': list of child sitemap URLs (if index)
        - 'urls': list of page URLs (if urlset)
    """
    result = {"type": "urlset", "sitemaps": [], "urls": []}

    try:
        xml_text = xml_text.strip()
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("XML parse error: %s", exc)
        return result

    root_tag = root.tag.lower()

    if "sitemapindex" in root_tag:
        result["type"] = "index"
        for sitemap_el in root.findall("sm:sitemap", _NS):
            loc = sitemap_el.find("sm:loc", _NS)
            if loc is not None and loc.text:
                result["sitemaps"].append(loc.text.strip())
        if not result["sitemaps"]:
            for sitemap_el in root.findall("sitemap"):
                loc = sitemap_el.find("loc")
                if loc is not None and loc.text:
                    result["sitemaps"].append(loc.text.strip())
        return result

    result["type"] = "urlset"
    for url_el in root.findall("sm:url", _NS):
        loc = url_el.find("sm:loc", _NS)
        if loc is not None and loc.text:
            result["urls"].append(loc.text.strip())
    if not result["urls"]:
        for url_el in root.findall("url"):
            loc = url_el.find("loc")
            if loc is not None and loc.text:
                result["urls"].append(loc.text.strip())

    return result


def crawl_sitemap(
    sitemap_url: str,
    timeout: int = 30,
    max_depth: int = 5,
    on_progress=None,
) -> List[str]:
    """
    Crawl a sitemap URL (or sitemap index) recursively and return all
    unique page URLs found.
    """
    all_urls: List[str] = []
    seen_urls: Set[str] = set()
    visited_sitemaps: Set[str] = set()

    def _crawl(url: str, depth: int):
        if depth > max_depth:
            logger.warning("Max sitemap depth (%d) reached at %s", max_depth, url)
            return
        if url in visited_sitemaps:
            return
        visited_sitemaps.add(url)

        if on_progress:
            on_progress(f"Fetching sitemap: {url}")

        xml_text = _fetch_xml(url, timeout=timeout)
        if not xml_text:
            return

        parsed = _parse_sitemap(xml_text)

        if parsed["type"] == "index":
            if on_progress:
                on_progress(f"  Sitemap index with {len(parsed['sitemaps'])} child sitemap(s)")
            for child_url in parsed["sitemaps"]:
                _crawl(child_url, depth + 1)
        else:
            new_count = 0
            for page_url in parsed["urls"]:
                if page_url not in seen_urls:
                    seen_urls.add(page_url)
                    all_urls.append(page_url)
                    new_count += 1
            if on_progress:
                on_progress(f"  Found {len(parsed['urls'])} URL(s) ({new_count} new)")

    _crawl(sitemap_url, depth=0)

    logger.info(
        "Sitemap crawl complete: %d unique URLs from %d sitemap(s)",
        len(all_urls), len(visited_sitemaps),
    )
    return all_urls


def discover_sitemap(base_url: str, timeout: int = 30) -> Optional[str]:
    """
    Try to discover the sitemap URL for a given website.
    Checks robots.txt first, then common paths.
    """
    base_url = base_url.rstrip("/")

    robots_url = f"{base_url}/robots.txt"
    try:
        resp = requests.get(robots_url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            for line in resp.text.splitlines():
                if line.strip().lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    if sitemap_url:
                        logger.info("Found sitemap in robots.txt: %s", sitemap_url)
                        return sitemap_url
    except requests.RequestException:
        pass

    for path in _SITEMAP_PATHS:
        url = base_url + path
        try:
            resp = requests.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                logger.info("Found sitemap at: %s", url)
                return url
        except requests.RequestException:
            continue

    return None
