# تبيَّن (Tabayyun)
### نظام ذكي للتحقق من الأخبار العربية

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Groq](https://img.shields.io/badge/Groq-Llama%203.3%2070B-orange)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic-purple)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20DB-green)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-teal)

**مشروع نهائي | معسكر الذكاء الاصطناعي التطبيقي | اكاديمية سدايا **

</div>

---

## نظرة عامة

**تبيَّن** نظام ذكاء اصطناعي متكامل للتحقق من الأخبار العربية والسعودية. يستخدم تقنيات RAG (Retrieval-Augmented Generation) مع وكيل ذكي مبني على LangGraph للتحقق من صحة الادعاءات الإخبارية.

### المشكلة التي يحلها
انتشار الأخبار الكاذبة والمضللة على وسائل التواصل الاجتماعي باللغة العربية، مع غياب أدوات تحقق آلية فعّالة للمحتوى السعودي والخليجي.

---

## الميزات الرئيسية

- تحقق نصي — تحليل الادعاءات الإخبارية النصية
- تحقق بالصور — استخراج النص من الصور (screenshots) والتحقق منه
- وكيل ذكي — يستخدم LangGraph مع نمط ReAct وChain-of-Thought
- Self-Reflection Loop — يُعيد البحث تلقائياً إذا كانت الثقة منخفضة
- قاعدة معرفة عربية — 11,629 مقالة من مصادر موثوقة
- تحديث يومي تلقائي — يجلب أحدث التغريدات من واس والجهات الحكومية
- تتبع الحسابات المشبوهة — يحفظ سجل الحسابات التي تنشر أخباراً كاذبة
- لوحة إدارة — واجهة للأدمن للمراقبة والتحكم

---

## معمارية النظام

```
المستخدم (app.html)
        |
   FastAPI Server
        |
   LangGraph Agent
   --------------------------------
   1. فحص سمعة الحساب
   2. توليد استعلامات البحث
   3. البحث في KB (FAISS)
   4. تحليل الأدلة (ReAct)      <- يُكرر إذا ثقة < 60%
   5. إصدار الحكم النهائي
   --------------------------------
        |
   النتيجة للمستخدم
```

### التصنيفات الممكنة

| التصنيف | المعنى |
|---------|--------|
| `confirmed_true` | صحيح بأدلة قوية |
| `confirmed_false` | خاطئ بوضوح |
| `misleading` | حقيقة جزئية مضللة |
| `nei` | لا توجد أدلة كافية |

---

## قاعدة المعرفة (Knowledge Base)

| المصدر | النوع | الحجم |
|--------|-------|-------|
| AFND (Arabic Fake News Dataset) | Kaggle | 6,487 مقالة |
| Classified Arabic News | Kaggle | 5,000 مقالة |
| Al Jazeera Arabic | Scraping | 88 مقالة |
| BBC Arabic | RSS | 24 مقالة |
| واس (SPA) | Manual | 10 مقالات |
| العربية | Manual | 12 مقالة |
| تغريدات SPAregions | Apify | يومي |
| تغريدات SaudiNews50 | Apify | يومي |
| تغريدات moe_gov_sa | Apify | يومي |
| **المجموع** | | **11,629+ مقالة** |

### تحميل البيانات
- AFND: [Kaggle - Arabic Fake News Dataset](https://www.kaggle.com)
- Classified Arabic News: [Kaggle - Classified Arabic News](https://www.kaggle.com)

---

## التقنيات المستخدمة

| التقنية | الاستخدام |
|---------|-----------|
| Groq API (Llama 3.3 70B) | نموذج اللغة الرئيسي |
| Groq Vision (Llama 4 Scout) | استخراج النص من الصور |
| LangGraph | تنسيق خطوات الوكيل |
| FAISS | قاعدة البيانات المتجهية |
| Sentence Transformers | تحويل النصوص لمتجهات |
| FastAPI | الـ Backend API |
| Apify | جلب التغريدات تلقائياً |
| HTML/CSS/JS | واجهة المستخدم |

---

## هيكل المشروع

```
tabayyun_kb/
|-- tabayyan.py              # الوكيل الذكي + FastAPI server
|-- kb_vector.py             # قاعدة البيانات المتجهية (FAISS)
|-- update_kb.py             # تحديث التغريدات اليومي
|-- run_kb.py                # تشغيل جميع المجمّعات
|
|-- collectors/
|   |-- trusted_sources.py   # جمع البيانات من المصادر الموثوقة
|   |-- benchmarks.py        # تحميل مجموعات البيانات
|   └-- evaluation_set.py    # مجموعة التقييم
|
|-- data/
|   |-- trusted_sources/
|   |   |-- trusted_articles.json       # مقالات الجزيرة + BBC
|   |   |-- manual_was.json             # مقالات واس
|   |   |-- manual_alarabiya.json       # مقالات العربية
|   |   └-- xtweets_was.json            # تغريدات يومية
|   └-- benchmarks/
|       |-- afnd_sample.json            # غير مرفوع (كبير الحجم)
|       └-- classified_arabic_news.json # غير مرفوع (كبير الحجم)
|
|-- utils/
|   └-- helpers.py           # دوال مساعدة
|
|-- app.html                 # واجهة المستخدم
|-- admin.html               # لوحة الإدارة
|-- suspicious_accounts.json # سجل الحسابات المشبوهة
|-- requirements.txt         # المكتبات المطلوبة
└-- README.md
```

---

## طريقة التشغيل

### المتطلبات
- Python 3.12+
- مفتاح Groq API مجاني من [console.groq.com](https://console.groq.com)

### 1. تثبيت المكتبات

```bash
pip install groq fastapi uvicorn pydantic langgraph langchain-core
pip install sentence-transformers faiss-cpu pillow requests
pip install feedparser beautifulsoup4 lxml
```

### 2. تحميل البيانات

حمّل مجموعات البيانات من Kaggle وضعها في:

```
data/benchmarks/AFND/
data/benchmarks/Classified Arabic News.csv
```

### 3. بناء قاعدة البيانات (مرة واحدة فقط)

```bash
python kb_vector.py --build
```

### 4. تشغيل السيرفر

```bash
# Windows PowerShell
$env:GROQ_API_KEY="gsk_YOUR_KEY_HERE"
python tabayyan.py
```

### 5. فتح الواجهة

- المستخدم: افتح `app.html` في المتصفح
- الأدمن: افتح `admin.html` (كلمة المرور: `tabayyun2026`)

---

## API Endpoints

| Method | Endpoint | الوصف |
|--------|----------|-------|
| `POST` | `/verify` | التحقق من ادعاء نصي |
| `POST` | `/verify-image` | التحقق من صورة |
| `GET` | `/suspicious` | قائمة الحسابات المشبوهة |
| `GET` | `/healthz` | حالة السيرفر |
| `POST` | `/admin/update-tweets` | تحديث التغريدات |
| `POST` | `/admin/rebuild-db` | إعادة بناء قاعدة البيانات |

### مثال

```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{"claim": "أعلنت وزارة التعليم إلزام الطلاب بدراسة الذكاء الاصطناعي", "source_handle": "SaudiNews50"}'
```

---

## التحديث اليومي

يعمل النظام على تحديث التغريدات تلقائياً عبر Apify:

```
Apify Schedule (يومياً 2:30-2:40 م)
        |
تحميل تغريدات SPAregions + SaudiNews50 + moe_gov_sa
        |
تحويل للصيغة المناسبة
        |
اضافة للـ FAISS index
```

لتحديث يدوي:

```bash
python update_kb.py
```

---

## فريق العمل

| الاسم | الدور |
|-------|-------|
| رفا الشريف | Knowledge Base + RAG Pipeline + واجهات المستخدم |
| فاطمة الغامدي  | Agent Logic + LangGraph |
| سارة الخثعمي | LLM Integration + API |

**المشرف**:  محمد بدار
**الجهة**: اكاديمية سدايا 
**السنة**: 2026

---

## نتائج التقييم

| المقياس | النتيجة |
|---------|--------|
| دقة التصنيف على AFND | قيد التقييم |
| متوسط وقت الاستجابة | 40-60 ثانية |
| حجم قاعدة المعرفة | 11,629 مقالة |
| دعم اللغة العربية | كامل |
| دعم الصور | مدعوم |

---

## الترخيص

هذا المشروع لأغراض أكاديمية — مشروع تخرج جامعة الإمام عبدالرحمن بن فيصل 2026.
