import os, json, time
from typing import List, Dict
from ddgs import DDGS

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
MEM_PATH = os.path.join(DATA_DIR, "memory.json")

# ذاكرة قصيرة تحفظ آخر 50 تفاعل
def _load_mem() -> List[Dict]:
    try:
        with open(MEM_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_mem(items: List[Dict]):
    items = items[-50:]
    with open(MEM_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def analyze_tone(msg: str) -> str:
    m = msg.lower()
    sad = ["حزين","حزن","تعبان","محبط","فشلت","كسرت خاطري","متضايق"]
    angry = ["غاضب","زعلان","مستفز","عصّبت","ليش","خطأ","سيء"]
    excited = ["رائع","متحمس","فرحان","نجحت","جميل","ممتاز","واو"]
    if any(w in m for w in sad): return "supportive"
    if any(w in m for w in angry): return "calm"
    if any(w in m for w in excited): return "excited"
    return "friendly"

def style_wrap(text: str, tone: str) -> str:
    if tone == "supportive":
        return f"أفهم شعورك 💙. خلّينا نمشي خطوة بخطوة:\n{text}\nأنا هنا معك."
    if tone == "calm":
        return f"ولا يهمك ✋، بهدوء نحلّها:\n{text}"
    if tone == "excited":
        return f"يا سلام! 🎉 خبر جميل. التفاصيل:\n{text}"
    return f"أكيد! 🙂\n{text}"

def web_search(q: str, n:int=5) -> List[Dict]:
    out = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=n, region="sa-ar"):
            out.append({"title": r.get("title",""), "href": r.get("href",""), "body": r.get("body","")})
    return out

def summarize(points: List[Dict], question:str) -> str:
    if not points: return "لم أعثر على مصادر مناسبة حالياً."
    # تلخيص بسيط: نأخذ أهم الجمل من الملخصات
    bodies = " ".join(p.get("body","") for p in points)
    sentences = [s.strip() for s in bodies.replace("؟",".").split(".") if len(s.strip())>20]
    top = sentences[:6]
    bullets = "\n".join([f"- {s}" for s in top])
    links  = "\n".join([f"• {p.get('title','')} — {p.get('href','')}" for p in points[:5]])
    return f"ملخّص سريع للسؤال: {question}\n{bullets}\n\nأهم المصادر:\n{links}"

def answer(message: str, preferred_tone: str|None=None) -> str:
    tone = preferred_tone or analyze_tone(message)
    sr = web_search(message, n=6)
    body = summarize(sr, message)
    wrapped = style_wrap(body, tone)

    # تحديث الذاكرة القصيرة
    mem = _load_mem()
    mem.append({"ts": int(time.time()), "user": message, "tone": tone})
    _save_mem(mem)
    return wrapped
