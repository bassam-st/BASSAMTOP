# bassam_core/app/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from .api import router as api_router
from workers.core_worker import start_scheduler

app = FastAPI(title="Bassam Core", version="1.0.0")

# ضمّ مسارات الـ API
app.include_router(api_router, prefix="/api", tags=["API"])

# صفحة رئيسية بسيطة
@app.get("/", response_class=HTMLResponse)
def index():
    html = """
<!doctype html><meta charset="utf-8"><title>Bassam Core</title>
<style>
body{background:#0b1220;color:#fff;font-family:Tahoma,Arial;margin:0}
.wrap{max-width:900px;margin:40px auto;padding:16px}
.card{background:#0f1a2b;border:1px solid #1e2b44;border-radius:14px;padding:20px}
.row{display:flex;gap:8px} input{flex:1;padding:10px;border-radius:10px;border:1px solid #2b3e63;background:#0b1324;color:#fff}
button{padding:10px 16px;border-radius:10px;border:1px solid #2b3e63;background:#14223a;color:#fff;cursor:pointer}
a{color:#9ad} small{opacity:.8}
</style>
<div class="wrap">
  <div class="card">
    <h2>Bassam Core 🧠</h2>
    <p>الخدمة تعمل الآن ✅</p>
    <p>جرّب البحث السريع أو افتح التوثيق أدناه.</p>
    <div class="row">
      <input id="q" placeholder="اكتب موضوعًا للبحث أو التعلّم..." />
      <button onclick="go()">🔍 بحث</button>
    </div>
    <p><small>توثيق API: <a href="/docs" target="_blank">Swagger</a></small></p>
    <p><small>عرض الأخبار: <a href="/api/news" target="_blank">/api/news</a></small></p>
    <p><small>تشغيل دورة تعلّم يدويًا: <a href="#" onclick="run()">/api/learn/run</a></small></p>
    <p><small>عرض حالة المجدول: <a href="/api/learn/state" target="_blank">/api/learn/state</a></small></p>
  </div>
</div>
<script>
async function go(){
  const q=document.getElementById('q').value.trim();
  if(!q) return alert('❗ اكتب شيئًا أولاً');
  await fetch('/api/search',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({q})
  });
  alert('✅ تمت إضافة المهمة إلى صف التعلّم.');
}
async function run(){
  const r=await fetch('/api/learn/run',{method:'POST'}); 
  const j=await r.json(); 
  alert('🔁 ' + (j.message || 'تم تشغيل دورة التعلّم.'));
}
</script>
"""
    return HTMLResponse(html)

@app.get("/health")
def health():
    """نقطة فحص بسيطة."""
    return JSONResponse({"ok": True})

# بدء المجدول تلقائيًا عند تشغيل الخادم
@app.on_event("startup")
def _startup():
    start_scheduler()
