from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response, JSONResponse
from .api import router as api_router
from .chat_routes import router as chat_router  # إذا لم تكن تريد واجهة الدردشة احذف هذا السطر وهذا include

app = FastAPI(title="Bassam Core", version="1.0.0")

# الصفحة الرئيسية HTML بسيطة
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"/>
<title>Bassam Core</title>
<style>
body{background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;margin:0;padding:24px}
.card{max-width:900px;margin:auto;background:#12182a;border:1px solid #24314d;border-radius:14px;padding:20px}
.row{display:flex;gap:8px;margin-top:12px}
input{flex:1;border:1px solid #2b3e63;border-radius:10px;background:#0b1324;color:#fff;padding:10px}
button{border:1px solid #2b3e63;border-radius:10px;background:#17223a;color:#fff;padding:10px 14px;cursor:pointer}
.hint{opacity:.8}
a{color:#9ecbff}
</style>
<div class="card">
  <h1>🧠 Bassam Core</h1>
  <p class="hint">الخدمة تعمل الآن. جرّب البحث السريع أو افتح التوثيق.</p>

  <div class="row">
    <input id="q" placeholder="اكتب موضوعًا للتعلّم/البحث..." />
    <button onclick="go()">بحث</button>
  </div>

  <p style="margin-top:16px">
    🔗 <a href="/docs">Swagger</a> —
    📰 <a href="/api/news" target="_blank">/api/news</a> —
    🔐 جرّب POST إلى <code>/api/secure</code>
  </p>
</div>
<script>
async function go(){
  const q = document.getElementById('q').value.trim();
  if(!q){ alert('اكتب استعلامًا'); return; }
  const r = await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})});
  const j = await r.json();
  alert('تمت إضافة المهمة: ' + JSON.stringify(j));
}
</script>
"""

# favicon لتفادي 404
@app.get("/favicon.ico")
def favicon():
    return Response(content=b"", media_type="image/x-icon")

# نقطة صحّة سريعة
@app.get("/health")
def health():
    return JSONResponse({"ok": True})

# راوترات الـ API
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(chat_router, tags=["Chat"])
