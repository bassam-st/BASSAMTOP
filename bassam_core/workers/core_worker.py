import os, time, json, threading
from typing import List, Dict, Any
from duckduckgo_search import DDGS

# مجلد تخزين البيانات داخل الحاوية
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
NEWS_PATH = os.path.join(DATA_DIR, "news.json")

# فترة التعلّم بالدقائق
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "10"))

# موضوعات افتراضية للتعلّم
TOPICS = [
    "أحدث تقنيات الذكاء الاصطناعي",
    "أطر البرمجة الحديثة",
    "شبكات الكمبيوتر والأنظمة",
    "أمن المعلومات والتشفير",
    "أخبار التقنية والبرمجيات مفتوحة المصدر",
]

# طابور استعلامات المستخدم للتعلّم
query_queue: List[str] = []

def deep_search(q: str, n: int = 8, region: str = "sa-ar") -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    try:
        with DDGS() as d:
            for r in d.text(q, max_results=n, region=region):
                items.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", "")
                })
    except Exception as e:
        items.append({"title": "ERR", "href": "", "body": f"search-error: {e}"})
    return items

def learn_once() -> None:
    """جولة تعلّم واحدة: من المواضيع + من طابور الاستعلامات"""
    store = {"ts": int(time.time()), "topics": {}, "queries": {}}

    for t in TOPICS:
        store["topics"][t] = deep_search(t, n=6)

    # معالجة الاستعلامات المضافة من المستخدم
    # ننسخ الطابور ثم نفرّغه لتجنّب التداخل مع الثريد
    pending = list(query_queue)
    query_queue.clear()
    for q in pending:
        store["queries"][q] = deep_search(q, n=6)

    try:
        with open(NEWS_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

class Scheduler:
    """مشغّل دوري بسيط بالـ threading"""
    def __init__(self, minutes: int = INTERVAL_MIN, run_immediately: bool = True):
        self.interval = max(2, minutes) * 60
        self._stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.run_immediately = run_immediately

    def start(self):
        print(f"⏰ Scheduler started, every {self.interval/60:.1f} min")
        self.thread.start()

    def _loop(self):
        if self.run_immediately:
            learn_once()
        while not self._stop.is_set():
            time.sleep(self.interval)
            learn_once()

    def shutdown(self):
        print("⛔ Scheduler stopped")
        self._stop.set()

# واجهة بسيطة للطابور
def enqueue_query(q: str) -> None:
    if not isinstance(q, str) or not q.strip():
        return
    query_queue.append(q.strip())
    print(f"🧠 queued for learning: {q[:80]}")

def query_index() -> List[str]:
    return list(query_queue)

# نسخة عالمية يستوردها التطبيق
SCHEDULER = Scheduler()
