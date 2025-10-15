set -e

APPDIR="bassam-core/app"
STATIC="bassam-core/static"

mkdir -p "$APPDIR" "$STATIC"

# 1) ملف المنطق الذكي: بحث + تلخيص + توليد رد بنبرة (مشاعر)
cat > "$APPDIR/assistant.py" <<'PY'
from typing import List, Tuple
import re, textwrap, requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from readability import Document

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118 Safari/537.36"

def _fetch(url: str, timeout: int = 15) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        r.raise_for_status()
        html = r.text
        # استخلاص المقال القابل للقراءة
        try:
            html = Document(html).summary()
        except Exception:
            pass
        soup = BeautifulSoup(html, "lxml")
        # إزالة سكريبت وستايل
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text("\n")
        # تنظيف المسافات
        text = re.sub(r"\n{2,}", "\n", text).strip()
        return text
    except Exception:
        return ""

def _summarize(text: str, max_lines: int = 6) -> List[str]:
    """
    تلخيص بسيط: نختار الجُمل/السطور الأكثر معلوماتية.
    (بدون مكتبات ثقيلة — يعمل في Replit مجاناً)
    """
    if not text:
        return []
    # قسم لسطور قصيرة
    lines = [ln.strip() for ln in text.split("\n") if len(ln.strip()) > 0]
    # رتّب حسب الطول المعتدل ووجود أرقام/نِسَب/نقاط مفيدة
    scored: List[Tuple[int, str]] = []
    for ln in lines:
        score = 0
        if 50 <= len(ln) <= 220: score += 2
        if re.search(r"\d+(\.\d+)?%?", ln): score += 1
        if re.search(r"(TCP|UDP|API|HTTP|AES|RSA|OAuth|DNS|Docker|Kubernetes|FastAPI|Python|Android|iOS)", ln, re.I):
            score += 1
        scored.append((score, ln))
    scored.sort(key=lambda t: t[0], reverse=True)
    out = [ln for _, ln in scored[:max_lines]]
    return out

def web_search(q: str, k: int = 3):
    with DDGS() as ddgs:
        for r in ddgs.text(q, max_results=k):
            # r يحتوي title, href, body
            yield r

def answer(message: str, tone: str = "warm") -> str:
    # ابحث في الويب
    results = list(web_search(message, k=3))
    bullets = []
    sources = []
    for r in results:
        url = r.get("href") or r.get("url")
        txt = _fetch(url) if url else ""
        summary_lines = _summarize(txt, max_lines=4)
        if summary_lines:
            bullets.append("• " + "\n• ".join(summary_lines))
        if url:
            sources.append(url)

    if not bullets:
        bullets = ["• لم أجد ملخصًا واضحًا فورًا – جرّبت البحث السطحي. اسألني بتفصيل أكثر أو أعد صياغة السؤال."]

    # نبرة/مشاعر
    openings = {
        "warm": "🙂 حاضر! هذا ملخص واضح ومفيد:",
        "cheer": "🚀 تمام! جهزت لك الخلاصة بحماس:",
        "formal": "🔎 خلاصة مركزة:",
        "fun": "😄 على عيني! شوف الزبدة الجميلة:"
    }
    closing = {
        "warm": "لو تحب نتعمّق في نقطة معيّنة قولي عليها 🔍",
        "cheer": "لو ودك نكمل بتفاصيل أدق على أي نقطة، أعطِني كلمة ✨",
        "formal": "اذكر النقطة التي ترغب بتفصيلها وسأتوسّع فيها.",
        "fun": "تبغاني أفتّح موضوع أكثر؟ حمّسني بكلمة ونتوغل! 😎",
    }
    opener = openings.get(tone, openings["warm"])
    footer = closing.get(tone, closing["warm"])

    body = "\n\n".join(bullets)
    srcs = ""
    if sources:
        srcs = "\n\nالمصادر (أبرز الروابط):\n" + "\n".join(f"- {u}" for u in sources)

    reply = f"{opener}\n\n{body}\n\n{footer}{srcs}"
    # قص النص الطويل حتى لا يثقل الواجهة
    return textwrap.shorten(reply, width=3000, placeholder="\n…")
PY

