# ============================================================
# ADMIN ENDPOINTS — أضيفي هذا قبل if __name__ == "__main__"
# ============================================================

class AdminRequest(BaseModel):
    admin_key: str

ADMIN_KEY = "tabayyun2026"

@app.post("/admin/update-tweets")
def admin_update_tweets(request: AdminRequest):
    """تحديث التغريدات فقط — بدون إعادة بناء الـ KB كاملاً."""
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(403, "غير مصرح")

    import subprocess
    import sys

    log = []
    try:
        # Step 1: Download fresh tweets
        log.append("› جاري تحميل التغريدات من Apify...")
        result = subprocess.run(
            [sys.executable, "update_kb.py"],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True, text=True, timeout=120
        )
        log.append(f"› {result.stdout.strip()}" if result.stdout else "› تم تحميل التغريدات")

        # Step 2: Add tweets only to VDB (fast!)
        log.append("› جاري إضافة التغريدات للـ KB...")
        from kb_vector import add_tweets_only
        add_tweets_only()
        log.append("› ✅ تم تحديث الـ KB بالتغريدات الجديدة!")

        # Count tweets
        import json
        tweets_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data", "trusted_sources", "xtweets_was.json"
        )
        with open(tweets_path, encoding="utf-8") as f:
            tweets = json.load(f)

        return {
            "success": True,
            "total_tweets": len(tweets),
            "log": log,
        }

    except Exception as e:
        log.append(f"› ❌ خطأ: {str(e)}")
        return {"success": False, "message": str(e), "log": log}


@app.post("/admin/rebuild-db")
def admin_rebuild_db(request: AdminRequest):
    """إعادة بناء الـ KB كاملاً — يأخذ 10-15 دقيقة."""
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(403, "غير مصرح")

    try:
        from kb_vector import build_db
        build_db()
        return {"success": True, "message": "✅ تم إعادة بناء الـ KB بنجاح!"}
    except Exception as e:
        return {"success": False, "message": str(e)}
