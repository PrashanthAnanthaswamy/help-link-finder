"""
Report Generator Module
-----------------------
Generates a beautiful, interactive HTML report of the help link finder results.
"""

import os
import logging
from datetime import datetime
from typing import List
from jinja2 import Template

logger = logging.getLogger(__name__)

HTML_TEMPLATE = Template(r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Help Link Finder Report</title>
    <style>
        :root {
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #1e293b;
            --bg-card-hover: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #2563eb;
            --accent-light: #60a5fa;
            --info: #0ea5e9;
            --info-light: #7dd3fc;
            --success: #22c55e;
            --success-light: #86efac;
            --warning: #f59e0b;
            --warning-light: #fcd34d;
            --border: #334155;
            --shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 24px; }

        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 32px;
            box-shadow: var(--shadow);
        }
        .header h1 { font-size: 2rem; font-weight: 700; margin-bottom: 8px; }
        .header .subtitle { color: var(--text-secondary); font-size: 0.95rem; }
        .header .pattern-info {
            margin-top: 12px;
            padding: 8px 16px;
            background: rgba(37, 99, 235, 0.15);
            border-radius: 8px;
            font-family: 'Fira Code', monospace;
            font-size: 0.88rem;
            color: var(--accent-light);
            display: inline-block;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }
        .summary-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: var(--shadow);
            transition: transform 0.2s;
        }
        .summary-card:hover { transform: translateY(-2px); }
        .summary-card .number { font-size: 2.5rem; font-weight: 800; line-height: 1.2; }
        .summary-card .label {
            font-size: 0.85rem; color: var(--text-secondary);
            text-transform: uppercase; letter-spacing: 1px; margin-top: 8px;
        }
        .number.accent { color: var(--accent-light); }
        .number.info { color: var(--info-light); }
        .number.success { color: var(--success); }
        .number.warning { color: var(--warning); }

        .tabs { display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 2px solid var(--border); padding-bottom: 8px; }
        .tab-btn {
            background: transparent; color: var(--text-secondary); border: none;
            padding: 10px 20px; font-size: 0.95rem; cursor: pointer;
            border-radius: 8px 8px 0 0; transition: all 0.2s;
        }
        .tab-btn:hover { color: var(--text-primary); background: var(--bg-secondary); }
        .tab-btn.active { color: var(--accent-light); background: var(--bg-secondary); border-bottom: 2px solid var(--accent); }
        .tab-content { display: none; }
        .tab-content.active { display: block; }

        .filter-bar { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; align-items: center; }
        .filter-bar input, .filter-bar select {
            background: var(--bg-secondary); border: 1px solid var(--border);
            color: var(--text-primary); padding: 10px 16px; border-radius: 8px; font-size: 0.9rem;
        }
        .filter-bar input { flex: 1; min-width: 260px; }

        .page-card {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; margin-bottom: 20px; overflow: hidden; box-shadow: var(--shadow);
        }
        .page-card-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 20px 24px; cursor: pointer; transition: background 0.2s;
            flex-wrap: wrap; gap: 12px;
        }
        .page-card-header:hover { background: var(--bg-card-hover); }
        .page-url { font-weight: 600; font-size: 1rem; word-break: break-all; color: var(--accent-light); }
        .page-url a { color: inherit; text-decoration: none; }
        .page-url a:hover { text-decoration: underline; }

        .badge {
            display: inline-flex; align-items: center; padding: 4px 12px;
            border-radius: 20px; font-size: 0.78rem; font-weight: 700; white-space: nowrap;
        }
        .badge-info { background: rgba(14,165,233,0.15); color: var(--info-light); }
        .badge-success { background: rgba(34,197,94,0.15); color: var(--success-light); }
        .badge-warning { background: rgba(245,158,11,0.15); color: var(--warning-light); }

        .page-card-body { display: none; border-top: 1px solid var(--border); }
        .page-card.open .page-card-body { display: block; }

        .link-table { width: 100%; border-collapse: collapse; }
        .link-table th {
            text-align: left; padding: 12px 24px; font-size: 0.78rem;
            text-transform: uppercase; letter-spacing: 1px; color: var(--text-muted);
            background: var(--bg-primary); border-bottom: 1px solid var(--border);
        }
        .link-table td {
            padding: 14px 24px; font-size: 0.88rem; border-bottom: 1px solid var(--border);
            color: var(--text-secondary); vertical-align: top;
        }
        .link-table tr:last-child td { border-bottom: none; }
        .link-table tr:hover td { background: rgba(37,99,235,0.05); }
        .link-url {
            color: var(--info-light); word-break: break-all;
            font-family: 'Fira Code', monospace; font-size: 0.82rem;
        }
        .link-url a { color: inherit; text-decoration: none; }
        .link-url a:hover { text-decoration: underline; }

        .page-stats { display: flex; gap: 16px; padding: 8px 24px 16px; flex-wrap: wrap; }
        .page-stat { font-size: 0.82rem; color: var(--text-muted); }
        .page-stat strong { color: var(--text-secondary); }

        .screenshot-section {
            padding: 24px; border-top: 1px solid var(--border); background: var(--bg-primary);
        }
        .screenshot-section h4 {
            font-size: 0.85rem; color: var(--text-muted);
            text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px;
        }
        .screenshot-container {
            border: 2px solid var(--border); border-radius: 8px;
            overflow: hidden; max-height: 600px; overflow-y: auto;
        }
        .screenshot-container img { width: 100%; display: block; }

        .modal-overlay {
            display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.85);
            z-index: 10000; justify-content: center; align-items: center; cursor: zoom-out;
        }
        .modal-overlay.active { display: flex; }
        .modal-overlay img { max-width: 95vw; max-height: 95vh; border-radius: 8px; box-shadow: 0 10px 40px rgba(0,0,0,0.5); }

        .unique-targets {
            background: var(--bg-card); border: 1px solid var(--border);
            border-radius: 12px; padding: 24px; margin-bottom: 20px;
        }
        .unique-targets h3 { margin-bottom: 16px; color: var(--text-primary); font-size: 1.1rem; }
        .target-list { list-style: none; }
        .target-list li {
            padding: 8px 16px; border-bottom: 1px solid var(--border);
            font-family: 'Fira Code', monospace; font-size: 0.85rem;
        }
        .target-list li:last-child { border-bottom: none; }
        .target-list a { color: var(--info-light); text-decoration: none; }
        .target-list a:hover { text-decoration: underline; }
        .target-count {
            display: inline-block; background: rgba(14,165,233,0.15); color: var(--info-light);
            padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; margin-left: 8px;
        }

        .scroll-top {
            position: fixed; bottom: 24px; right: 24px; background: var(--accent);
            color: white; border: none; width: 48px; height: 48px; border-radius: 50%;
            font-size: 1.4rem; cursor: pointer; box-shadow: 0 4px 12px rgba(37,99,235,0.4);
            display: none; z-index: 9999;
        }

        @media (max-width: 768px) {
            .container { padding: 12px; }
            .header { padding: 24px; }
            .header h1 { font-size: 1.5rem; }
            .link-table th, .link-table td { padding: 10px 12px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>&#128270; Help Link Finder Report</h1>
            <p class="subtitle">
                Generated on {{ report_date }} &mdash; Source: <code>{{ source_file }}</code>
            </p>
            <div class="pattern-info">Pattern: {{ pattern }}</div>
        </div>

        <div class="summary-grid">
            <div class="summary-card">
                <div class="number accent">{{ total_pages }}</div>
                <div class="label">Pages Crawled</div>
            </div>
            <div class="summary-card">
                <div class="number success">{{ total_links_scanned }}</div>
                <div class="label">Total Links Scanned</div>
            </div>
            <div class="summary-card">
                <div class="number info">{{ total_help_links }}</div>
                <div class="label">Help Links Found</div>
            </div>
            <div class="summary-card">
                <div class="number warning">{{ pages_with_help }}</div>
                <div class="label">Pages with /help</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: var(--info-light);">{{ unique_target_count }}</div>
                <div class="label">Unique /help Targets</div>
            </div>
            <div class="summary-card">
                <div class="number" style="color: var(--text-secondary);">{{ total_duration }}</div>
                <div class="label">Duration</div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('help')">Entry Points ({{ pages_with_help }})</button>
            <button class="tab-btn" onclick="switchTab('targets')">Unique Targets ({{ unique_target_count }})</button>
            <button class="tab-btn" onclick="switchTab('all')">All Pages ({{ total_pages }})</button>
            <button class="tab-btn" onclick="switchTab('screenshots')">Screenshots ({{ screenshot_count }})</button>
        </div>

        <div class="filter-bar">
            <input type="text" id="searchInput" placeholder="Search by URL, anchor text..." oninput="filterCards()">
        </div>

        <!-- ENTRY POINTS TAB -->
        <div id="tab-help" class="tab-content active">
            {% for page in pages_with_help_links %}
            <div class="page-card" data-page-url="{{ page.page_url }}">
                <div class="page-card-header" onclick="toggleCard(this)">
                    <div>
                        <span class="page-url"><a href="{{ page.page_url }}" target="_blank">{{ page.page_url }}</a></span>
                    </div>
                    <span class="badge badge-info">{{ page.help_links | length }} help link(s)</span>
                </div>
                <div class="page-card-body">
                    <div class="page-stats">
                        <span class="page-stat">Total links on page: <strong>{{ page.total_links }}</strong></span>
                        <span class="page-stat">Duration: <strong>{{ "%.1f" | format(page.crawl_duration) }}s</strong></span>
                        <span class="page-stat">Page HTTP: <strong>{{ page.page_status_code or 'N/A' }}</strong></span>
                    </div>
                    <table class="link-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Help Link URL</th>
                                <th>Anchor Text</th>
                                <th>Raw href</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for link in page.help_links %}
                            <tr>
                                <td>{{ loop.index }}</td>
                                <td class="link-url"><a href="{{ link.url }}" target="_blank">{{ link.url }}</a></td>
                                <td>{{ link.anchor_text }}</td>
                                <td style="font-family:monospace;font-size:0.82rem;color:var(--text-muted);">{{ link.raw_href }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>

                    {% if page.screenshot_path %}
                    <div class="screenshot-section">
                        <h4>&#128247; Page Screenshot (help links highlighted in blue)</h4>
                        <div class="screenshot-container">
                            <img src="{{ page.screenshot_path }}"
                                 alt="Screenshot of {{ page.page_url }}"
                                 onclick="openModal(this.src)"
                                 style="cursor: zoom-in;">
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}

            {% if not pages_with_help_links %}
            <div style="text-align:center; padding:60px 20px; color: var(--success);">
                <div style="font-size:3rem; margin-bottom:16px;">&#9989;</div>
                <h2>No Help Links Found</h2>
                <p style="color: var(--text-muted); margin-top:8px;">
                    None of the {{ total_pages }} pages scanned contain links matching the pattern.
                </p>
            </div>
            {% endif %}
        </div>

        <!-- UNIQUE TARGETS TAB -->
        <div id="tab-targets" class="tab-content">
            <div class="unique-targets">
                <h3>All Unique /help Target URLs</h3>
                <ul class="target-list">
                    {% for target in unique_targets %}
                    <li>
                        <a href="{{ target.url }}" target="_blank">{{ target.url }}</a>
                        <span class="target-count">found on {{ target.count }} page(s)</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>

        <!-- ALL PAGES TAB -->
        <div id="tab-all" class="tab-content">
            {% for page in all_pages %}
            <div class="page-card" data-page-url="{{ page.page_url }}">
                <div class="page-card-header" onclick="toggleCard(this)">
                    <div>
                        <span class="page-url"><a href="{{ page.page_url }}" target="_blank">{{ page.page_url }}</a></span>
                    </div>
                    <div>
                        {% if page.help_links %}
                        <span class="badge badge-info">{{ page.help_links | length }} help link(s)</span>
                        {% else %}
                        <span class="badge badge-success">&#10003; No help links</span>
                        {% endif %}
                        <span class="badge" style="background:rgba(37,99,235,0.15);color:var(--accent-light);">{{ page.total_links }} links</span>
                    </div>
                </div>
                <div class="page-card-body">
                    <div class="page-stats">
                        <span class="page-stat">Total links: <strong>{{ page.total_links }}</strong></span>
                        <span class="page-stat">Help links: <strong>{{ page.help_links | length }}</strong></span>
                        <span class="page-stat">Duration: <strong>{{ "%.1f" | format(page.crawl_duration) }}s</strong></span>
                        <span class="page-stat">Page HTTP: <strong>{{ page.page_status_code or 'N/A' }}</strong></span>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- SCREENSHOTS TAB -->
        <div id="tab-screenshots" class="tab-content">
            {% for ss in screenshots %}
            <div class="page-card">
                <div class="page-card-header" onclick="toggleCard(this)">
                    <span class="page-url"><a href="{{ ss.page_url }}" target="_blank">{{ ss.page_url }}</a></span>
                    {% if ss.success %}
                    <span class="badge badge-success">Captured</span>
                    {% else %}
                    <span class="badge badge-warning">Failed</span>
                    {% endif %}
                </div>
                <div class="page-card-body">
                    {% if ss.success and ss.screenshot_path %}
                    <div class="screenshot-section">
                        <h4>&#128247; Page Screenshot with Help Links Highlighted</h4>
                        <div class="screenshot-container">
                            <img src="{{ ss.screenshot_path }}"
                                 alt="Screenshot of {{ ss.page_url }}"
                                 onclick="openModal(this.src)"
                                 style="cursor: zoom-in;">
                        </div>
                    </div>
                    {% elif ss.error_message %}
                    <div style="padding:24px; color: var(--warning-light);">
                        Error: {{ ss.error_message }}
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}

            {% if not screenshots %}
            <div style="text-align:center; padding:60px 20px; color: var(--text-muted);">
                <div style="font-size:3rem; margin-bottom:16px;">&#128247;</div>
                <p>No screenshots captured.</p>
            </div>
            {% endif %}
        </div>
    </div>

    <div class="modal-overlay" id="imageModal" onclick="closeModal()">
        <img src="" alt="Full screenshot" id="modalImage">
    </div>

    <button class="scroll-top" id="scrollTopBtn" onclick="window.scrollTo({top:0,behavior:'smooth'})">&#8593;</button>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
        }
        function toggleCard(header) { header.parentElement.classList.toggle('open'); }
        function filterCards() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.page-card').forEach(card => {
                const text = card.textContent.toLowerCase();
                card.style.display = (!search || text.includes(search)) ? '' : 'none';
            });
        }
        function openModal(src) {
            document.getElementById('modalImage').src = src;
            document.getElementById('imageModal').classList.add('active');
        }
        function closeModal() { document.getElementById('imageModal').classList.remove('active'); }
        document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });
        window.addEventListener('scroll', () => {
            document.getElementById('scrollTopBtn').style.display = window.scrollY > 400 ? 'block' : 'none';
        });
        const firstEntry = document.querySelector('#tab-help .page-card');
        if (firstEntry) firstEntry.classList.add('open');
    </script>
