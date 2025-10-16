# bassam_core/workers/core_worker.py
# -*- coding: utf-8 -*-
"""
🔥 Bassam Core Worker – FINAL
- صفّ مهام لطلبات المستخدم (enqueue → drain).
- تعلّم ذاتي مجدول (Scheduler) + تشغيل دورة يدويًا عبر API.
- تخزين النتائج بصيغة JSONL داخل bassam_core/data.
- بحث افتراضي عبر DuckDuckGo (يمكن لاحقًا إضافة Google).
"""

from __future__ import annotations

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from duckduckgo_search import DDGS  # محرك البحث الافتراضي

# =========================
# مسارات العمل والتخزين
# =========================
PKG_DIR  = os.path.dirname(os.path.dirname(__file__))       # bassam_core/
DATA_DIR = os.path.join(PKG_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

NEWS_PATH = os.path.join(DATA_DIR, "news.jsonl")        # أرشيف ما تعلّمه النظام
QUEUE_PATH = os.path.join(DATA_DIR, "queue.jsonl")      # صفّ طلبات المستخدم
KNOW_PATH  = os.path.join(DATA_DIR, "knowledge.jsonl")  # معرفة تراكمية (اختياري)

# =========================
# إعدادات الجدولة من البيئة
# =========================
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "30"))
INTERVAL_SEC = int(os.getenv("LEARN_INTERVAL_SEC", "0"))
RUN_IMMEDIATELY = os.getenv("LEARN_RUN_IMMEDIATELY", "1") == "1"

# =========================
# مواضيع افتراضية للتعلّم الذاتي
# =========================
TOPICS: List[str] = [
    "تقنيات الذكاء الاصطناعي الحديثة 2025",
    "أطر Python لبناء واجهات برمجية: FastAPI و Flask",
    "تحسين أداء تطبيقات الويب باستخدام AsyncIO",
    "تصميم Chatbots تعتمد على RAG و LLMs",
    "أفضل ممارسات التشفير والأمان في تطبيقات الويب",
    "استخدام APIs مفتوحة لجلب الأخبار والمحتوى",
    "تطبيقات الذكاء الاصطناعي في التعليم والعمل",
]

