import threading, time
from workers.news_worker import enqueue_query

class AutoIndexer:
    def __init__(self, interval_minutes=15, run_immediately=True):
        self.interval = interval_minutes * 60
        self.run_immediately = run_immediately
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
    def start(self):
        print(f"🕒 Scheduler started, every {self.interval/60} min")
        self.thread.start()
    def _loop(self):
        if self.run_immediately:
            enqueue_query("latest AI programming frameworks")
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            enqueue_query("AI + programming + networking + systems")
    def shutdown(self):
        print("🛑 Scheduler stopped")
        self._stop_event.set()
