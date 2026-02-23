#!/usr/bin/env python3
"""
Help Link Finder — Main Entry Point
====================================

Usage:
    python main.py urls.csv                                    # from CSV file
    python main.py --sitemap https://example.com/sitemap.xml   # from sitemap
    python main.py --sitemap https://example.com               # auto-discover sitemap
    python main.py urls.csv -o results                         # custom output dir

Batch mode (run 1000 URLs at a time from a large sitemap):
    python main.py --sitemap https://example.com/sitemap.xml --batch 1 --batch-size 1000
"""

import argparse
import logging
import os
import sys
import time
import warnings
from datetime import datetime

import urllib3
from colorama import init, Fore, Style
from tqdm import tqdm

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message=".*SSL.*")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import FinderConfig
from src.url_parser import read_urls_from_csv
from src.sitemap_crawler import crawl_sitemap, discover_sitemap
from src.page_crawler import PageCrawler
from src.screenshot_capture import ScreenshotCapture
from src.report_generator import ReportGenerator

init(autoreset=True)


def setup_logging(level: str = "INFO", verbose: bool = False):
    """Configure logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s" if verbose else "%(message)s"
    logging.basicConfig(level=log_level, format=fmt, datefmt="%H:%M:%S")


def print_banner():
    """Print a styled banner."""
    banner = f"""
{Fore.CYAN}{Style.BRIGHT}
 _   _      _        _     _       _      _____ _           _
| | | | ___| |_ __  | |   (_)_ __ | | __ |  ___(_)_ __   __| | ___ _ __
| |_| |/ _ \\ | '_ \\ | |   | | '_ \\| |/ / | |_  | | '_ \\ / _` |/ _ \\ '__|
|  _  |  __/ | |_) || |___| | | | |   <  |  _| | | | | | (_| |  __/ |
|_| |_|\\___|_| .__/ |_____|_|_| |_|_|\\_\\ |_|   |_|_| |_|\\__,_|\\___|_|
             |_|
{Style.RESET_ALL}\
{Fore.WHITE}  Crawl pages and find all entry points linking to /help{Style.RESET_ALL}
{Fore.WHITE}  ──────────────────────────────────────────────────────{Style.RESET_ALL}
"""
    print(banner)


def _sitemap_progress(message: str):
    print(f"  {message}")


def parse_arguments() -> FinderConfig:
    """Parse command-line arguments and return a FinderConfig."""
    parser = argparse.ArgumentParser(
        description="Help Link Finder — Crawl pages and find all links to /help or /help/*. "
                    "Input via CSV file or sitemap URL.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py urls.csv
  python main.py --sitemap https://example.com/sitemap.xml
  python main.py --sitemap https://example.com
  python main.py --sitemap https://example.com/sitemap.xml --batch 1 --batch-size 1000
  python main.py urls.csv --no-screenshots --verbose
        """,
    )

    # ── Input ──
    parser.add_argument(
        "csv_file", nargs="?", default=None,
        help="Path to a CSV file containing URLs (optional if --sitemap is used).",
    )
    parser.add_argument(
        "--sitemap", metavar="URL",
        help="Sitemap URL to crawl. If a base domain is given, the sitemap is auto-discovered.",
    )

    # ── Batching ──
    parser.add_argument(
        "--batch", type=int, default=None, metavar="N",
        help="Batch number to run (1-based). Use with --batch-size.",
    )
    parser.add_argument(
        "--batch-size", type=int, default=1000,
        help="Number of URLs per batch (default: 1000).",
    )

    # ── Crawling ──
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds (default: 30)")
    parser.add_argument("--max-concurrent", type=int, default=10, help="Max concurrent checks (default: 10)")
    parser.add_argument("--user-agent", default="HelpLinkFinder/1.0", help="Custom User-Agent string")
    parser.add_argument("--verify-ssl", action="store_true", help="Verify SSL certificates (default: skip)")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between page requests in seconds (default: 0.25)")

    # ── Pattern ──
    parser.add_argument(
        "--pattern", default=r"(/help)(/.*)?$",
        help="Regex to match against link paths (default: (/help)(/.*)?$)",
    )

    # ── Screenshots ──
    parser.add_argument("--no-screenshots", action="store_true", help="Skip screenshot capture")
    parser.add_argument("--viewport-width", type=int, default=1920, help="Browser viewport width (default: 1920)")
    parser.add_argument("--viewport-height", type=int, default=1080, help="Browser viewport height (default: 1080)")
    parser.add_argument("--no-full-page", action="store_true", help="Capture only viewport, not full page")

    # ── Cookie consent ──
    parser.add_argument("--no-dismiss-cookies", action="store_true", help="Do NOT auto-dismiss cookie banners")
    parser.add_argument("--cookie-selector", default=None, help="Custom CSS selector for cookie accept button")

    # ── Output ──
    parser.add_argument("--output-dir", "-o", default="reports", help="Output directory (default: reports)")
    parser.add_argument("--screenshot-dir", default="screenshots", help="Screenshot directory (default: screenshots)")
    parser.add_argument("--report-name", default=None, help="Custom report filename")

    # ── Logging ──
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])

    args = parser.parse_args()

    if not args.csv_file and not args.sitemap:
        parser.error("Provide either a CSV file or --sitemap URL.")

    return FinderConfig(
        csv_file=args.csv_file,
        sitemap_url=args.sitemap,
        batch=args.batch,
        batch_size=args.batch_size,
        timeout=args.timeout,
        max_concurrent=args.max_concurrent,
        user_agent=args.user_agent,
        verify_ssl=args.verify_ssl,
        delay=args.delay,
        pattern=args.pattern,
        take_screenshots=not args.no_screenshots,
        viewport_width=args.viewport_width,
        viewport_height=args.viewport_height,
        full_page_screenshot=not args.no_full_page,
        screenshot_timeout=args.timeout * 1000,
        dismiss_cookies=not args.no_dismiss_cookies,
        cookie_selector=args.cookie_selector,
        output_dir=args.output_dir,
        screenshot_dir=args.screenshot_dir,
        report_filename=args.report_name,
        log_level=args.log_level,
        verbose=args.verbose,
    )


