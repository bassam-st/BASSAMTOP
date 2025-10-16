# bassam_core/workers/core_worker.py
# -*- coding: utf-8 -*-
"""
🔥 Bassam Core Worker – النسخة النهائية
يربط المجدول بعامل التشغيل تلقائيًا.
يُنفّذ المهام اليدوية (من المستخدم) + التعلّم الذاتي المجدول.
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS

# مسارات التخزين
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

NEWS_PATH = os.path.join(DATA_DIR, "news.jsonl")      # أرشيف التعلّم
QUEUE_PATH = os.path.join(DATA_DIR, "queue.jsonl")    # صف انتظار المستخدم
KNOW_PATH = os.path.join(DATA_DIR, "knowledge.jsonl") # معرفة تراكمية

# إعدادات الجدولة (افتراضيًا كل 30 دقيقة)
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "30"))
INTERVAL_SEC = int(os.getenv("LEARN_INTERVAL_SEC", "0"))
RUN_IMMEDIATELY = os.getenv("LEARN_RUN_IMMEDIATELY", "1") == "1"

# المواضيع الافتراضية للتعلّم الذاتي
TOPICS = [
    "تقنيات الذكاء الاصطناعي الحديثة 2025",
    "أُطر Python لبناء واجهات برمجية FastAPI و Flask",
    "تحسين أداء تطبيقات الويب باستخدام AsyncIO",
    "تصميم Chatbots ذكية تعتمد على RAG و LLMs",
    "أفضل ممارسات الأمان والتشفير في تطبيقات الويب",
    "استخدام APIs مفتوحة لجلب الأخبار والمحتوى",
    "تطبيقات الذكاء الاصطناعي في التعليم والعمل",
]

# -------------------------
# أدوات المساعدة للتخزين
# -------------------------
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

# -------------------------
# صف المهام (Worker Queue)
# -------------------------
_queue_lock = threading.Lock()
_queue: List[Dict[str, Any]] = []
_last_results_lock = threading.Lock()
_last_results: List[Dict[str, Any]] = []
_running = threading.Event()

def enqueue_task(q: str) -> None:
    """إضافة مهمة من المستخدم (بحث/تعلم)."""
    item = {"q": q.strip(), "ts": datetime.utcnow().isoformat()}
    with _queue_lock:
        _queue.append(item)
    _append_jsonl(QUEUE_PATH, item)

def query_index() -> List[str]:
    """عرض آخر الطلبات من المستخدم."""
    with _queue_lock:
        return [x["q"] for x in _queue[-15:]]

def get_status() -> Dict[str, Any]:
    """حالة النظام والمجدول."""
    return {
        "running": _running.is_set(),
        "interval_min": INTERVAL_MIN,
        "interval_sec": INTERVAL_SEC,
        "queue_size": len(_queue),
        "topics": TOPICS,
    }

def get_latest_results(limit: int = 10) -> List[Dict[str, Any]]:
    """عرض أحدث نتائج التعلّم الذاتي."""
    docs = _read_jsonl(NEWS_PATH, limit=limit)
    return list(reversed(docs))

# -------------------------
# وظائف البحث والتلخيص
# -------------------------
def _ddg_search(q: str, n: int = 6) -> List[Dict[str, str]]:
    results = []
    try:
        with DDGS() as d:
            for r in d.text(q, max_results=n, region="sa-ar"):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "snippet": r.get("body", "")[:250],
                })
    except Exception as e:
        results.append({"title": "SearchError", "href": "", "snippet": str(e)})
    return results

def _summarize(q: str, results: List[Dict[str, str]]) -> str:
    """تلخيص مبسط من النتائج."""
    lines = [f"- {r['title']}: {r['snippet']}" for r in results[:5]]
    if not lines:
        lines = ["- لا توجد نتائج."]
    return f"📘 ملخص حول «{q}»:\n" + "\n".join(lines)

def _learn_once(q: str) -> Dict[str, Any]:
    """تنفيذ عملية تعلم واحدة (بحث + تلخيص + تخزين)."""
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

def _drain_queue() -> None:
    """تنفيذ جميع الطلبات الموجودة بالصف."""
    global _queue
    with _queue_lock:
        if not _queue:
            return
        batch = _queue[:]
        _queue = []
    for item in batch:
        _learn_once(item["q"])

# -------------------------
# المجدول (Scheduler)
# -------------------------
class Scheduler:
    def __init__(self, minutes=INTERVAL_MIN, seconds=INTERVAL_SEC, run_now=RUN_IMMEDIATELY):
        self.interval = minutes * 60 + seconds
        self.run_now = run_now
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        print(f"🕒 Scheduler started (every {self.interval//60} min)")
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        print("🛑 Scheduler stopped")

    def _loop(self):
        if self.run_now:
            self._tick()
        while not self.stop_event.is_set():
            for _ in range(int(self.interval * 10)):
                if self.stop_event.is_set():
                    return
                time.sleep(0.1)
            self._tick()

    def _tick(self):
        print(f"🔁 Running auto-learning cycle ({datetime.utcnow().isoformat()})")
        _drain_queue()
        for topic in TOPICS:
            try:
                _learn_once(topic)
            except Exception as e:
                _append_jsonl(NEWS_PATH, {"topic": topic, "error": str(e), "ts": datetime.utcnow().isoformat()})
        print("✅ Cycle complete — knowledge updated.")

# -------------------------
# ربط المجدول بعامل التشغيل
# -------------------------
_SCHED: Optional[Scheduler] = None

def start_scheduler() -> None:
    """يتم استدعاؤها عند بدء تشغيل التطبيق (startup event)."""
    global _SCHED
    if _SCHED:
        return
    _running.set()
    _SCHED = Scheduler()
    _SCHED.start()
    print("🔥 Bassam Core Worker linked to Scheduler — running automatically!")

# تشغيل يدوي للاختبار المحلي
if __name__ == "__main__":
    start_scheduler()
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        _SCHED.stop()
