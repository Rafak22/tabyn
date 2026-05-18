"""
Shared helpers for تبيَّن KB collectors.
"""

import json
import os
from datetime import datetime


def save_json(data, path):
    """Save a list of dicts to a JSON file with Arabic support."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 Saved {len(data)} records → {path}")


def load_json(path):
    """Load a JSON file. Returns empty list if file doesn't exist."""
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def deduplicate(articles, key="url"):
    """Remove duplicate articles based on a given key."""
    seen = set()
    unique = []
    for a in articles:
        val = a.get(key, "")
        if val and val not in seen:
            seen.add(val)
            unique.append(a)
    duplicates_removed = len(articles) - len(unique)
    if duplicates_removed > 0:
        print(f"  🔄 Removed {duplicates_removed} duplicates → {len(unique)} unique")
    return unique


def merge_with_existing(new_articles, path, key="url"):
    """
    Load existing data from path, merge with new articles,
    deduplicate, and return the merged list.
    Useful for incremental daily updates.
    """
    existing = load_json(path)
    combined = existing + new_articles
    merged = deduplicate(combined, key=key)
    print(f"  📦 Merged: {len(existing)} existing + {len(new_articles)} new = {len(merged)} total")
    return merged


def timestamp():
    return datetime.utcnow().isoformat()


def print_summary(articles, label="Collection"):
    from collections import Counter
    print(f"\n📊 {label} Summary:")
    by_source = Counter(a.get("source", "unknown") for a in articles)
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"   {src}: {count}")
    print(f"   TOTAL: {len(articles)}")
