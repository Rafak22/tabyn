"""
Collector 3 — Benchmark Datasets
Loads:
  - AFND: 134 source folders, each with scraped_articles.json
  - Classified Arabic News: single CSV file
Output: data/benchmarks/afnd_sample.json
        data/benchmarks/classified_arabic_news.json
"""

import os
import sys
import json
import csv
import glob

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.helpers import save_json, timestamp

BENCHMARKS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data", "benchmarks"
)

def load_afnd(max_per_source=50):
    print("\n📂 AFND — Loading from source folders")

    dataset_dir  = os.path.join(BENCHMARKS_DIR, "AFND", "Dataset")
    sources_json = os.path.join(BENCHMARKS_DIR, "AFND", "sources.json")

    if not os.path.exists(dataset_dir):
        print("   ✗ AFND/Dataset folder not found")
        return []

    # Load source metadata — format: {"source_1": "credible", ...}
    source_meta = {}
    if os.path.exists(sources_json):
        with open(sources_json, encoding="utf-8") as f:
            meta = json.load(f)
            for sid, credibility in meta.items():
                source_meta[sid] = {
                    "name":        sid,
                    "credibility": credibility,
                    "url":         "",
                    "country":     "",
                }

    articles = []
    source_folders = sorted(glob.glob(os.path.join(dataset_dir, "source_*")))
    print(f"   Found {len(source_folders)} source folders")

    for folder in source_folders:
        source_name = os.path.basename(folder)
        meta = source_meta.get(source_name, {
            "name":        source_name,
            "credibility": "unknown",
            "url":         "",
            "country":     "",
        })

        # Each source has one scraped_articles.json file
        json_file = os.path.join(folder, "scraped_articles.json")
        if not os.path.exists(json_file):
            continue

        count = 0
        try:
            with open(json_file, encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            # data could be a list or a dict
            # data could be a list or a dict with "articles" key
            if isinstance(data, dict):
             data = data.get("articles", list(data.values())[0] if data else [])

            for item in data[:max_per_source]:
                if isinstance(item, str):
                    title   = item[:200]
                    summary = ""
                    date    = ""
                else:
                    title   = str(item.get("title") or item.get("headline") or "")[:200]
                    summary = str(item.get("text") or item.get("content") or item.get("body") or "")[:500]
                    date = str(item.get("date") or item.get("published date") or item.get("published") or "")

                if not title and not summary:
                    continue

                articles.append({
                    "source":        meta["name"],
                    "source_url":    meta["url"],
                    "language":      "ar",
                    "trusted":       meta["credibility"] == "credible",
                    "credibility":   meta["credibility"],
                    "country":       meta["country"],
                    "title":         title,
                    "summary":       summary,
                    "published_at":  date,
                    "collected_at":  timestamp(),
                    "used_for":      "benchmark",
                    "dataset":       "AFND",
                    "source_folder": source_name,
                })
                count += 1

        except Exception:
            continue

    print(f"   ✓ Loaded {len(articles)} articles from {len(source_folders)} sources")
    print(f"     (max {max_per_source} per source)")

    out_path = os.path.join(BENCHMARKS_DIR, "afnd_sample.json")
    save_json(articles, out_path)
    return articles


def load_classified_arabic_news(max_rows=5000):
    print("\n📂 Classified Arabic News — Loading CSV")

    csv_path = os.path.join(BENCHMARKS_DIR, "Classified Arabic News.csv")
    if not os.path.exists(csv_path):
        print("   ✗ CSV file not found")
        return []

    articles = []
    try:
        with open(csv_path, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            print(f"   Columns found: {reader.fieldnames}")

            for i, row in enumerate(reader):
                if i >= max_rows:
                    break

                title  = row.get("title") or row.get("Title") or row.get("headline") or ""
                text   = row.get("text") or row.get("Text") or row.get("content") or row.get("body") or ""
                label  = row.get("label") or row.get("Label") or row.get("class") or row.get("category") or ""
                source = row.get("source") or row.get("Source") or row.get("publisher") or ""
                date   = row.get("date") or row.get("Date") or row.get("published date") or ""
                url    = row.get("url") or row.get("URL") or row.get("link") or ""

                if not title and not text:
                    continue

                articles.append({
                    "source":       source or "Classified Arabic News",
                    "source_url":   url,
                    "language":     "ar",
                    "trusted":      None,
                    "label":        label,
                    "title":        str(title)[:200],
                    "summary":      str(text)[:500],
                    "published_at": str(date),
                    "collected_at": timestamp(),
                    "used_for":     "benchmark",
                    "dataset":      "Classified Arabic News",
                })

        print(f"   ✓ Loaded {len(articles)} rows (limited to {max_rows})")

    except Exception as e:
        print(f"   ✗ Failed: {e}")

    out_path = os.path.join(BENCHMARKS_DIR, "classified_arabic_news.json")
    save_json(articles, out_path)
    return articles


def print_benchmark_summary(afnd, classified):
    from collections import Counter
    print("\n📊 Benchmark Summary:")
    print(f"   AFND:                    {len(afnd):,} articles")
    if afnd:
        cred = Counter(a["credibility"] for a in afnd)
        for k, v in cred.items():
            print(f"     → {k}: {v:,}")
    print(f"   Classified Arabic News:  {len(classified):,} rows")
    if classified:
        labels = Counter(a["label"] for a in classified if a["label"])
        for k, v in list(labels.items())[:5]:
            print(f"     → {k}: {v:,}")


def run():
    print("=" * 55)
    print("  Collector 3 — Benchmark Datasets")
    print("=" * 55)
    os.makedirs(BENCHMARKS_DIR, exist_ok=True)
    afnd       = load_afnd(max_per_source=50)
    classified = load_classified_arabic_news(max_rows=5000)
    print_benchmark_summary(afnd, classified)
    print("\n✅ Benchmarks loaded!")
    print(f"   → data/benchmarks/afnd_sample.json")
    print(f"   → data/benchmarks/classified_arabic_news.json")


if __name__ == "__main__":
    run()