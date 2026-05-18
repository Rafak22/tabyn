"""
Tabayyan - Groq Edition
========================
نظام تحقق متقدم من الأخبار العربية باستخدام:
- Groq API (سريع ومجاني)
- LangGraph للـ Agent Orchestration
- ReAct Pattern + Chain-of-Thought
- Self-Reflection Loop
- دعم الصور عبر Groq Vision

المكتبات المطلوبة:
   pip install groq fastapi uvicorn pydantic langgraph langchain-core pillow
"""

import os
import json
import time
import base64
from datetime import datetime
from typing import List, Optional, TypedDict, Annotated
from operator import add

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq
import uvicorn

from langgraph.graph import StateGraph, END
from kb_vector import search_kb as _real_search_kb


# ============================================================
# 1. الإعدادات
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

# نموذج النصوص — سريع جداً
TEXT_MODEL = "llama-3.3-70b-versatile"

# نموذج الصور — يدعم vision
VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

CONFIDENCE_THRESHOLD = 0.6
MAX_RETRIEVAL_LOOPS = 2

if not GROQ_API_KEY:
    print("⚠️  لازم تحطين GROQ_API_KEY قبل التشغيل!")
    print("    اعملي حساب مجاني في: https://console.groq.com")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# ============================================================
# 2. قاعدة البيانات الحقيقية
# ============================================================

def search_kb(query: str, top_k: int = 5) -> List[dict]:
    """البحث في قاعدة البيانات الحقيقية — 11,539 مقالة عربية."""
    return _real_search_kb(query, n_results=top_k)


# ============================================================
# 3. سجل المصادر غير الموثوقة
# ============================================================

SUSPICIOUS_ACCOUNTS = {}
# ─────────────────────────────────────────
# Suspicious Accounts — Persistent Storage
# ─────────────────────────────────────────
SUSPICIOUS_DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "suspicious_accounts.json"
)

def _load_db() -> dict:
    if os.path.exists(SUSPICIOUS_DB_PATH):
        with open(SUSPICIOUS_DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_db():
    with open(SUSPICIOUS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(SUSPICIOUS_ACCOUNTS, f, ensure_ascii=False, indent=2)

SUSPICIOUS_ACCOUNTS = _load_db()


def check_suspicious_account(handle: str) -> dict:
    if not handle or handle not in SUSPICIOUS_ACCOUNTS:
        return {"is_suspicious": False, "false_count": 0, "total_submissions": 0, "error_rate": 0.0}
    record = SUSPICIOUS_ACCOUNTS[handle]
    is_suspicious = record["error_rate"] >= 0.3 and record["total_submissions"] >= 3
    return {
        "is_suspicious": is_suspicious,
        "false_count": record["false_count"],
        "total_submissions": record["total_submissions"],
        "error_rate": record["error_rate"],
        "last_seen": record.get("last_seen", ""),
    }


def update_suspicious_account(handle: str, claim: str, was_false: bool):
    if not handle:
        return None
    if handle not in SUSPICIOUS_ACCOUNTS:
        SUSPICIOUS_ACCOUNTS[handle] = {
            "total_submissions": 0,
            "false_count": 0,
            "error_rate": 0.0,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "claims": []
        }
    record = SUSPICIOUS_ACCOUNTS[handle]
    record["total_submissions"] += 1
    record["last_seen"] = datetime.now().isoformat()
    if was_false:
        record["false_count"] += 1
        record["claims"].append({
            "claim": claim[:100],
            "date": datetime.now().isoformat()
        })
    record["error_rate"] = round(record["false_count"] / record["total_submissions"], 2)
    _save_db()
    return record


# ============================================================
# 4. AI Helper Functions (Groq)
# ============================================================

def call_ai(system_prompt: str, user_message: str, temperature: float = 0.3) -> str:
    """استدعاء Groq للنصوص."""
    if not client:
        raise HTTPException(500, "GROQ_API_KEY مو موجود!")

    response = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=temperature,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def call_vision_ai(prompt: str, image_data: str) -> str:
    """استدعاء Groq Vision للصور."""
    if not client:
        raise HTTPException(500, "GROQ_API_KEY مو موجود!")

    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
        }],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def extract_json(text: str) -> dict:
    """استخرج JSON من رد الـ AI."""
    text = text.replace("```json", "").replace("```", "")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"ما لقيت JSON في: {text[:200]}")
    return json.loads(text[start:end + 1])


