"""
تبيَّن — Auto-Update Script
=============================
Downloads fresh tweets from Apify tasks daily,
merges with existing KB, and rebuilds the vector DB.

Run manually:      python update_kb.py
Run automatically: Add to Windows Task Scheduler
"""

import requests
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────
# CONFIG — fill these in!
# ─────────────────────────────────────────

APIFY_TOKEN = "apify_api_yeHiEqoX1k5z7Ci3uIqUZFuaCm5WBl0ZUab5"  # ← paste Fatimah's token here

TASK_IDS = {
    "SaudiNews50":   "beloved_neighborhood~saudinews50-task",
    "واس المناطق":   "beloved_neighborhood~sparegions-task",
    "وزارة التعليم": "beloved_neighborhood~moe-gov-sa-task",
}

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(BASE_DIR, "data", "trusted_sources", "xtweets_was.json")

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def download_task(task_id: str, source_name: str) -> list:
    # Always fetches the LATEST run's dataset automatically
    url = f"https://api.apify.com/v2/actor-tasks/{task_id}/runs/last/dataset/items?token={APIFY_TOKEN}&format=json&clean=true"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        tweets = r.json()
        print(f"   ✓ {source_name}: {len(tweets)} tweets downloaded")
        return tweets
    except Exception as e:
        print(f"   ✗ {source_name}: {e}")
        return []


def convert_tweets(tweets: list, source_name: str) -> list:
    converted = []
    for t in tweets:
        if t.get("isRetweet"):
            continue
        text = t.get("full_text") or t.get("text", "")
        text = text.strip()
        clean = re.sub(r'https://t\.co/\S+', '', text)
        clean = re.sub(r'#\w+', '', clean)
        clean = re.sub(r'RT @\w+:', '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if len(clean) < 10:
            continue
        sentences = re.split(r'[.!؟\n]', clean)
        title = next((s.strip() for s in sentences if len(s.strip()) > 10), clean[:150])

        # Scweet field names
        author = t.get("author_name") or t.get("user", {}).get("screen_name", "")
        tweet_url = t.get("tweet_url") or t.get("url", "")

        converted.append({
            "source":       source_name,
            "source_url":   f"https://x.com/{author}",
            "language":     "ar",
            "trusted":      True,
            "category":     "أخبار",
            "title":        title[:200],
            "url":          tweet_url,
            "summary":      clean[:500],
            "full_text":    clean,
            "published_at": t.get("created_at") or t.get("createdAt", ""),
            "collected_at": datetime.now(timezone(timedelta(hours=3))).isoformat(),
            "likes":        t.get("favorite_count") or t.get("likeCount", 0),
            "retweets":     t.get("retweet_count") or t.get("retweetCount", 0),
        })
    return converted


def load_existing() -> list:
    if not os.path.exists(OUTPUT_PATH):
        return []
    with open(OUTPUT_PATH, encoding="utf-8") as f:
        return json.load(f)


def merge_and_dedup(existing: list, new_tweets: list) -> list:
    seen_urls = {t.get("url") for t in existing if t.get("url")}
    added = 0
    for t in new_tweets:
        if t.get("url") and t["url"] not in seen_urls:
            existing.append(t)
            seen_urls.add(t["url"])
            added += 1
    print(f"   ✓ Added {added} new tweets (total: {len(existing)})")
    return existing


def save(tweets: list):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(tweets, f, ensure_ascii=False, indent=2)
    print(f"   💾 Saved → {OUTPUT_PATH}")


def update_vdb():
    """Fast update — only re-embeds tweets, no full rebuild!"""
    print("\n⚡ Updating vector database (tweets only)...")
    try:
        sys.path.insert(0, BASE_DIR)
        from kb_vector import add_tweets_only
        add_tweets_only()
        print("   ✅ Vector DB updated successfully!")
    except Exception as e:
        print(f"   ✗ Failed to update VDB: {e}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def run():
    print("=" * 55)
    print("  تبيَّن — Daily KB Update")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 55)

    if APIFY_TOKEN == "YOUR_API_TOKEN_HERE":
        print("❌ Please set your APIFY_TOKEN first!")
        return

    # Step 1: Download
    print("\n📥 Downloading fresh tweets from Apify...")
    all_new = []
    for source_name, task_id in TASK_IDS.items():
        tweets = download_task(task_id, source_name)
        converted = convert_tweets(tweets, source_name)
        all_new.extend(converted)
    print(f"\n   Total new tweets: {len(all_new)}")

    if not all_new:
        print("⚠️  No new tweets. Check token and task IDs.")
        return

    # Step 2: Merge
    print("\n🔀 Merging with existing KB...")
    existing = load_existing()
    print(f"   Existing tweets: {len(existing)}")
    merged = merge_and_dedup(existing, all_new)

    # Step 3: Save
    save(merged)

    # Step 4: Fast VDB update (tweets only!)
    update_vdb()

    print("\n✅ KB update complete!")
    print(f"   Total tweets in KB: {len(merged)}")


if __name__ == "__main__":
    run()
