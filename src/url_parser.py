"""
URL Parser Module
-----------------
Reads URLs from CSV files (local or remote).
Supports auto-detecting a 'url' column header or falling back to the first column.
"""

import csv
import logging
import os
from typing import List
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


def read_urls_from_csv(csv_path: str) -> List[str]:
    """
    Read URLs from a CSV file.

    If a column named 'url' (case-insensitive) exists it will be used;
    otherwise the first column is taken. Blank rows and duplicates are skipped.
    """
    urls: List[str] = []
    seen: set = set()

    content = _fetch_content(csv_path)
    lines = content.strip().split("\n")

    if not lines:
        logger.warning("CSV file is empty")
        return urls

    reader = csv.reader(lines)
    url_col = 0

    first_row = next(reader, None)
    if first_row is None:
        return urls

    is_header = False
    for idx, col_name in enumerate(first_row):
        if col_name.strip().lower() == "url":
            url_col = idx
            is_header = True
            break

    if not is_header:
        candidate = first_row[0].strip()
        if _is_valid_url(candidate):
            if candidate not in seen:
                seen.add(candidate)
                urls.append(candidate)
        else:
            is_header = True

    for row in reader:
        if len(row) > url_col:
            val = row[url_col].strip()
            if val and _is_valid_url(val) and val not in seen:
                seen.add(val)
                urls.append(val)

    logger.info("Read %d URL(s) from CSV: %s", len(urls), csv_path)
    return urls


def _fetch_content(source: str) -> str:
    """Fetch content from a URL or local file."""
    if source.startswith("http://") or source.startswith("https://"):
        logger.info("Fetching remote source: %s", source)
        response = requests.get(source, timeout=30, headers={
            "User-Agent": "HelpLinkFinder/1.0"
        })
        response.raise_for_status()
        return response.text
    else:
        abs_path = os.path.abspath(source)
        logger.info("Reading local file: %s", abs_path)
        with open(abs_path, "r", encoding="utf-8-sig") as f:
            return f.read()


def _is_valid_url(url: str) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    try:
        result = urlparse(url)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False
