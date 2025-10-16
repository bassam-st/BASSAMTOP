# أعلى الملف:
from datetime import datetime, timedelta
# ...
_running = threading.Event()
_NEXT_AT: Optional[str] = None  # <-- جديد

def get_status() -> Dict[str, Any]:
    """حالة النظام والمجدول."""
    return {
        "running": _running.is_set(),
        "interval_min": INTERVAL_MIN,
        "interval_sec": INTERVAL_SEC,
        "queue_size": len(_queue),
        "topics": TOPICS,
        "next_run_at": _NEXT_AT,   # <-- جديد
    }