def run(config: FinderConfig):
    """Run the full help link finding pipeline."""
    start_time = time.time()

    # ── Step 1: Collect URLs ──
    print(f"\n{Fore.CYAN}[1/4] Collecting URLs...{Style.RESET_ALL}")
    urls = []

    if config.csv_file:
        if not os.path.isfile(config.csv_file):
            print(f"{Fore.RED}Error: CSV file not found: {config.csv_file}{Style.RESET_ALL}", file=sys.stderr)
            sys.exit(1)
        print(f"  Reading URLs from CSV: {config.csv_file}")
        urls.extend(read_urls_from_csv(config.csv_file))

    if config.sitemap_url:
        sitemap_url = config.sitemap_url.strip()

        if not sitemap_url.endswith(".xml"):
            print(f"\n  Discovering sitemap for: {sitemap_url}")
            discovered = discover_sitemap(sitemap_url, timeout=config.timeout)
            if discovered:
                print(f"  Found sitemap: {discovered}")
                sitemap_url = discovered
            else:
                sitemap_url = sitemap_url.rstrip("/") + "/sitemap.xml"
                print(f"  Auto-discovery failed, trying: {sitemap_url}")

        print(f"\n  Crawling sitemap: {sitemap_url}")
        sitemap_urls = crawl_sitemap(
            sitemap_url, timeout=config.timeout, on_progress=_sitemap_progress,
        )
        existing = set(urls)
        new_count = 0
        for u in sitemap_urls:
            if u not in existing:
                existing.add(u)
                urls.append(u)
                new_count += 1
        print(f"\n  Sitemap contributed {new_count} new URL(s).")

    if not urls:
        print(f"{Fore.YELLOW}  No URLs found. Exiting.{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(0)

    total_urls = len(urls)
    print(f"  {Fore.GREEN}Total: {total_urls} unique URL(s) found.{Style.RESET_ALL}")

    # ── Apply batch slicing ──
    if config.batch is not None:
        batch_num = config.batch
        batch_size = config.batch_size
        if batch_num < 1:
            print(f"{Fore.RED}Error: --batch must be >= 1.{Style.RESET_ALL}", file=sys.stderr)
            sys.exit(1)

        total_batches = (total_urls + batch_size - 1) // batch_size
        start_idx = (batch_num - 1) * batch_size
        end_idx = min(start_idx + batch_size, total_urls)

        if start_idx >= total_urls:
            print(
                f"  {Fore.RED}Batch {batch_num} is out of range "
                f"(only {total_batches} batch(es) of {batch_size}).{Style.RESET_ALL}",
                file=sys.stderr,
            )
            sys.exit(1)

        urls = urls[start_idx:end_idx]
        print(
            f"  Batch {batch_num}/{total_batches}: "
            f"URLs {start_idx + 1}–{end_idx} of {total_urls} "
            f"({len(urls)} URLs in this batch).\n"
        )
    else:
        print()

    for i, url in enumerate(urls[:5]):
        print(f"    {Fore.WHITE}{i + 1}. {url}{Style.RESET_ALL}")
    if len(urls) > 5:
        print(f"    {Fore.WHITE}... and {len(urls) - 5} more{Style.RESET_ALL}")

    # ── Step 2: Crawl Pages ──
    print(f"\n{Fore.CYAN}[2/4] Crawling pages for /help links (pattern: {config.pattern})...{Style.RESET_ALL}")
    crawler = PageCrawler(
        pattern=config.pattern,
        timeout=config.timeout,
        max_concurrent=config.max_concurrent,
        user_agent=config.user_agent,
        verify_ssl=config.verify_ssl,
        delay=config.delay,
    )

    progress_bar = tqdm(total=len(urls), desc="  Crawling pages", unit="page", colour="cyan")

    def crawl_progress(current, total, url):
        progress_bar.update(1)
        progress_bar.set_postfix_str(url[:60] + "..." if len(url) > 60 else url)

    page_results = crawler.crawl_pages(urls, progress_callback=crawl_progress)
    progress_bar.close()

    total_help = sum(len(pr.help_links) for pr in page_results)
    total_links = sum(pr.total_links for pr in page_results)
    pages_with_help = sum(1 for pr in page_results if pr.help_links)

    print(f"\n  {Fore.WHITE}Links scanned: {total_links}{Style.RESET_ALL}")
    if total_help > 0:
        print(f"  {Fore.CYAN}Help links found: {total_help} across {pages_with_help} page(s){Style.RESET_ALL}")
    else:
        print(f"  {Fore.GREEN}No help links found on any page.{Style.RESET_ALL}")

    # ── Step 3: Capture Screenshots ──
    screenshot_results = []
    if config.take_screenshots and total_help > 0:
        print(f"\n{Fore.CYAN}[3/4] Capturing screenshots with highlighted help links...{Style.RESET_ALL}")

        cookie_selectors = None
        if config.cookie_selector:
            cookie_selectors = [config.cookie_selector] + ScreenshotCapture.DEFAULT_COOKIE_SELECTORS

        capturer = ScreenshotCapture(
            output_dir=config.screenshot_dir,
            viewport_width=config.viewport_width,
            viewport_height=config.viewport_height,
            full_page=config.full_page_screenshot,
            timeout=config.screenshot_timeout,
            dismiss_cookies=config.dismiss_cookies,
            cookie_selectors=cookie_selectors,
        )

        pages_needing_ss = [pr for pr in page_results if pr.help_links]
        ss_bar = tqdm(total=len(pages_needing_ss), desc="  Screenshots", unit="page", colour="yellow")

        def ss_progress(current, total, url):
            ss_bar.update(1)

        screenshot_results = capturer.capture_pages_with_help_links(
            page_results, progress_callback=ss_progress,
        )
        ss_bar.close()

        captured = sum(1 for s in screenshot_results if s.success)
        print(f"  {Fore.GREEN}Captured {captured}/{len(screenshot_results)} screenshots{Style.RESET_ALL}")
    else:
        if not config.take_screenshots:
            print(f"\n{Fore.YELLOW}[3/4] Screenshot capture skipped (--no-screenshots){Style.RESET_ALL}")
        else:
            print(f"\n{Fore.GREEN}[3/4] No help links — screenshots not needed{Style.RESET_ALL}")

    # ── Step 4: Generate Report ──
    print(f"\n{Fore.CYAN}[4/4] Generating HTML report...{Style.RESET_ALL}")
    reporter = ReportGenerator(output_dir=config.output_dir)

    source_label = config.csv_file or config.sitemap_url or "unknown"
    batch_suffix = f"_batch{config.batch}" if config.batch is not None else ""
    report_filename = config.report_filename
    if report_filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"help_links_report_{timestamp}{batch_suffix}.html"

    report_path = reporter.generate(
        page_results=page_results,
        screenshot_results=screenshot_results,
        source_file=source_label,
        pattern=config.pattern,
        report_filename=report_filename,
    )

    elapsed = time.time() - start_time
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    print(f"\n{'=' * 60}")
    print(f"{Fore.GREEN}{Style.BRIGHT}  DONE!{Style.RESET_ALL}")
    print(f"{'=' * 60}")
    print(f"  Pages crawled:      {len(urls)}")
    print(f"  Links scanned:      {total_links}")
    print(f"  Help links found:   {Fore.CYAN}{total_help}{Style.RESET_ALL}")
    print(f"  Pages with /help:   {Fore.YELLOW}{pages_with_help}{Style.RESET_ALL}")
    print(f"  Duration:           {minutes}m {seconds}s" if minutes else f"  Duration:           {seconds}s")
    print(f"  Report:             {Fore.CYAN}{report_path}{Style.RESET_ALL}")
    if config.batch is not None:
        print(f"  Batch:              {config.batch} (size {config.batch_size})")
    print(f"{'=' * 60}\n")

    return report_path


def main():
    """Main entry point."""
    print_banner()
    config = parse_arguments()
    setup_logging(config.log_level, config.verbose)
    run(config)


if __name__ == "__main__":
    main()
