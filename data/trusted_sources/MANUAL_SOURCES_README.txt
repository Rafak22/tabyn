============================================================
  MANUAL SOURCES — واس & Al Arabiya
  Why manual? Both sites use Cloudflare WAF which blocks
  all automated/script access. They work fine in a browser.
============================================================

OPTION A — Easiest: Use browser developer tools
─────────────────────────────────────────────────
1. Open https://www.spa.gov.sa/ar/news in Chrome/Edge
2. Press F12 → go to "Network" tab
3. Filter by "Fetch/XHR"
4. Scroll down the page to load more articles
5. Look for API calls like /api/news or /getNews
6. Copy the JSON response → save as:
   data/trusted_sources/manual_was.json

For Al Arabiya:
1. Open https://www.alarabiya.net in Chrome/Edge
2. Same steps — look for API calls
3. Save as: data/trusted_sources/manual_alarabiya.json

OPTION B — Chrome Extension
─────────────────────────────────────────────────
Install "Web Scraper" extension (free, chrome web store)
1. Go to https://www.spa.gov.sa/ar/news
2. Create a sitemap targeting article cards
3. Export as JSON
4. Save as: data/trusted_sources/manual_was.json

OPTION C — Just use the format below and paste manually
─────────────────────────────────────────────────
If you copy a few articles manually, use this JSON format:

[
  {
    "title": "عنوان الخبر هنا",
    "url": "https://www.spa.gov.sa/ar/news/...",
    "summary": "ملخص الخبر",
    "published_at": "2026-05-07",
    "category": "عام"
  },
  ...
]

Save this file as: data/trusted_sources/manual_was.json
Same format for Al Arabiya → data/trusted_sources/manual_alarabiya.json

============================================================
NOTE: For the capstone demo, Al Jazeera + BBC Arabic
(auto-collected) is already a solid KB. واس and Al Arabiya
can be added incrementally.
============================================================