def extract_claim_from_image(image_data: str) -> str:
    """استخرج الادعاء من الصورة."""
    prompt = """انظر إلى هذه الصورة بدقة واستخرج الادعاء أو الخبر الرئيسي المكتوب فيها.

إذا كانت الصورة:
- تغريدة أو منشور سوشال ميديا: استخرج نص المنشور
- لقطة شاشة لخبر: استخرج عنوان الخبر والمحتوى الأساسي
- صورة فيها نص: استخرج النص

أخرج النص بالعربية فقط، بدون أي تعليقات أو شرح إضافي."""
    return call_vision_ai(prompt, image_data).strip()


# ============================================================
# 5. System Prompts
# ============================================================

PLANNER_SYSTEM_PROMPT = """أنت خبير في توليد استعلامات البحث للفاكت تشيكنق العربي.

دورك: تحويل الادعاء إلى استعلامات بحث مركزة باللغة العربية الفصحى.

تعليمات صارمة:
1. ولّد 2-3 استعلامات قصيرة (3-6 كلمات لكل واحد)
2. استخدم الكلمات المفتاحية الأهم
3. تجنب الكلمات العامة (قال، صرح، أعلن)
4. كل استعلام يستهدف زاوية مختلفة

أخرج JSON فقط:
{"queries": ["استعلام 1", "استعلام 2", "استعلام 3"]}"""


FACT_CHECKER_SYSTEM_PROMPT = """أنت محقق صحفي خبير متخصص في التحقق من الأخبار العربية والسعودية.

نطاق عملك: الأخبار السعودية والخليجية والعربية فقط.

مهمتك: تحليل الادعاء وإصدار حكم موضوعي بناءً على:
1. الأدلة المتوفرة في قاعدة البيانات
2. معرفتك العامة بالأحداث الموثوقة
3. منطق الأحداث والسياق

اتبع هذا المنهج:
1. **التفكير**: ما الذي تحاول التحقق منه؟
2. **الملاحظة**: ماذا تجد في الأدلة؟
3. **التحليل من زاويتين**:
   - حجة الدعم: لماذا قد يكون الادعاء صحيحاً؟
   - حجة الرفض: لماذا قد يكون الادعاء خاطئاً؟
4. **الحكم النهائي**

التصنيفات:
- confirmed_true: صحيح بأدلة قوية أو معرفة موثوقة (confidence >= 0.75)
- confirmed_false: خاطئ بوضوح — إما بأدلة مضادة أو لأنه يتعارض مع الواقع المعروف (confidence >= 0.75)
- misleading: حقيقة جزئية مضللة
- nei: لا توجد أدلة كافية ولا يمكن الجزم — استخدمه فقط إذا الأدلة غير ذات صلة تماماً، ولا تلجأ إليه إذا وجدت أي دليل يتحدث عن نفس الموضوع

قواعد مهمة:
- إذا الادعاء يتعارض مع حقائق معروفة وموثوقة → confirmed_false حتى لو ما في أدلة في قاعدة البيانات
- إذا الادعاء يدّعي شيئاً لم يحدث ولا يوجد أي مصدر يؤكده → confirmed_false
- إذا الادعاء معقول لكن ما في دليل → nei
- لا تخترع اقتباسات غير موجودة
- الثقة من 0 إلى 1
- إذا الحساب المصدر مشبوه → خفّض درجة الثقة بـ 0.2


تعليمات إضافية مهمة:
- إذا وجدت أدلة تتعلق بالموضوع ولو بشكل غير مباشر، استخدمها واحكم
- confirmed_true أو confirmed_false أفضل من nei إذا كان الحكم منطقياً
- nei هو آخر خيار فقط عند غياب أي صلة بالموضوع

أخرج JSON فقط:
{
  "thought": "تفكيرك في الادعاء",
  "observation": "ما لاحظته في الأدلة",
  "defense_argument": "أقوى حجة تدعم الادعاء",
  "prosecution_argument": "أقوى حجة ترفض الادعاء",
  "verdict": "confirmed_true|confirmed_false|misleading|nei",
  "confidence": 0.0,
  "justification_ar": "تبرير عربي واضح 50-100 كلمة",
  "citations": [
    {"source": "اسم المصدر", "url": "الرابط", "date": "التاريخ", "quote": "اقتباس مباشر"}
  ]
}"""

