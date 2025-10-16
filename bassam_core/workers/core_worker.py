# bassam_core/workers/core_worker.py
import threading
import time
from typing import List, Dict, Any
from duckduckgo_search import DDGS

# --------- حالة عامة ---------
_queue: List[str] = []
_lock = threading.Lock()
_running = False
_last_query: str | None = None
_latest: Dict[str, Any] = {"query": None, "ts": None, "items": []}

def _search_ddg(q: str, n: int = 8) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    # region تقدر تغيّرها لو تحب
    with DDGS() as d:
        for r in d.text(q, max_results=n, region="sa-ar"):
            items.append({
                "title": r.get("title", ""),
                "href": r.get("href", ""),
                "body": r.get("body", ""),
            })
    return items

def _worker_loop():
    global _running, _last_query, _latest
    while True:
        with _lock:
            if not _queue:
                _running = False
                return
            q = _queue.pop(0)
            _last_query = q
        try:
            items = _search_ddg(q, n=8)
            _latest = {"query": q, "ts": int(time.time()), "items": items}
        except Exception as e:
            _latest = {"query": q, "ts": int(time.time()), "error": str(e), "items": []}
        # مهلة خفيفة بين المهمات
        time.sleep(0.5)

# --------- واجهة عامة يُستورد منها في api.py ---------
def enqueue_task(q: str) -> None:
    """إضافة استعلام للتنفيذ في الخلفية."""
    global _running
    q = (q or "").strip()
    if not q:
        return
    with _lock:
        _queue.append(q)
        if not _running:
            _running = True
            t = threading.Thread(target=_worker_loop, daemon=True)
            t.start()

def query_index() -> List[str]:
    with _lock:
        return list(_queue)

def get_status() -> Dict[str, Any]:
    with _lock:
        return {
            "queue_len": len(_queue),
            "running": _running,
            "last_query": _last_query,
            "last_ts": _latest.get("ts"),
        }

def get_latest_results() -> Dict[str, Any]:
    return dict(_latest)