# 2) راوتر واجهة الدردشة + API
cat > "$APPDIR/chat_routes.py" <<'PY'
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from .assistant import answer

router = APIRouter()

class ChatIn(BaseModel):
    message: str
    tone: str = "warm"   # warm | cheer | formal | fun

@router.get("/chat", response_class=HTMLResponse)
async def chat_page():
    # صفحة دردشة بسيطة (HTML + CSS + JS في نفس الرد)
    return """<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Bassam AI – محادثة</title>
<link rel="manifest" href="/static/manifest.json">
<link rel="icon" type="image/png" href="/static/favicon.png">
<link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
<style>
  body{background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;margin:0}
  .wrap{max-width:900px;margin:0 auto;padding:16px}
  .head{display:flex;gap:8px;align-items:center;justify-content:space-between}
  .tone{background:#11182a;border:1px solid #2a3352;color:#fff;border-radius:10px;padding:8px}
  .chat{background:#0f1425;border:1px solid #273056;border-radius:16px;padding:14px;height:65vh;overflow:auto;margin-top:12px}
  .me,.bot{padding:10px 14px;border-radius:12px;max-width:90%;margin:8px 0;white-space:pre-wrap;line-height:1.6}
  .me{background:#2441ff22;border:1px solid #4e63ff44;margin-left:auto}
  .bot{background:#1a2037;border:1px solid #34406a}
  .row{display:flex;gap:8px;margin-top:12px}
  input,button{font-size:16px}
  input[type=text]{flex:1;background:#0f162b;color:#fff;border:1px solid #2a3352;border-radius:12px;padding:12px}
  button{background:#4e46dc;border:none;color:#fff;padding:12px 16px;border-radius:12px;cursor:pointer}
  button:disabled{opacity:.6;cursor:not-allowed}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <h2>🤝 محادثة مع النواة</h2>
    <select id="tone" class="tone" title="نبرة الرد">
      <option value="warm">ودّي 🤗</option>
      <option value="cheer">مشجّع 🚀</option>
      <option value="formal">رسمي 📑</option>
      <option value="fun">مرح 😄</option>
    </select>
  </div>

  <div id="chat" class="chat" aria-live="polite"></div>

  <div class="row">
    <input id="msg" type="text" placeholder="اكتب رسالتك... ثم اضغط إرسال"/>
    <button id="send">إرسال</button>
  </div>
</div>

<script>
const chat = document.getElementById('chat');
const msg  = document.getElementById('msg');
const tone = document.getElementById('tone');
const btn  = document.getElementById('send');

function addBubble(text, cls){
  const div = document.createElement('div');
  div.className = cls;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
}

async function ask(){
  const q = msg.value.trim();
  if(!q) return;
  addBubble(q, 'me');
  msg.value = '';
  btn.disabled = true;

  try{
    const r = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:q, tone:tone.value})
    });
    const data = await r.json();
    addBubble(data.reply || 'حدث خطأ في الإجابة.', 'bot');
  }catch(e){
    addBubble('تعذّر الاتصال. حاول ثانية.', 'bot');
  }finally{
    btn.disabled = false;
    msg.focus();
  }
}

btn.addEventListener('click', ask);
msg.addEventListener('keydown', e=>{
  if(e.key === 'Enter'){ ask(); }
});

// رسالة ترحيب
addBubble('أهلاً! اكتب سؤالك، وسأبحث وألخّص لك بإذن الله 🙂', 'bot');
</script>
</body></html>"""

@router.post("/api/chat")
async def api_chat(payload: ChatIn):
    reply = answer(payload.message, payload.tone)
    return JSONResponse({"reply": reply})
PY

# 3) ضمّ الراوتر في main.py إن لم يكن مضمومًا
if ! grep -q "from \.chat_routes import router as chat_router" "$APPDIR/main.py" 2>/dev/null; then
  printf "\nfrom .chat_routes import router as chat_router\napp.include_router(chat_router)\n" >> "$APPDIR/main.py"
fi

# 4) تأكد من الحزم (قد تكون مثبّتة من قبل)
python3 -m pip install --no-user ddgs readability-lxml beautifulsoup4 lxml requests >/dev/null 2>&1 || true

echo "✅ Chat UI added. افتح /chat بعد تشغيل السيرفر."