# ============================================================
# 6. LangGraph State
# ============================================================

class AgentState(TypedDict):
    claim: str
    source_handle: Optional[str]

    queries: List[str]
    articles: List[dict]
    analysis: dict
    loop_count: int
    account_reputation: dict

    final_verdict: dict
    trace_log: Annotated[List[str], add]


# ============================================================
# 7. LangGraph Nodes
# ============================================================

def node_check_account(state: AgentState) -> AgentState:
    handle = state.get("source_handle")
    reputation = check_suspicious_account(handle) if handle else {
        "is_suspicious": False, "false_count": 0, "total": 0
    }
    log = f"[CHECK] @{handle or 'غير محدد'}: {'⚠️ مشبوه' if reputation['is_suspicious'] else '✓ نظيف'}"
    print(f"   {log}")
    return {"account_reputation": reputation, "trace_log": [log]}


def node_plan_queries(state: AgentState) -> AgentState:
    print("   [PLAN] توليد استعلامات البحث...")
    response = call_ai(PLANNER_SYSTEM_PROMPT, f"الادعاء: {state['claim']}", temperature=0.3)
    parsed = extract_json(response)
    queries = parsed.get("queries", [state["claim"]])
    log = f"[PLAN] {len(queries)} استعلام: {queries}"
    print(f"   {log}")
    return {"queries": queries, "trace_log": [log]}


def node_retrieve(state: AgentState) -> AgentState:
    print("   [RETRIEVE] البحث في قاعدة البيانات...")
    all_articles = []
    seen_urls = set()
    for query in state["queries"]:
        results = search_kb(query)
        for article in results:
            if article["url"] not in seen_urls:
                all_articles.append(article)
                seen_urls.add(article["url"])
    log = f"[RETRIEVE] وجدت {len(all_articles)} مقالة"
    print(f"   {log}")
    return {"articles": all_articles, "trace_log": [log]}


def node_analyze(state: AgentState) -> AgentState:
    print("   [ANALYZE] تحليل الأدلة وإصدار الحكم...")

    if not state["articles"]:
        analysis = {
            "thought": "لا توجد أدلة في قاعدة البيانات",
            "observation": "لم أعثر على مقالات ذات صلة",
            "defense_argument": "لا يوجد دليل",
            "prosecution_argument": "غياب الأدلة لا يعني الخطأ",
            "verdict": "nei",
            "confidence": 0.0,
            "justification_ar": "لم نعثر على أدلة كافية في المصادر الموثوقة للتحقق من هذا الادعاء.",
            "citations": [],
        }
    else:
        # بناء نص الأدلة
        evidence_text = ""
        for i, article in enumerate(state["articles"], 1):
            evidence_text += f"\nالدليل {i}:\n"
            evidence_text += f"- المصدر: {article['source']}\n"
            evidence_text += f"- التاريخ: {article.get('date', 'غير محدد')}\n"
            evidence_text += f"- العنوان: {article['title']}\n"
            evidence_text += f"- النص: {article['body'][:300]}\n"

        # أضف معلومات سمعة الحساب إذا وُجدت
        rep = state.get("account_reputation", {})
        if rep.get("is_suspicious"):
            evidence_text += f"\n⚠️ تحذير: هذا الحساب نشر {rep['false_count']} ادعاءات كاذبة سابقاً!\n"

        user_msg = f"الادعاء: {state['claim']}\n\nالأدلة المتاحة:\n{evidence_text}"
        response = call_ai(FACT_CHECKER_SYSTEM_PROMPT, user_msg, temperature=0.2)
        analysis = extract_json(response)

    log = f"[ANALYZE] {analysis['verdict']} (ثقة: {analysis['confidence']:.2f})"
    print(f"   {log}")
    return {"analysis": analysis, "trace_log": [log]}


def node_should_retry(state: AgentState) -> str:
    confidence = state["analysis"]["confidence"]
    loop_count = state.get("loop_count", 0)
    if confidence < CONFIDENCE_THRESHOLD and loop_count < MAX_RETRIEVAL_LOOPS:
        print(f"   [LOOP] ثقة منخفضة ({confidence:.2f}) — إعادة البحث بزاوية مختلفة...")
        return "retry"
    return "done"


