import os, time, json, threading
from ddgs import DDGS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
NEWS_PATH = os.path.join(DATA_DIR, "news.json")

INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "10"))  # كل 10 دقائق
TOPICS = [
    "أحدث تقنيات الذكاء الاصطناعي",
    "أطر البرمجة الحديثة",
    "شبكات الكمبيوتر والأنظمة",
    "أمن المعلومات والتشفير",
    "أخبار التقنية والبرمجيات مفتوحة المصدر"
]

def deep_search(q, n=8):
    items=[]
    with DDGS() as d:
        for r in d.text(q, max_results=n, region="sa-ar"):
            items.append({"title": r.get("title",""), "href": r.get("href",""), "body": r.get("body","")})
    return items

def learn_once():
    store={"ts": int(time.time()), "topics":{}}
    for t in TOPICS:
        store["topics"][t]=deep_search(t, n=6)
    try:
        with open(NEWS_PATH,"w",encoding="utf-8") as f:
            json.dump(store,f,ensure_ascii=False,indent=2)
    except Exception: pass

class Scheduler:
    def __init__(self, minutes:int=INTERVAL_MIN, run_immediately=True):
        self.interval = max(2, minutes) * 60
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.run_immediately = run_immediately
    def start(self):
        print(f"⏰ Scheduler started, every {self.interval/60:.1f} min")
        self.thread.start()
    def _loop(self):
        if self.run_immediately: learn_once()
        while not self._stop.is_set():
            time.sleep(self.interval)
            learn_once()
    def shutdown(self):
        print("⛔ Scheduler stopped")
        self._stop.set()

SCHEDULER = Scheduler()
from typing import List

# تخزين مؤقت للأسئلة قيد التعلم
query_queue: List[str] = []

def enqueue_query(q: str):
    """إضافة استعلام إلى قائمة الانتظار"""
    query_queue.append(q)
    print(f"🧠 تمت إضافة استعلام للتعلّم: {q[:50]}...")

def query_index() -> List[str]:
    """عرض قائمة الاستعلامات الحالية"""
    return query_queue
