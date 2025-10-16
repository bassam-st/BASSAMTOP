# bassam_core/workers/core_worker.py
# -*- coding: utf-8 -*-
"""
🔥 Bassam Core Worker – FINAL
- ربط المجدول بعامل التشغيل تلقائيًا.
- تنفيذ طلبات المستخدم (صف مهام).
- تعلّم ذاتي مجدول + إمكانية تشغيل دورة تعلّم يدوياً عبر API.
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS

# ==== مسارات التخزين ====
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

NEWS_PATH = os.path.join(DATA_DIR, "news.jsonl")       # أرشيف التعلّم
QUEUE_PATH = os.path.join(DATA_DIR, "queue.jsonl")     # صفّ طلبات المستخدم
KNOW_PATH  = os.path.join(DATA_DIR, "knowledge.jsonl") # معرفة تراكمية

# ==== إعدادات الجدولة ====
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "30"))
INTERVAL_SEC = int(os.getenv("LEARN_INTERVAL_SEC", "0"))
RUN_IMMEDIATELY = os.getenv("LEARN_RUN_IMMEDIATELY", "1") == "1"

# ==== مواضيع افتراضية ====
TOPICS = [
    "تقنيات الذكاء الاصطناعي الحديثة 2025",
    "أُطر Python لبناء واجهات برمجية FastAPI و Flask",
    "تحسين أداء تطبيقات الويب باستخدام AsyncIO",
    "تصميم Chatbots تعتمد على RAG و LLMs",
    "أفضل ممارسات التشفير والأمان في تطبيقات الويب",
    "استخدام APIs مفتوحة لجلب الأخبار والمحتوى",
    "تطبيقات الذكاء الاصطناعي في التعليم والعمل",
]

# ==== أدوات JSONL ====
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

# ==== صفّ المهام والنتائج ====
_queue_lock = threading.Lock()
_queue: List[Dict[str, Any]] = []

_running = threading.Event()

def enqueue_task(q: str) -> None:
    """إضافة مهمة من المستخدم (بحث/تعلّم)."""
    item = {"q": q.strip(), "ts": datetime.utcnow().isoformat()}
    if not item["q"]:
        return
    with _queue_lock:
        _queue.append(item)
    _append_jsonl(QUEUE_PATH, item)

def query_index() -> List[str]:
    """آخر الطلبات في الصفّ (للعرض)."""
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
    """أحدث نتائج التعلّم."""
    docs = _read_jsonl(NEWS_PATH, limit=limit)
    return list(reversed(docs))

# ==== البحث والتلخيص ====
def _ddg_search(q: str, n: int = 6) -> List[Dict[str, str]]:
    results = []
    try:
        with DDGS() as d:
            for r in d.text(q, max_results=n, region="sa-ar"):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "snippet": (r.get("body") or "")[:250],
                })
    except Exception as e:
        results.append({"title": "SearchError", "href": "", "snippet": str(e)})
    return results

def _summarize(q: str, results: List[Dict[str, str]]) -> str:
    lines = [f"- {r['title']}: {r['snippet']}" for r in results[:5]]
    if not lines:
        lines = ["- لا توجد نتائج."]
    return f"📘 ملخص حول «{q}»:\n" + "\n".join(lines)

def _learn_once(q: str) -> Dict[str, Any]:
    """بحث + تلخيص + تخزين لعنصر واحد."""
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
    """تنفيذ جميع المهام الموجودة في الصفّ."""
    count = 0
    global _queue
    with _queue_lock:
        if not _queue:
            return 0
        batch = _queue[:]
        _queue = []
    for item in batch:
        _learn_once(item["q"])
        count += 1
    return count

# ==== المجدول ====
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

    def _sleep(self):
        for _ in range(int(self.interval * 10)):
            if self.stop_event.is_set():
                return
            time.sleep(0.1)

    def _loop(self):
        if self.run_now:
            self._tick()
        while not self.stop_event.is_set():
            self._sleep()
            if self.stop_event.is_set():
                break
            self._tick()

    def _tick(self):
        run_cycle_once()  # تنفيذ دورة كاملة

# ==== تشغيل دورة يدويًا (للـ API) ====
def run_cycle_once(custom_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    """تشغيل دورة تعلّم كاملة الآن (ينادى من المجدول أو من API)."""
    print(f"🔁 Auto-learning cycle @ {datetime.utcnow().isoformat()}")
    done_from_queue = _drain_queue()
    topics = custom_topics if (custom_topics and len(custom_topics) > 0) else TOPICS
    done_from_topics = 0
    for topic in topics:
        try:
            _learn_once(topic)
            done_from_topics += 1
        except Exception as e:
            _append_jsonl(NEWS_PATH, {"topic": topic, "error": str(e), "ts": datetime.utcnow().isoformat()})
    msg = f"✅ Cycle complete — queue:{done_from_queue}, topics:{done_from_topics}"
    print(msg)
    return {"queue": done_from_queue, "topics": done_from_topics, "message": msg}

# ==== ربط المجدول بعامل التشغيل ====
_SCHED: Optional[Scheduler] = None

def start_scheduler() -> None:
    """يستدعى من حدث بدء التطبيق."""
    global _SCHED
    if _SCHED:
        return
    _running.set()
    _SCHED = Scheduler()
    _SCHED.start()
    print("🔥 Worker linked to Scheduler and running.")
# داخل bassam_core/workers/core_worker.py
from typing import List, Dict, Optional
from .search_providers import search_google, search_ddg
import os, time
from ..app.db import save_docs  # تأكد أن db.py يوفّر save_docs

def do_search(q: str, source: str = "auto", max_results: int = 8) -> List[Dict]:
    """يبحث أولاً في Google (إن توفّرت المفاتيح) ثم يسقط على DDG."""
    source = (source or "auto").lower()
    results: List[Dict] = []
    if source in ("google", "auto"):
        try:
            results = search_google(q, max_results=max_results)
        except Exception:
            results = []
    if not results and source in ("ddg", "auto", "both"):
        results = search_ddg(q, max_results=max_results)
    if source == "both":  # دمج الإثنين
        try:
            g = search_google(q, max_results=max_results//2 or 4)
        except Exception:
            g = []
        d = search_ddg(q, max_results=max_results - len(g))
        results = (g or []) + (d or [])
    return results

def learn_from_query(q: str, source: str = "auto") -> Dict:
    """ينفّذ بحثًا ويحفظ النتائج في قاعدة المعرفة."""
    docs = do_search(q, source=source, max_results=10)
    if docs:
        save_docs(docs)
    return {"learned": len(docs), "docs": docs[:5]}  # نرجّع عيّنة صغيرة للعرض

# موجود مسبقًا لكن نضيف optional topics:
def run_cycle_once(topics: Optional[List[str]] = None) -> Dict:
    topics = topics or os.getenv("TOPICS", "الذكاء الاصطناعي, الأمن السيبراني").split(",")
    total = 0
    for t in [x.strip() for x in topics if x.strip()]:
        total += learn_from_query(t).get("learned", 0)
        time.sleep(1)
    return {"message": "cycle_done", "topics": len(topics), "learned": total}