</body>
</html>
""")


class ReportGenerator:
    """Generates HTML reports for help link finder results."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(
        self,
        page_results: list,
        screenshot_results: list,
        source_file: str,
        pattern: str,
        report_filename: str = None,
    ) -> str:
        """Generate an HTML report and return its path."""
        if report_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"help_links_report_{timestamp}.html"

        report_path = os.path.join(self.output_dir, report_filename)
        report_dir = os.path.dirname(os.path.abspath(report_path))

        screenshot_map = {}
        for ss in screenshot_results:
            if ss.success and ss.screenshot_path and os.path.exists(ss.screenshot_path):
                rel_path = os.path.relpath(
                    os.path.abspath(ss.screenshot_path), report_dir,
                )
                screenshot_map[ss.page_url] = rel_path

        pages_with_help_links = []
        all_pages_data = []
        total_links_scanned = 0
        total_help_links = 0
        total_duration = 0.0
        target_counts: dict = {}

        for pr in page_results:
            total_links_scanned += pr.total_links
            total_help_links += len(pr.help_links)
            total_duration += pr.crawl_duration

            for hl in pr.help_links:
                normalized = hl.url.split("?")[0].split("#")[0].rstrip("/")
                target_counts[normalized] = target_counts.get(normalized, 0) + 1

            page_data = {
                "page_url": pr.page_url,
                "total_links": pr.total_links,
                "help_links": [
                    {
                        "url": hl.url,
                        "anchor_text": hl.anchor_text,
                        "raw_href": hl.raw_href,
                    }
                    for hl in pr.help_links
                ],
                "crawl_duration": pr.crawl_duration,
                "page_status_code": pr.page_status_code,
                "page_error": pr.page_error,
                "screenshot_path": screenshot_map.get(pr.page_url, ""),
            }

            all_pages_data.append(page_data)
            if pr.help_links:
                pages_with_help_links.append(page_data)

        unique_targets = sorted(
            [{"url": url, "count": count} for url, count in target_counts.items()],
            key=lambda x: (-x["count"], x["url"]),
        )

        minutes = int(total_duration // 60)
        seconds = int(total_duration % 60)
        duration_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        html = HTML_TEMPLATE.render(
            report_date=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
            source_file=source_file,
            pattern=pattern,
            total_pages=len(page_results),
            total_links_scanned=total_links_scanned,
            total_help_links=total_help_links,
            pages_with_help=len(pages_with_help_links),
            unique_target_count=len(unique_targets),
            total_duration=duration_str,
            pages_with_help_links=pages_with_help_links,
            unique_targets=unique_targets,
            all_pages=all_pages_data,
            screenshots=[
                {
                    "page_url": ss.page_url,
                    "screenshot_path": screenshot_map.get(ss.page_url, ""),
                    "success": ss.success,
                    "error_message": ss.error_message,
                }
                for ss in screenshot_results
            ],
            screenshot_count=len([s for s in screenshot_results if s.success]),
        )

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("Report generated: %s", report_path)
        return report_path