def node_increment_loop(state: AgentState) -> AgentState:
    new_count = state.get("loop_count", 0) + 1
    # عدّل الاستعلامات لتكون أوسع في المحاولة الثانية
    expanded = [q + " أخبار سعودية" for q in state["queries"]]
    log = f"[LOOP] محاولة {new_count + 1} باستعلامات موسّعة"
    print(f"   {log}")
    return {"loop_count": new_count, "queries": expanded, "trace_log": [log]}


def node_finalize(state: AgentState) -> AgentState:
    analysis = state["analysis"]

    # حدّث سجل المصادر المشبوهة
    if state.get("source_handle"):
        was_false = analysis["verdict"] == "confirmed_false"
        update_suspicious_account(state["source_handle"], state["claim"], was_false)

    verdict = {
        "verdict":          analysis["verdict"],
        "confidence":       analysis["confidence"],
        "justification_ar": analysis["justification_ar"],
        "citations":        analysis.get("citations", []),
        "thought":          analysis.get("thought", ""),
        "defense_argument": analysis.get("defense_argument", ""),
        "prosecution_argument": analysis.get("prosecution_argument", ""),
    }
    log = f"[FINAL] {verdict['verdict']} (ثقة: {verdict['confidence']:.2f})"
    print(f"   {log}")
    return {"final_verdict": verdict, "trace_log": [log]}


# ============================================================
# 8. LangGraph Build
# ============================================================

def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("check_account",   node_check_account)
    graph.add_node("plan",            node_plan_queries)
    graph.add_node("retrieve",        node_retrieve)
    graph.add_node("analyze",         node_analyze)
    graph.add_node("increment_loop",  node_increment_loop)
    graph.add_node("finalize",        node_finalize)

    graph.set_entry_point("check_account")
    graph.add_edge("check_account", "plan")
    graph.add_edge("plan",          "retrieve")
    graph.add_edge("retrieve",      "analyze")

    graph.add_conditional_edges(
        "analyze",
        node_should_retry,
        {"retry": "increment_loop", "done": "finalize"}
    )
    graph.add_edge("increment_loop", "retrieve")
    graph.add_edge("finalize",       END)

    return graph.compile()


agent_graph = build_agent_graph()


# ============================================================
# 9. FastAPI
# ============================================================

app = FastAPI(
    title="Tabayyan - نظام التحقق من الأخبار",
    description="نظام تحقق ذكي من الأخبار العربية",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimRequest(BaseModel):
    claim: str = Field(..., min_length=5, max_length=500)
    source_handle: Optional[str] = None


class VerdictResponse(BaseModel):
    claim: str
    verdict: str
    confidence: float
    justification: str
    citations: List[dict]

    defense_argument: str
    prosecution_argument: str
    thought: str
    account_reputation: dict
    loop_count: int
    trace_log: List[str]
    elapsed_seconds: float

    extracted_from_image: Optional[bool] = False
    image_extracted_text: Optional[str] = None


# ============================================================
# 10. Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "name": "Tabayyan — نظام التحقق من الأخبار العربية",
        "version": "1.0.0",
        "model": TEXT_MODEL,
        "vision_model": VISION_MODEL,
        "kb_size": "11,539 مقالة عربية",
        "groq_configured": bool(GROQ_API_KEY),
        "docs": "/docs",
    }


@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "groq_configured": bool(GROQ_API_KEY),
        "kb_size": "11,539",
    }


@app.post("/verify", response_model=VerdictResponse)
def verify_claim(request: ClaimRequest):
    return _run_verification(
        claim=request.claim,
        source_handle=request.source_handle,
    )


@app.post("/verify-image", response_model=VerdictResponse)
async def verify_image_claim(
    image: UploadFile = File(...),
    source_handle: Optional[str] = Form(None),
):
    print("\n[IMAGE] استلام صورة للتحقق منها...")
    image_bytes = await image.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    try:
        print("[IMAGE] استخراج النص من الصورة...")
        extracted_claim = extract_claim_from_image(image_b64)
        print(f"[IMAGE] النص المستخرج: {extracted_claim[:80]}...")

        if not extracted_claim or len(extracted_claim) < 5:
            raise HTTPException(400, "لم أتمكن من استخراج نص من الصورة")

        return _run_verification(
            claim=extracted_claim,
            source_handle=source_handle,
            from_image=True,
            extracted_text=extracted_claim,
        )
    except Exception as e:
        raise HTTPException(500, f"خطأ في معالجة الصورة: {str(e)}")


