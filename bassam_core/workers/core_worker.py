# bassam_core/workers/core_worker.py
import os, threading, time
from typing import List, Dict, Optional
from .search_providers import search_google, search_ddg
from ..app.db import save_docs, get_recent_docs

# ====== صف انتظار بسيط ======
_queue: List[str] = []
_lock = threading.Lock()

# ====== حالة المجدول ======
_state = {
    "active": False,
    "interval_min": int(os.getenv("LEARN_INTERVAL_MIN", "30") or "30"),
    "last_cycle_ts": None,
    "cycles_done": 0,
}

def enqueue_task(q: str):
    with _lock:
        _queue.append(q)

def query_index() -> List[str]:
    with _lock:
        return list(_queue)

def get_status() -> Dict:
    return dict(_state)

def get_latest_results(limit: int = 10):
    return get_recent_docs(limit)

# ====== البحث الفعلي (جوجل -> DDG) ======
def do_search(q: str, source: str = "auto", max_results: int = 8) -> List[Dict]:
    source = (source or "auto").lower()
    results: List[Dict] = []
    if source in ("google", "auto"):
        try:
            results = search_google(q, max_results=max_results)
        except Exception:
            results = []
    if not results and source in ("ddg", "auto", "both"):
        results = search_ddg(q, max_results=max_results)
    if source == "both":
        try:
            g = search_google(q, max_results=max_results//2 or 4)
        except Exception:
            g = []
        d = search_ddg(q, max_results=max_results - len(g))
        results = (g or []) + (d or [])
    return results

def learn_from_query(q: str, source: str = "auto") -> Dict:
    docs = do_search(q, source=source, max_results=10)
    if docs:
        save_docs(docs)
    return {"learned": len(docs), "docs": docs[:5]}

def run_cycle_once(topics: Optional[List[str]] = None) -> Dict:
    topics = topics or os.getenv("TOPICS", "الذكاء الاصطناعي, الأمن السيبراني").split(",")
    total = 0
    for t in [x.strip() for x in topics if x.strip()]:
        total += learn_from_query(t).get("learned", 0)
        time.sleep(1)
    _state["last_cycle_ts"] = int(time.time())
    _state["cycles_done"] += 1
    return {"message": "cycle_done", "topics": len(topics), "learned": total}

# ====== حلقة الخلفية للمجدول ======
def _loop():
    while _state["active"]:
        # نفّذ أي عناصر في الصف
        while True:
            with _lock:
                if not _queue: break
                q = _queue.pop(0)
            try:
                learn_from_query(q)
            except Exception:
                pass

        # دورة تعلّم تلقائية
        try:
            run_cycle_once()
        except Exception:
            pass

        # نوم للفاصل
        interval = max(1, int(_state["interval_min"]))
        for _ in range(interval * 60):
            if not _state["active"]:
                return
            time.sleep(1)

def start_scheduler():
    if _state["active"]:
        return
    _state["active"] = True
    threading.Thread(target=_loop, daemon=True).start()

def stop_scheduler():
    _state["active"] = False
