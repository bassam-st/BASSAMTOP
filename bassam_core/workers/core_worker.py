# -*- coding: utf-8 -*-
"""
نواة التعلّم الذاتي:
- تجمع الحوارات (سؤال/رد/نبرة) في طابور thread-safe.
- تستخرج كلمات مفتاحية عربية/إنجليزية من الحوار.
- تبحث بعمق عبر DuckDuckGo (DDGS) وتخزّن المعرفة محليًا.
- تعمل مجدولياً كل X دقائق + إمكانية التشغيل الفوري.
"""
from __future__ import annotations
import os, time, json, threading, re
from typing import List, Dict, Any
from duckduckgo_search import DDGS

# مسارات التخزين
ROOT = os.path.dirname(os.path.dirname(__file__))  # bassam_core/
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)
LEARN_PATH = os.path.join(DATA_DIR, "learned.json")   # حصيلة التعلّم
DIALOG_LOG = os.path.join(DATA_DIR, "dialogs.jsonl")  # أرشيف الحوارات (سطر/حوار)

# فترة المجدول (دقائق)
INTERVAL_MIN = int(os.getenv("LEARN_INTERVAL_MIN", "10"))

# طابور الحوارات للتعلّم
_dialog_queue: List[Dict[str, Any]] = []
_queue_lock = threading.Lock()

# قائمة وقف بسيطة (عربي/إنجليزي)
AR_STOP = set("""من في على الى إلى عن مع و أو ثم أن إن كان تكون تكونوا الذي التي الذين التي هذا هذه هناك هنا ماذا لماذا كيف حيث اذا إذا لقد قد كل على الى أيضاً ايضا جدا جداًَ ما من هو هي هم هن نحن لكم لكمنا لك لكِ لكَ عليه عليها لديهم لدي لدى بدون حتى بين عبر حسب ضد مثل ضمن خلال فوق تحت قبل بعد عند لدى بسبب داخل خارج وراء أمام خلف كثير قليل جداً بشكل بصورة لذلك لأن كون لكن ليس سوى فقط أكثر أقل بعض أي كلما ربما رغم حتى أم بل """.split())
EN_STOP = set("""
a an the and or if then else for to in on at of from into over under with without this that these those be is am are was were been being have has had do does did not no nor so just very more most less least only also as by about above below before after during between while both each few other some such than too can will would should could might may must many much
""".split())

WORD_RE = re.compile(r"[A-Za-z\u0600-\u06FF]{3,}")  # عربي/إنجليزي ≥3 حروف

def _keywords(text: str) -> List[str]:
    toks = [t.lower() for t in WORD_RE.findall(text or "")]
    out = []
    for t in toks:
        if t in EN_STOP or t in AR_STOP:
            continue
        out.append(t)
    # أعد فقط 8 كلمات كحد أقصى
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            uniq.append(t); seen.add(t)
        if len(uniq) >= 8:
            break
    return uniq

def _deep_search(queries: List[str], n_per_query: int = 4) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    if not queries: 
        return results
    try:
        with DDGS() as d:
            for q in queries:
                for r in d.text(q, max_results=n_per_query, region="sa-ar"):
                    results.append({
                        "q": q,
                        "title": r.get("title", ""),
                        "href": r.get("href", ""),
                        "body": r.get("body", ""),
                    })
    except Exception as e:
        results.append({"q": "ERROR", "title": "ddgs_failed", "href": "", "body": str(e)})
    return results

def _persist_json(path: str, obj: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def _append_jsonl(path: str, line_obj: Any):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line_obj, ensure_ascii=False) + "\n")

# ============ واجهة يستخدمها باقي النظام ============

def enqueue_dialog(user_msg: str, bot_reply: str, tone: str | None = None):
    """إضافة حوار إلى طابور التعلّم"""
    item = {
        "ts": int(time.time()),
        "user": (user_msg or "").strip(),
        "reply": (bot_reply or "").strip(),
        "tone": tone or "",
    }
    # احفظ نسخة أرشيفية فوراً
    try:
        _append_jsonl(DIALOG_LOG, item)
    except Exception:
        pass

    with _queue_lock:
        _dialog_queue.append(item)

def get_status() -> Dict[str, Any]:
    with _queue_lock:
        qlen = len(_dialog_queue)
    return {"queue_size": qlen, "interval_min": INTERVAL_MIN}

def get_latest_results(limit: int = 50) -> Dict[str, Any]:
    if not os.path.exists(LEARN_PATH):
        return {"items": []}
    try:
        data = json.load(open(LEARN_PATH, "r", encoding="utf-8"))
    except Exception:
        return {"items": []}
    items = data.get("items", [])
    return {"items": items[-limit:]}

# ============ قلب التعلّم ============

def _learn_once():
    """يسحب ما في الطابور، يستخرج كلمات مفتاحية، يبحث ويحدِّث قاعدة المعرفة."""
    with _queue_lock:
        batch = list(_dialog_queue)
        _dialog_queue.clear()

    if not batch:
        return

    # ابني قائمة استعلامات من المستخدم + الرد
    queries: List[str] = []
    for it in batch:
        kk = _keywords(it.get("user", "") + " " + it.get("reply", ""))
        # دمج بسيط لتوليد عبارات بحث
        queries += [
            " ".join(kk[:5]),
            "تعليم ذاتي " + " ".join(kk[:4]),
            "شرح " + " ".join(kk[:3]),
        ]

    # ابحث وخزّن
    results = _deep_search([q for q in queries if q.strip()], n_per_query=3)

    snapshot = {
        "ts": int(time.time()),
        "batch_size": len(batch),
        "queries": queries[:40],
        "items": results,
    }

    # ادمج على الملف السابق
    try:
        if os.path.exists(LEARN_PATH):
            old = json.load(open(LEARN_PATH, "r", encoding="utf-8"))
        else:
            old = {"history": [], "items": []}
    except Exception:
        old = {"history": [], "items": []}

    old["history"].append({"ts": snapshot["ts"], "batch": snapshot["batch_size"]})
    old["items"].extend(snapshot["items"])
    _persist_json(LEARN_PATH, old)

class AutoLearner:
    """مجدول يعمل بالخلفية"""
    def __init__(self, minutes: int = INTERVAL_MIN, run_immediately: bool = True):
        self.interval = max(2, int(minutes)) * 60
        self.run_immediately = run_immediately
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        print(f"⏰ AutoLearner started: every {self.interval/60:.1f} min")
        self._t.start()

    def shutdown(self):
        self._stop.set()
        print("⛔ AutoLearner stopped")

    def _loop(self):
        if self.run_immediately:
            _learn_once()
        while not self._stop.is_set():
            time.sleep(self.interval)
            _learn_once()

# مُثبّت عام يبدأ مع التطبيق (يُستدعى من app/main.py)
SCHEDULER = AutoLearner()
