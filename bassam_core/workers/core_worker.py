# bassam_core/workers/core_worker.py
# -*- coding: utf-8 -*-
"""
🔥 Bassam Core Worker – Final Unified Version
- يقوم بالبحث من Google أو DuckDuckGo.
- ينفّذ التعلّم الذاتي المجدول.
- يدعم البحث الفوري والتعلّم اليدوي عبر API.
"""

import os
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS

# ==== إعداد المسارات ====
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

NEWS_PATH = os.path.join(DATA_DIR, "news.jsonl")
QUEUE_PATH = os.path.join(DATA_DIR, "queue.jsonl")
KNOW_PATH = os.path.join(DATA_DIR, "knowledge.jsonl")

# ==== إعداد الجدولة ====
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "30"))
INTERVAL_SEC = int(os.getenv("LEARN_INTERVAL_SEC", "0"))
RUN_IMMEDIATELY = os.getenv("LEARN_RUN_IMMEDIATELY", "1") == "1"

# ==== مواضيع افتراضية ====
TOPICS = [
    "الذكاء الاصطناعي الحديث 2025",
    "مشاريع Python و FastAPI",
    "أمن المعلومات والتشفير",
    "تعلّم الآلة Machine Learning",
]

# ==== أدوات مساعدة JSONL ====
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

# ==== صفّ الطلبات ====
_queue_lock = threading.Lock()
_queue: List[Dict[str, Any]] = []
_running = threading.Event()

def enqueue_task(q: str) -> None:
    item = {"q": q.strip(), "ts": datetime.utcnow().isoformat()}
    if not item["q"]:
        return
    with _queue_lock:
        _queue.append(item)
    _append_jsonl(QUEUE_PATH, item)

def query_index() -> List[str]:
    with _queue_lock:
        return [x["q"] for x in _queue[-15:]]

def get_status() -> Dict[str, Any]:
    return {
        "running": _running.is_set(),
        "interval_min": INTERVAL_MIN,
        "interval_sec": INTERVAL_SEC,
        "queue_size": len(_queue),
        "topics": TOPICS,
    }

def get_latest_results(limit: int = 10) -> List[Dict[str, Any]]:
    docs = _read_jsonl(NEWS_PATH, limit=limit)
    return list(reversed(docs))

# ==== البحث من DuckDuckGo ====
def search_ddg(q: str, max_results: int = 6) -> List[Dict[str, str]]:
    results = []
    try:
        with DDGS() as d:
            for r in d.text(q, max_results=max_results, region="sa-ar"):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": (r.get("body") or "")[:250],
                })
    except Exception as e:
        results.append({"title": "SearchError", "url": "", "snippet": str(e)})
    return results

# ==== البحث من Google إن وُجدت المفاتيح ====
def search_google(q: str, max_results: int = 6) -> List[Dict[str, str]]:
    api_key = os.getenv("GOOGLE_API_KEY")
    cx = os.getenv("GOOGLE_CX")
    if not api_key or not cx:
        return []
    try:
        import requests
        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={q}"
        r = requests.get(url, timeout=10)
        data = r.json()
        out = []
        for item in data.get("items", []):
            out.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return out
    except Exception as e:
        return [{"title": "GoogleSearchError", "url": "", "snippet": str(e)}]

# ==== منطق الدمج ====
def do_search(q: str, source: str = "auto", max_results: int = 8) -> List[Dict[str, Any]]:
    source = (source or "auto").lower()
    results: List[Dict[str, Any]] = []
    if source in ("google", "auto"):
        try:
            results = search_google(q, max_results=max_results)
        except Exception:
            results = []
    if not results and source in ("ddg", "auto", "both"):
        results = search_ddg(q, max_results=max_results)
    if source == "both":
        g = search_google(q, max_results=max_results // 2)
        d = search_ddg(q, max_results=max_results // 2)
        results = (g or []) + (d or [])
    return results

# ==== دالة التعلّم الفوري (المطلوبة من api.py) ====
def learn_from_query(q: str, source: str = "auto") -> Dict[str, Any]:
    docs = do_search(q, source=source, max_results=10)
    summary = "📘 ملخص حول «{}»:\n".format(q)
    summary += "\n".join([f"- {d['title']}: {d.get('snippet','')[:150]}" for d in docs[:5]])
    record = {
        "query": q,
        "summary": summary,
        "timestamp": datetime.utcnow().isoformat(),
        "results": docs,
    }
    _append_jsonl(NEWS_PATH, record)
    _append_jsonl(KNOW_PATH, record)
    return {"learned": len(docs), "docs": docs[:5]}

# ==== دورة التعلّم ====
def _drain_queue() -> int:
    count = 0
    global _queue
    with _queue_lock:
        if not _queue:
            return 0
        batch = _queue[:]
        _queue = []
    for item in batch:
        learn_from_query(item["q"])
        count += 1
    return count

def run_cycle_once(custom_topics: Optional[List[str]] = None) -> Dict[str, Any]:
    print(f"🔁 Auto-learning cycle @ {datetime.utcnow().isoformat()}")
    done_from_queue = _drain_queue()
    topics = custom_topics if custom_topics else TOPICS
    done_from_topics = 0
    for topic in topics:
        learn_from_query(topic)
        done_from_topics += 1
    msg = f"✅ Cycle complete — queue:{done_from_queue}, topics:{done_from_topics}"
    print(msg)
    return {"queue": done_from_queue, "topics": done_from_topics, "message": msg}

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
        run_cycle_once()

_SCHED: Optional[Scheduler] = None

def start_scheduler() -> None:
    global _SCHED
    if _SCHED:
        return
    _running.set()
    _SCHED = Scheduler()
    _SCHED.start()
    print("🔥 Worker linked to Scheduler and running.")
