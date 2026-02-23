# Help Link Finder

A Python automation framework that crawls a website (via **sitemap.xml** or **CSV of URLs**), identifies every page containing links to `/help` or `/help/*`, captures **Playwright screenshots** with the help links **highlighted in blue**, and generates a comprehensive **interactive HTML report**.

---

## Features

- **Two Input Modes** — CSV file or Sitemap URL (with auto-discovery via robots.txt)
- **Sitemap Crawler** — Recursively crawls sitemap index files
- **Batch Mode** — Process large sitemaps in configurable batches (e.g. 1000 URLs at a time)
- **Configurable Pattern** — Default matches `/help` and `/help/*`, but any regex can be used
- **Screenshot Capture** — Uses Playwright to take full-page screenshots of pages with help links
- **Help Link Highlighting** — Matched links are outlined in blue with labels directly on the screenshot
- **Interactive HTML Report** — Filterable, searchable report with tabs for entry points, unique targets, all pages, and screenshots
- **Cookie Banner Dismissal** — Auto-dismisses common cookie consent banners before screenshots
- **GitHub Actions Workflow** — Run directly from the Actions tab with configurable inputs
- **CLI Interface** — Rich progress bars and colored output via tqdm and colorama

---

## Project Structure

```
help-link-crawler/
├── main.py                     # CLI entry point
├── requirements.txt            # Python dependencies
├── sample_urls.csv             # Default CSV with URLs
├── README.md
├── src/
│   ├── __init__.py
│   ├── config.py               # Configuration dataclass
│   ├── url_parser.py           # Reads URLs from CSV files
│   ├── sitemap_crawler.py      # Sitemap crawling & auto-discovery
│   ├── page_crawler.py         # Crawls pages & identifies /help links
│   ├── screenshot_capture.py   # Playwright screenshots with highlights
│   └── report_generator.py     # HTML report generation (Jinja2)
├── inputs/                     # Additional sample input files
│   ├── sample_sitemap.xml
│   ├── sample_urls.csv
│   └── README.md
├── reports/                    # Generated HTML reports (output)
├── screenshots/                # Captured screenshots (output)
└── .github/workflows/          # GitHub Actions workflow
```

---

## Installation

### 1. Install Python Dependencies

```bash
cd help-link-crawler
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

---

## Usage

### From a CSV File

```bash
python main.py sample_urls.csv
python main.py ./inputs/sample_urls.csv
```

### From a Sitemap URL

```bash
python main.py --sitemap https://www.example.com/sitemap.xml
```

### Auto-Discover Sitemap from Domain

```bash
python main.py --sitemap https://www.example.com
```

The tool will check `robots.txt` and common paths to find the sitemap automatically.

### Batch Mode (for Large Sitemaps)

```bash
python main.py --sitemap https://www.example.com/sitemap.xml --batch 1 --batch-size 1000
python main.py --sitemap https://www.example.com/sitemap.xml --batch 2 --batch-size 1000
```

### Custom Pattern

Find `/support` links instead of `/help`:

```bash
python main.py sample_urls.csv --pattern "(/support)(/.*)?"
```

### Skip Screenshots (Faster)

```bash
python main.py sample_urls.csv --no-screenshots
```

### Full Options

```bash
python main.py sample_urls.csv \
               --sitemap https://www.example.com/sitemap.xml \
               --batch 1 --batch-size 1000 \
               --pattern "(/help)(/.*)?" \
               --timeout 30 \
               --max-concurrent 15 \
               --viewport-width 1920 \
               --viewport-height 1080 \
               --output-dir ./my_reports \
               --screenshot-dir ./my_screenshots \
               --verbose
```

---

## CLI Options Reference

| Flag | Default | Description |
|------|---------|-------------|
| `csv_file` (positional) | *(optional)* | Path to CSV file with URLs |
| `--sitemap` | | Sitemap URL to crawl (or domain for auto-discovery) |
| `--batch` | | Batch number (1-based) for processing a slice of URLs |
| `--batch-size` | `1000` | Number of URLs per batch |
| `--pattern` | `(/help)(/.*)?$` | Regex to match against link paths |
| `--timeout` | `30` | HTTP request timeout (seconds) |
| `--max-concurrent` | `10` | Max concurrent page crawls |
| `--user-agent` | `HelpLinkFinder/1.0` | Custom User-Agent string |
| `--delay` | `0.25` | Delay between requests in seconds |
| `--verify-ssl` | `False` | Verify SSL certificates |
| `--no-screenshots` | | Skip Playwright screenshot capture |
| `--viewport-width` | `1920` | Browser viewport width |
| `--viewport-height` | `1080` | Browser viewport height |
| `--no-full-page` | | Capture viewport only, not full page |
| `--no-dismiss-cookies` | | Don't auto-dismiss cookie banners |
| `--cookie-selector` | | Custom CSS selector for cookie accept button |
| `--output-dir`, `-o` | `reports` | Output directory for HTML reports |
| `--screenshot-dir` | `screenshots` | Directory for screenshots |
| `--report-name` | auto-generated | Custom report filename |
| `--verbose`, `-v` | | Enable verbose logging |
| `--log-level` | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |

---

## CSV Format

The CSV file should have a header row with a column named `url` (case-insensitive). If no matching header is found, the first column is used.

```csv
url,page_name,category
https://www.example.com,Home Page,main
https://www.example.com/about,About Us,info
https://www.example.com/contact,Contact,info
```

---

## GitHub Actions

This project includes a GitHub Actions workflow (`workflow_dispatch`) with the following inputs:

| Input | Description |
|-------|-------------|
| **Input mode** | Choose `csv` or `sitemap` |
| **CSV file** | Path to CSV file in repo (default: `sample_urls.csv`) |
| **Sitemap URL** | Required when mode is `sitemap` |
| **Pattern** | Regex for matching link paths (default: `/help`) |
| **Batch number** | Leave empty to run all, or set 1, 2, 3... |
| **Batch size** | URLs per batch (default: 1000) |
| **Timeout** | HTTP timeout in seconds |
| **Max concurrent** | Concurrent page crawls |
| **Skip screenshots** | Toggle screenshot capture |

To trigger manually: **Actions** → **Help Link Finder** → **Run workflow**.

The report (HTML + screenshots) is uploaded as an artifact and can be downloaded from the workflow run page.

---

## HTML Report

The generated report includes:

- **Summary Dashboard** — Pages crawled, links scanned, help links found, unique targets, duration
- **Entry Points Tab** — Pages that contain /help links, with details and embedded screenshots
- **Unique Targets Tab** — Deduplicated list of all /help URLs found, with counts of how many pages link to each
- **All Pages Tab** — Overview of every page scanned with link counts
- **Screenshots Tab** — Full-page screenshots with help links highlighted in blue
- **Search & Filter** — Filter by URL or anchor text
- **Lightbox Viewer** — Click any screenshot to view it full-size

---

## How It Works

1. **URL Collection** — Reads page URLs from CSV and/or crawls sitemap (with recursive index support and auto-discovery)
2. **Batch Slicing** — If `--batch` is specified, only the corresponding slice of URLs is processed
3. **Page Crawling** — Fetches each page and extracts all `<a>` links
4. **Pattern Matching** — Each link's resolved path is checked against the pattern (default: `/help` or `/help/*`)
5. **Screenshot Capture** — For pages with matching links, Playwright loads the page, injects CSS to highlight help link elements in blue, and captures a full-page screenshot
6. **Report Generation** — All results and screenshots are compiled into a self-contained HTML report
