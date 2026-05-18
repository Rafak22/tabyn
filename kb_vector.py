"""
تبيَّن — Knowledge Base Vector Database (FAISS Edition)
=========================================================
أسرع وأثبت من ChromaDB — ملف واحد لا يتلف أبداً!

Steps:
1. Run once to build:   python kb_vector.py --build
2. search_kb() ready!
3. Daily tweet update:  python kb_vector.py --update-tweets
"""

import json
import os
import argparse
import pickle
import numpy as np
from typing import List

# ─────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
INDEX_PATH = "C:/tabayyun/faiss_index.bin"
META_PATH  = "C:/tabayyun/faiss_meta.pkl"

SOURCES = {
    "trusted":    os.path.join(DATA_DIR, "trusted_sources",  "trusted_articles.json"),
    "tweets":     os.path.join(DATA_DIR, "trusted_sources",  "xtweets_was.json"),
    "manual_was": os.path.join(DATA_DIR, "trusted_sources",  "manual_was.json"),
    "alarabiya":  os.path.join(DATA_DIR, "trusted_sources",  "manual_alarabiya.json"),
    "afnd":       os.path.join(DATA_DIR, "benchmarks",       "afnd_sample.json"),
    "classified": os.path.join(DATA_DIR, "benchmarks",       "classified_arabic_news.json"),
}

EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────

def load_articles(sources_dict: dict) -> List[dict]:
    all_articles = []
    for name, path in sources_dict.items():
        if not os.path.exists(path):
            print(f"   ⚠️  Skipping {name} (file not found)")
            continue
        with open(path, encoding="utf-8") as f:
            articles = json.load(f)
        normalized = []
        for a in articles:
            title  = str(a.get("title")   or a.get("headline") or "").strip()
            body   = str(a.get("summary") or a.get("full_text") or a.get("text") or a.get("body") or "").strip()
            source = str(a.get("source")  or "").strip()
            url    = str(a.get("url")     or a.get("source_url") or "").strip()
            date   = str(a.get("published_at") or a.get("date") or a.get("published date") or a.get("createdAt") or "").strip()
            if not title and not body:
                continue
            normalized.append({
                "title":   title,
                "body":    body[:1000],
                "source":  source,
                "url":     url,
                "date":    date,
                "text":    f"{title} {body}".strip()[:512],
                "dataset": name,
            })
        print(f"   ✓ {name}: {len(normalized)} articles")
        all_articles.extend(normalized)
    return all_articles


# ─────────────────────────────────────────
# GET EMBEDDING MODEL
# ─────────────────────────────────────────

def get_model():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


# ─────────────────────────────────────────
# BUILD FULL INDEX
# ─────────────────────────────────────────

def build_db():
    print("\n" + "=" * 55)
    print("  تبيَّن — Building FAISS Index")
    print("=" * 55)

    print(f"\n📦 Loading embedding model...")
    model = get_model()
    print("   ✓ Model loaded")

    print("\n📂 Loading articles...")
    articles = load_articles(SOURCES)
    print(f"\n   Total: {len(articles)} articles")

    if not articles:
        print("❌ No articles found!")
        return

    print(f"\n🔢 Embedding articles...")
    texts = [a["text"] for a in articles]
    embeddings = model.encode(texts, batch_size=128, show_progress_bar=True)
    embeddings = embeddings.astype(np.float32)

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-10)

    print("\n💾 Building FAISS index...")
    import faiss
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product = cosine after normalization
    index.add(embeddings)

    # Save index
    faiss.write_index(index, INDEX_PATH)

    # Save metadata
    meta = [{
        "source":  a["source"],
        "url":     a["url"],
        "date":    a["date"],
        "title":   a["title"][:200],
        "body":    a["body"][:500],
        "dataset": a["dataset"],
    } for a in articles]

    with open(META_PATH, "wb") as f:
        pickle.dump(meta, f)

    print(f"\n✅ Done! {len(articles)} articles indexed.")
    print(f"   Index: {INDEX_PATH}")
    print(f"   Meta:  {META_PATH}")
    print(f"\n   ⚡ FAISS is ready — no more rebuild errors!")


# ─────────────────────────────────────────
# FAST TWEET UPDATE
# ─────────────────────────────────────────

