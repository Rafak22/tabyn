"""
Collector 2 — Evaluation Set
Scrapes labeled fact-checks from Misbar and Fatabyyano.
Each record contains: claim, verdict, source_url, cited_source.
Output: data/evaluation_set/evaluation_claims.json
"""

import requests
from bs4 import BeautifulSoup
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.helpers import save_json, merge_with_existing, deduplicate, timestamp, print_summary

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ar,en;q=0.9",
}

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "evaluation_set", "evaluation_claims.json"
)

# Verdict normalization — maps site-specific labels to our 4 standard labels
VERDICT_MAP = {
    # English labels
    "true":              "Confirmed True",
    "false":             "Confirmed False",
    "misleading":        "Misleading",
    "partially true":    "Misleading",
    "partially false":   "Misleading",
    "unverified":        "Not Enough Evidence",
    "not enough evidence": "Not Enough Evidence",
    "satire":            "Misleading",
    # Arabic labels
    "صحيح":              "Confirmed True",
    "خاطئ":              "Confirmed False",
    "مضلل":              "Misleading",
    "صحيح جزئياً":       "Misleading",
    "خاطئ جزئياً":       "Misleading",
    "غير مؤكد":          "Not Enough Evidence",
    "لا يمكن التحقق":   "Not Enough Evidence",
}

def normalize_verdict(raw_verdict):
    if not raw_verdict:
        return "Not Enough Evidence"
    clean = raw_verdict.strip().lower()
    for key, val in VERDICT_MAP.items():
        if key in clean:
            return val
    return raw_verdict.strip()  # Return as-is if not recognized


# ── Misbar ─────────────────────────────────────────────────

MISBAR_PAGES = [
    "https://misbar.com/factcheck/arabic",
    "https://misbar.com/factcheck/arabic?page=2",
    "https://misbar.com/factcheck/arabic?page=3",
]

def collect_misbar():
    claims = []
    print("\n📡 Misbar — Fact-check scraping")
    for page_url in MISBAR_PAGES:
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            # Each fact-check is usually in a card/article element
            cards = soup.find_all(["article", "div"], class_=lambda c: c and "fact" in c.lower())
            if not cards:
                # Fallback: any article tag
                cards = soup.find_all("article")

            for card in cards:
                # Claim text
                claim_tag = card.find(["h2", "h3", "h4"])
                claim = claim_tag.get_text(strip=True) if claim_tag else ""

                # Article URL
                link_tag = card.find("a", href=True)
                art_url = ""
                if link_tag:
                    href = link_tag["href"]
                    art_url = href if href.startswith("http") else f"https://misbar.com{href}"

                # Verdict (often in a badge/label)
                verdict_tag = card.find(class_=lambda c: c and any(
                    v in c.lower() for v in ["verdict", "label", "badge", "rating", "result"]
                ))
                raw_verdict = verdict_tag.get_text(strip=True) if verdict_tag else ""
                verdict = normalize_verdict(raw_verdict)

                # Date
                time_tag = card.find("time")
                published = time_tag.get("datetime", "") if time_tag else ""

                if not claim or not art_url:
                    continue

                claims.append({
                    "source":          "Misbar",
                    "source_url":      art_url,
                    "language":        "ar",
                    "claim":           claim,
                    "verdict":         verdict,
                    "raw_verdict":     raw_verdict,
                    "cited_source":    "",   # filled when visiting the article page
                    "published_at":    published,
                    "collected_at":    timestamp(),
                    "used_for":        "evaluation",
                })

            print(f"   ✓ {page_url.split('?')[0]}... → {len(cards)} cards found")
        except Exception as e:
            print(f"   ✗ Misbar page failed: {e}")

    print(f"   → Total from Misbar: {len(claims)}")
    return claims


# ── Fatabyyano ─────────────────────────────────────────────

FATABYYANO_PAGES = [
    "https://fatabyyano.net/en/newsroom/",
    "https://fatabyyano.net/en/newsroom/page/2/",
    "https://fatabyyano.net/en/newsroom/page/3/",
]

def collect_fatabyyano():
    claims = []
    print("\n📡 Fatabyyano — Fact-check scraping")
    for page_url in FATABYYANO_PAGES:
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")

            cards = soup.find_all("article")
            for card in cards:
                # Claim text
                claim_tag = card.find(["h2", "h3"])
                claim = claim_tag.get_text(strip=True) if claim_tag else ""

                # Article URL
                link_tag = card.find("a", href=True)
                art_url = ""
                if link_tag:
                    href = link_tag["href"]
                    art_url = href if href.startswith("http") else f"https://fatabyyano.net{href}"

                # Verdict
                verdict_tag = card.find(class_=lambda c: c and any(
                    v in c.lower() for v in ["verdict", "label", "badge", "rating", "tag"]
                ))
                raw_verdict = verdict_tag.get_text(strip=True) if verdict_tag else ""
                verdict = normalize_verdict(raw_verdict)

                # Date
                time_tag = card.find("time")
                published = time_tag.get("datetime", "") if time_tag else ""

                if not claim or not art_url:
                    continue

                claims.append({
                    "source":          "Fatabyyano",
                    "source_url":      art_url,
                    "language":        "ar",
                    "claim":           claim,
                    "verdict":         verdict,
                    "raw_verdict":     raw_verdict,
                    "cited_source":    "",
                    "published_at":    published,
                    "collected_at":    timestamp(),
                    "used_for":        "evaluation",
                })

            print(f"   ✓ {page_url} → {len(cards)} cards found")
        except Exception as e:
            print(f"   ✗ Fatabyyano page failed: {e}")

    print(f"   → Total from Fatabyyano: {len(claims)}")
    return claims


# ── Main ───────────────────────────────────────────────────

def run(incremental=True):
    print("=" * 55)
    print("  Collector 2 — Evaluation Set")
    print("=" * 55)

    all_new = []
    all_new += collect_misbar()
    all_new += collect_fatabyyano()

    if incremental:
        final = merge_with_existing(all_new, OUTPUT_PATH)
    else:
        final = deduplicate(all_new, key="source_url")

    save_json(final, OUTPUT_PATH)
    print_summary(final, label="Evaluation Set")

    # Stats on verdict distribution
    from collections import Counter
    verdicts = Counter(c["verdict"] for c in final)
    print("\n  Verdict distribution:")
    for v, count in verdicts.items():
        print(f"    {v}: {count}")

    return final


if __name__ == "__main__":
    run()
