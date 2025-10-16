# bassam_core/workers/core_worker.py
import threading, time
from typing import List

_queue: List[str] = []
_status = {"running": False, "last_run": None}

def enqueue_task(q: str) -> None:
    _queue.append(q)

def query_index() -> List[str]:
    return list(_queue)

def get_status():
    return dict(_status)

def get_latest_results():
    return {"ok": True, "count": len(_queue)}

def _worker_loop():
    _status["running"] = True
    while True:
        _status["last_run"] = int(time.time())
        # هنا من الممكن تنفيذ التعلم الذاتي/جمع الأخبار إلخ
        time.sleep(600)  # كل 10 دقائق

_thread = None
def start_scheduler():
    global _thread
    if _thread and _thread.is_alive():
        return
    _thread = threading.Thread(target=_worker_loop, daemon=True)
    _thread.start()
