"""
Collector 1 — Trusted Sources
Collects from:
  - Al Jazeera Arabic (scraping) ✅
  - BBC Arabic RSS ✅  
  - واس (manual export — see instructions below) ⚠️
  - Al Arabiya (manual export — see instructions below) ⚠️
Output: data/trusted_sources/trusted_articles.json
"""

import feedparser
import requests
from bs4 import BeautifulSoup
import sys, os, time, json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.helpers import save_json, merge_with_existing, deduplicate, timestamp, print_summary

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "trusted_sources", "trusted_articles.json"
)

MANUAL_WAS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "trusted_sources", "manual_was.json"
)

MANUAL_ALARABIYA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "trusted_sources", "manual_alarabiya.json"
)

def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    })
    return s


# ── BBC Arabic RSS ─────────────────────────────────────────
# Open RSS, no blocking, high-quality Arabic news

BBC_FEEDS = {
    "عالم":    "https://feeds.bbci.co.uk/arabic/rss.xml",
    "أخبار":   "https://feeds.bbci.co.uk/arabic/middleeast/rss.xml",
    "اقتصاد":  "https://feeds.bbci.co.uk/arabic/business/rss.xml",
    "علوم":    "https://feeds.bbci.co.uk/arabic/scienceandtech/rss.xml",
}

def collect_bbc_arabic():
    articles = []
    print("\n📡 BBC Arabic — RSS")
    session = make_session()
    for category, url in BBC_FEEDS.items():
        try:
            r = session.get(url, timeout=15)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            count = 0
            for entry in feed.entries:
                title   = entry.get("title", "").strip()
                url_art = entry.get("link", "").strip()
                if not title or not url_art:
                    continue
                articles.append({
                    "source":       "BBC عربي",
                    "source_url":   "https://www.bbc.com/arabic",
                    "language":     "ar",
                    "trusted":      True,
                    "category":     category,
                    "title":        title,
                    "url":          url_art,
                    "summary":      entry.get("summary", "").strip(),
                    "published_at": entry.get("published", ""),
                    "collected_at": timestamp(),
                })
                count += 1
            print(f"   ✓ [{category}] {count} articles")
        except Exception as e:
            print(f"   ✗ [{category}] Failed: {e}")
        time.sleep(0.5)
    print(f"   → Total from BBC Arabic: {len(articles)}")
    return articles


# ── Al Jazeera Arabic — Scraping ───────────────────────────

AJ_SECTIONS = {
    "أخبار":  "https://www.aljazeera.net/news/",
    "اقتصاد": "https://www.aljazeera.net/ebusiness/",
    "علوم":   "https://www.aljazeera.net/science/",
    "صحة":    "https://www.aljazeera.net/news/healthmedicine/",
    "سياسة":  "https://www.aljazeera.net/news/politics/",
}

def collect_aljazeera():
    articles = []
    print("\n📡 Al Jazeera Arabic — Scraping")
    session = make_session()
    for category, url in AJ_SECTIONS.items():
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.find_all("article")
            count = 0
            for card in cards:
                title_tag = card.find(["h2", "h3"])
                title = title_tag.get_text(strip=True) if title_tag else ""
                link_tag = card.find("a", href=True)
                art_url = ""
                if link_tag:
                    href = link_tag["href"]
                    art_url = href if href.startswith("http") else f"https://www.aljazeera.net{href}"
                p_tag = card.find("p")
                summary = p_tag.get_text(strip=True) if p_tag else ""
                time_tag = card.find("time")
                published = time_tag.get("datetime", "") if time_tag else ""
                if not title or not art_url:
                    continue
                articles.append({
                    "source": "الجزيرة", "source_url": "https://www.aljazeera.net",
                    "language": "ar", "trusted": True, "category": category,
                    "title": title, "url": art_url,
                    "summary": summary, "published_at": published,
                    "collected_at": timestamp(),
                })
                count += 1
            print(f"   ✓ [{category}] {count} articles")
            time.sleep(1)
        except Exception as e:
            print(f"   ✗ [{category}] Failed: {e}")
    print(f"   → Total from Al Jazeera: {len(articles)}")
    return articles


# ── واس — Manual JSON loader ───────────────────────────────
# واس uses Cloudflare WAF — blocks automated access.
# Solution: export articles manually using the browser extension
# "JSON Feed Exporter" on https://www.spa.gov.sa/ar/news
# Save the exported file as: data/trusted_sources/manual_was.json

def load_manual_was():
    if not os.path.exists(MANUAL_WAS_PATH):
        print("\n⚠️  واس — Manual file not found.")
        print(f"   Expected: {MANUAL_WAS_PATH}")
        print("   See MANUAL_SOURCES_README.txt for instructions.")
        return []
    with open(MANUAL_WAS_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    articles = []
    for item in raw:
        articles.append({
            "source":       "واس",
            "source_url":   "https://www.spa.gov.sa",
            "language":     "ar",
            "trusted":      True,
            "category":     item.get("category", "عام"),
            "title":        item.get("title", "").strip(),
            "url":          item.get("url", "").strip(),
            "summary":      item.get("summary", "").strip(),
            "published_at": item.get("published_at", ""),
            "collected_at": timestamp(),
        })
    print(f"\n📂 واس (manual) — loaded {len(articles)} articles")
    return articles


# ── Al Arabiya — Manual JSON loader ───────────────────────
# Same Cloudflare issue. Export manually and save as:
# data/trusted_sources/manual_alarabiya.json

def load_manual_alarabiya():
    if not os.path.exists(MANUAL_ALARABIYA_PATH):
        print("\n⚠️  Al Arabiya — Manual file not found.")
        print(f"   Expected: {MANUAL_ALARABIYA_PATH}")
        print("   See MANUAL_SOURCES_README.txt for instructions.")
        return []
    with open(MANUAL_ALARABIYA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    articles = []
    for item in raw:
        articles.append({
            "source":       "العربية",
            "source_url":   "https://www.alarabiya.net",
            "language":     "ar",
            "trusted":      True,
            "category":     item.get("category", "أخبار"),
            "title":        item.get("title", "").strip(),
            "url":          item.get("url", "").strip(),
            "summary":      item.get("summary", "").strip(),
            "published_at": item.get("published_at", ""),
            "collected_at": timestamp(),
        })
    print(f"\n📂 Al Arabiya (manual) — loaded {len(articles)} articles")
    return articles


# ── Main ───────────────────────────────────────────────────

def run(incremental=True):
    print("=" * 55)
    print("  Collector 1 — Trusted Sources")
    print("=" * 55)
    all_new = []
    all_new += collect_bbc_arabic()
    all_new += collect_aljazeera()
    all_new += load_manual_was()
    all_new += load_manual_alarabiya()
    if incremental:
        final = merge_with_existing(all_new, OUTPUT_PATH)
    else:
        final = deduplicate(all_new)
    save_json(final, OUTPUT_PATH)
    print_summary(final, label="Trusted Sources DB")
    return final

if __name__ == "__main__":
    run()