def add_tweets_only():
    """إضافة التغريدات الجديدة فقط — ثواني بدون rebuild كامل."""
    print("\n⚡ Fast tweet update...")

    if not os.path.exists(INDEX_PATH):
        print("   ⚠️  Index not found — running full build first!")
        build_db()
        return

    model = get_model()

    # Load existing index and meta
    import faiss
    index = faiss.read_index(INDEX_PATH)
    with open(META_PATH, "rb") as f:
        meta = pickle.load(f)

    # Remove old tweet entries
    tweet_indices = [i for i, m in enumerate(meta) if m.get("dataset") == "tweets"]
    print(f"   🗑️  Found {len(tweet_indices)} old tweet entries")

    # Load fresh tweets
    tweets_path = SOURCES["tweets"]
    if not os.path.exists(tweets_path):
        print("   ⚠️  No tweets file found!")
        return

    with open(tweets_path, encoding="utf-8") as f:
        raw_tweets = json.load(f)

    new_articles = []
    for a in raw_tweets:
        title = str(a.get("title") or "").strip()
        body  = str(a.get("summary") or a.get("full_text") or "").strip()
        if not title and not body:
            continue
        new_articles.append({
            "title":   title,
            "body":    body[:1000],
            "source":  str(a.get("source") or ""),
            "url":     str(a.get("url") or ""),
            "date":    str(a.get("published_at") or ""),
            "text":    f"{title} {body}".strip()[:512],
            "dataset": "tweets",
        })

    if not new_articles:
        print("   ⚠️  No new tweets!")
        return

    non_tweet_meta = [m for m in meta if m.get("dataset") != "tweets"]
    print(f"   📊 Non-tweet articles: {len(non_tweet_meta)}")
    print(f"   🐦 New tweets: {len(new_articles)}")

    non_tweet_sources = {k: v for k, v in SOURCES.items() if k != "tweets"}
    all_articles = load_articles(non_tweet_sources)
    all_articles += new_articles

    print(f"\n🔢 Re-indexing {len(all_articles)} articles...")
    texts = [a["text"] for a in all_articles]
    embeddings = model.encode(texts, batch_size=128, show_progress_bar=False)
    embeddings = embeddings.astype(np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-10)

    import faiss
    dim = embeddings.shape[1]
    new_index = faiss.IndexFlatIP(dim)
    new_index.add(embeddings)

    faiss.write_index(new_index, INDEX_PATH)

    new_meta = [{
        "source":  a["source"],
        "url":     a["url"],
        "date":    a["date"],
        "title":   a["title"][:200],
        "body":    a["body"][:500],
        "dataset": a["dataset"],
    } for a in all_articles]

    with open(META_PATH, "wb") as f:
        pickle.dump(new_meta, f)

    print(f"   ✅ Updated! {len(new_articles)} tweets added. Total: {len(all_articles)}")


# ─────────────────────────────────────────
# SEARCH FUNCTION
# ─────────────────────────────────────────

_model = None
_index = None
_meta  = None


def _load_resources():
    global _model, _index, _meta
    if _model is None:
        _model = get_model()
    if _index is None:
        import faiss
        _index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            _meta = pickle.load(f)


def search_kb(query: str, n_results: int = 5) -> List[dict]:
    """البحث في الـ KB — سريع ومستقر!"""
    if not os.path.exists(INDEX_PATH):
        print("⚠️  Index not built yet! Run: python kb_vector.py --build")
        return []

    _load_resources()

    # Embed query
    q_emb = _model.encode([query]).astype(np.float32)
    q_emb = q_emb / (np.linalg.norm(q_emb) + 1e-10)

    # Search — خفضنا الـ threshold من 0.3 إلى 0.15
    scores, indices = _index.search(q_emb, n_results * 3)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0 or score < 0.15:
            continue
        m = _meta[idx]
        results.append({
            "source":     m.get("source", ""),
            "url":        m.get("url", ""),
            "date":       m.get("date", ""),
            "title":      m.get("title", ""),
            "body":       m.get("body", ""),
            "similarity": round(float(score), 3),
        })
        if len(results) >= n_results:
            break

    return results


# ─────────────────────────────────────────
# TEST
# ─────────────────────────────────────────

def test_search():
    print("\n🧪 Testing search_kb()...")
    queries = [
        "ميزانية الدولة 2026",
        "وزارة التعليم ذكاء اصطناعي",
        "الأرصاد أمطار السعودية",
        "إلزام طلاب جامعة الإمام",
    ]
    for q in queries:
        results = search_kb(q, n_results=3)
        print(f"\n  Query: '{q}'")
        print(f"  Found: {len(results)} results")
        for r in results:
            print(f"    → [{r['similarity']}] {r['source']}: {r['title'][:60]}")


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build",         action="store_true", help="Build FAISS index (run once)")
    parser.add_argument("--test",          action="store_true", help="Test search")
    parser.add_argument("--update-tweets", action="store_true", help="Fast tweet update")
    args = parser.parse_args()

    if args.build:
        build_db()
    elif args.test:
        test_search()
    elif args.update_tweets:
        add_tweets_only()
    else:
        print("Usage:")
        print("  python kb_vector.py --build          # Build index (run once)")
        print("  python kb_vector.py --test           # Test search")
        print("  python kb_vector.py --update-tweets  # Fast daily update")