# =========================
# أدوات JSONL بسيطة
# =========================
def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def _read_jsonl(path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
    if limit:
        lines = lines[-limit:]
    return [json.loads(x) for x in lines]

# =========================
# صفّ المهام والنتائج
# =========================
_queue_lock = threading.Lock()
_queue: List[Dict[str, Any]] = []

_running = threading.Event()      # حالة العامل
_NEXT_AT: Optional[str] = None    # وقت الدورة القادمة (UTC ISO)

def enqueue_task(q: str) -> None:
    """إضافة مهمة (نصّ بحث/تعلّم) إلى الصفّ."""
    q = (q or "").strip()
    if not q:
        return
    item = {"q": q, "ts": datetime.utcnow().isoformat()}
    with _queue_lock:
        _queue.append(item)
    _append_jsonl(QUEUE_PATH, item)

def query_index() -> List[str]:
    """عرض آخر عبارات في الصف (للاطلاع فقط)."""
    with _queue_lock:
        return [x["q"] for x in _queue[-15:]]

def get_status() -> Dict[str, Any]:
    """حالة النظام والمجدول (تستدعيها الواجهة)."""
    return {
        "running": _running.is_set(),
        "interval_min": INTERVAL_MIN,
        "interval_sec": INTERVAL_SEC,
        "queue_size": len(_queue),
        "topics": TOPICS,
        "next_run_at": _NEXT_AT,  # وقت الدورة التالية (UTC ISO)
    }

def get_latest_results(limit: int = 10) -> List[Dict[str, Any]]:
    """آخر ما تمّ تعلمه/أرشفته (للـ /api/news /api/learn/latest)."""
    docs = _read_jsonl(NEWS_PATH, limit=limit)
    return list(reversed(docs))

# =========================
# البحث + التلخيص البسيط
# =========================
def _ddg_search(q: str, n: int = 8) -> List[Dict[str, str]]:
    """بحث عبر DuckDuckGo وإرجاع قائمة نتائج مبسّطة."""
    results: List[Dict[str, str]] = []
    try:
        with DDGS() as d:
            for r in d.text(q, max_results=n, region="sa-ar"):
                results.append({
                    "title": r.get("title", "") or "",
                    "url": r.get("href", "") or "",
                    "snippet": (r.get("body") or "")[:300],
                })
    except Exception as e:
        results.append({"title": "SearchError", "url": "", "snippet": str(e)})
    return results

def _summarize(q: str, results: List[Dict[str, str]]) -> str:
    """تلخيص نصي مبسّط لأوّل النتائج (مكان مناسب لاحقًا لاستدعاء LLM)."""
    lines = [f"- {r['title']}: {r['snippet']}" for r in results[:5] if r.get("title") or r.get("snippet")]
    if not lines:
        lines = ["- لا توجد نتائج كافية."]
    return f"📘 ملخص حول «{q}»:\n" + "\n".join(lines)

def _learn_once(q: str) -> Dict[str, Any]:
    """ينفّذ بحثًا + تلخيصًا ويخزن النتيجة في الأرشيف."""
    results = _ddg_search(q)
    summary = _summarize(q, results)
    doc = {
        "query": q,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
        "results": results,
    }
    _append_jsonl(NEWS_PATH, doc)
    _append_jsonl(KNOW_PATH, doc)
    return doc

def _drain_queue() -> int:
    """تنفيذ جميع المهام الموجودة في الصفّ (مرة واحدة)."""
    global _queue
    with _queue_lock:
        if not _queue:
            return 0
        batch = _queue[:]
        _queue = []
    count = 0
    for item in batch:
        try:
            _learn_once(item["q"])
            count += 1
        except Exception as e:
            _append_jsonl(NEWS_PATH, {"error": str(e), "query": item["q"], "ts": datetime.utcnow().isoformat()})
    return count

# =========================
# المجدول Scheduler
# =========================
class Scheduler:
    def __init__(self, minutes: int = INTERVAL_MIN, seconds: int = INTERVAL_SEC, run_now: bool = RUN_IMMEDIATELY):
        self.interval = max(1, minutes * 60 + seconds)
        self.run_now = run_now
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        global _NEXT_AT
        # حساب وقت الدورة القادمة فور البدء
        _NEXT_AT = (datetime.utcnow() + timedelta(seconds=self.interval)).isoformat()
        print(f"🕒 Scheduler started (every {self.interval//60} min {self.interval%60}s)")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        print("🛑 Scheduler stopped")

    def _sleep_chunked(self):
        # نوم مجزأ يسمح بالإيقاف السلس
        remaining = self.interval
        step = 0.1
        loops = int(remaining / step)
        for _ in range(loops):
            if self.stop_event.is_set():
                return
            time.sleep(step)

    def _loop(self):
        if self.run_now:
            self._tick()
        while not self.stop_event.is_set():
            self._sleep_chunked()
            if self.stop_event.is_set():
                break
            self._tick()

    def _tick(self):
        global _NEXT_AT
        try:
            run_cycle_once()  # تنفيذ دورة كاملة (صف + مواضيع)
        finally:
            _NEXT_AT = (datetime.utcnow() + timedelta(seconds=self.interval)).isoformat()

# =========================
# تشغيل دورة يدويًا / بواسطة المجدول
# =========================
def run_cycle_once(custom_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    تشغيل دورة تعلّم كاملة الآن:
      1) يفرّغ الصفّ (طلبات المستخدم).
      2) يتعلّم من قائمة مواضيع (مخصّصة أو الافتراضية).
    """
    print(f"🔁 Auto-learning cycle @ {datetime.utcnow().isoformat()}")

    done_from_queue = _drain_queue()
    topics = [t for t in (custom_topics or TOPICS) if t and t.strip()]

    done_from_topics = 0
    for topic in topics:
        try:
            _learn_once(topic.strip())
            done_from_topics += 1
        except Exception as e:
            _append_jsonl(NEWS_PATH, {"topic": topic, "error": str(e), "ts": datetime.utcnow().isoformat()})

    msg = f"✅ Cycle complete — queue:{done_from_queue}, topics:{done_from_topics}"
    print(msg)
    return {"queue": done_from_queue, "topics": done_from_topics, "message": msg}

# =========================
# واجهة بدء العامل من تطبيق FastAPI
# =========================
_SCHED: Optional[Scheduler] = None

def start_scheduler() -> None:
    """تُستدعى من حدث startup في FastAPI لربط العامل بالمجدول."""
    global _SCHED
    if _SCHED:
        return
    _running.set()
    _SCHED = Scheduler()
    _SCHED.start()
    print("🔥 Worker linked to Scheduler and running.")