def _run_verification(
    claim: str,
    source_handle: Optional[str] = None,
    from_image: bool = False,
    extracted_text: Optional[str] = None,
) -> VerdictResponse:
    start = time.time()

    print(f"\n{'=' * 60}")
    print(f"[NEW CLAIM] {claim[:60]}...")
    print(f"[SOURCE]    {source_handle or 'غير محدد'}")
    print(f"{'=' * 60}")

    try:
        initial_state = {
            "claim":          claim,
            "source_handle":  source_handle,
            "loop_count":     0,
            "trace_log":      [],
        }

        final_state = agent_graph.invoke(initial_state)
        verdict = final_state["final_verdict"]

        elapsed = round(time.time() - start, 2)
        print(f"\n[DONE] ✅ انتهى في {elapsed} ثانية\n")

        return VerdictResponse(
            claim=claim,
            verdict=verdict["verdict"],
            confidence=verdict["confidence"],
            justification=verdict["justification_ar"],
            citations=verdict.get("citations", []),
            defense_argument=verdict.get("defense_argument", ""),
            prosecution_argument=verdict.get("prosecution_argument", ""),
            thought=verdict.get("thought", ""),
            account_reputation=final_state["account_reputation"],
            loop_count=final_state.get("loop_count", 0),
            trace_log=final_state["trace_log"],
            elapsed_seconds=elapsed,
            extracted_from_image=from_image,
            image_extracted_text=extracted_text,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"خطأ: {str(e)}")


@app.get("/suspicious/{handle}")
def get_suspicious_account(handle: str):
    if handle not in SUSPICIOUS_ACCOUNTS:
        return {"handle": handle, "status": "clean", "false_count": 0}
    record = SUSPICIOUS_ACCOUNTS[handle]
    return {
        "handle": handle,
        "status": "suspicious" if record["false_count"] >= 2 else "monitored",
        "false_count": record["false_count"],
        "total_submissions": record["total"],
        "false_claims_history": record["claims"][-5:],
    }


@app.get("/suspicious")
def list_suspicious_accounts():
    suspicious = [
        {
            "handle": h,
            "false_count": r["false_count"],
            "total": r.get("total_submissions", r.get("total", 0)),
            "error_rate": r.get("error_rate", 0),
        }
        for h, r in SUSPICIOUS_ACCOUNTS.items()
        if r["false_count"] >= 2
    ]
    return {"count": len(suspicious), "accounts": suspicious}


# ============================================================
# ADMIN ENDPOINTS
# ============================================================

class AdminRequest(BaseModel):
    admin_key: str

ADMIN_KEY = "tabayyun2026"

@app.post("/admin/update-tweets")
def admin_update_tweets(request: AdminRequest):
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(403, "غير مصرح")
    log = []
    try:
        log.append("› جاري تحديث التغريدات...")
        from kb_vector import add_tweets_only
        add_tweets_only()
        log.append("› ✅ تم التحديث!")
        tweets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "trusted_sources", "xtweets_was.json")
        with open(tweets_path, encoding="utf-8") as f:
            tweets = json.load(f)
        return {"success": True, "total_tweets": len(tweets), "log": log}
    except Exception as e:
        return {"success": False, "message": str(e), "log": log}

@app.post("/admin/rebuild-db")
def admin_rebuild_db(request: AdminRequest):
    if request.admin_key != ADMIN_KEY:
        raise HTTPException(403, "غير مصرح")
    try:
        from kb_vector import build_db
        build_db()
        return {"success": True, "message": "✅ تم إعادة البناء!"}
    except Exception as e:
        return {"success": False, "message": str(e)}
# ============================================================
# 11. التشغيل
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Tabayyan — نظام التحقق من الأخبار العربية")
    print("=" * 60)
    print(f"📡 السيرفر:        http://localhost:8000")
    print(f"📖 التوثيق:        http://localhost:8000/docs")
    print(f"🤖 النموذج:        {TEXT_MODEL}")
    print(f"🖼️  نموذج الصور:   {VISION_MODEL}")
    print(f"📚 قاعدة البيانات: 11,539 مقالة عربية ✅")
    print(f"🔑 Groq API Key:   {'✓ موجود' if GROQ_API_KEY else '✗ ناقص!'}")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)