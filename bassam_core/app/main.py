# bassam_core/app/main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from .api import router as api_router
from workers.core_worker import start_scheduler

app = FastAPI(title="Bassam Core", version="1.0.0")
app.include_router(api_router, prefix="/api", tags=["API"])

@app.get("/", response_class=HTMLResponse)
def index():
    html = """
<!doctype html><meta charset="utf-8"><title>Bassam Core</title>
<style>
:root{--bg:#0b1220;--card:#0f1a2b;--muted:#a5b4d4;--line:#1e2b44}
*{box-sizing:border-box} body{background:var(--bg);color:#fff;font-family:Tahoma,Arial;margin:0}
.wrap{max-width:860px;margin:24px auto;padding:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{padding:4px 10px;border-radius:999px;border:1px solid var(--line);font-size:12px}
.badge.ok{border-color:#2b9856;color:#a6f3c0}
.badge.idle{border-color:#8a8a8a;color:#ddd}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
select,input,button{border:1px solid var(--line);background:#0b1324;color:#fff;border-radius:10px}
input{flex:1;min-width:220px;padding:10px}
select{padding:10px}
button{padding:10px 12px;background:#14223a;cursor:pointer}
small{opacity:.8} a{color:#9ad}
.grid{margin-top:12px; display:grid; gap:10px; grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.item{background:#0b1628;border:1px solid var(--line);border-radius:10px;padding:10px}
.item h4{margin:0 0 6px 0; font-size:15px}
.item p{margin:0; font-size:13px; line-height:1.5}
.notice{margin-top:10px; font-family:ui-monospace,monospace; background:#0b1324; border:1px dashed var(--line); padding:8px; border-radius:8px; color:#cde; display:none}
</style>

<div class="wrap">
  <div class="card">
    <div class="header">
      <h3 style="margin:0;">Bassam Core 🧠</h3>
      <span id="stateBadge" class="badge idle">الحالة: غير نشط</span>
      <span class="muted">— <a href="/docs" target="_blank">Swagger</a> — <a href="/api/news" target="_blank">/api/news</a></span>
    </div>

    <div class="row">
      <select id="src">
        <option value="auto">Auto (Google → DDG)</option>
        <option value="google">Google فقط</option>
        <option value="ddg">DuckDuckGo فقط</option>
        <option value="both">دمج الإثنين</option>
      </select>
      <input id="q" placeholder="اكتب موضوعًا… مثال: أساسيات الشبكات" />
      <button id="goQueue" onclick="goQueue()">بحث (صف + تعلّم)</button>
      <button id="goImmediate" onclick="goImmediate()">بحث فوري + تعلّم</button>
    </div>
    <small class="muted">الأول: يضيف للصف ثم يشغّل دورة ويتابع النتائج. الثاني: يبحث الآن ويعرض نتيجة فورية ويتعلّم فورًا.</small>

    <div id="notice" class="notice"></div>
    <div id="results" class="grid"></div>
  </div>
</div>

<script>
let pollTimer=null;

function setBadge(active){
  const el=document.getElementById('stateBadge');
  if(active){ el.className='badge ok'; el.textContent='الحالة: نشط'; }
  else{ el.className='badge idle'; el.textContent='الحالة: غير نشط'; }
}
async function refreshState(){
  try{
    const r=await fetch('/api/learn/state'); const j=await r.json();
    setBadge(!!j.active);
  }catch(e){ setBadge(false); }
}
function show(msg){ const n=document.getElementById('notice'); n.style.display='block'; n.textContent=typeof msg==='string'?msg:JSON.stringify(msg,null,2); }
function hide(){ const n=document.getElementById('notice'); n.style.display='none'; }
function esc(s){return String(s||'').replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]))}
function render(items){
  const box=document.getElementById('results'); box.innerHTML='';
  (Array.isArray(items)?items:[]).forEach(x=>{
    const d=document.createElement('div'); d.className='item';
    const title=esc(x.title||x.topic||'بدون عنوان');
    const sum=esc(x.summary||x.snippet||x.text||'');
    const url=x.url||x.link;
    d.innerHTML='<h4>'+title+'</h4>'+(sum?'<p>'+sum+'</p>':'')+(url?'<p style="margin-top:6px"><a target="_blank" href="'+url+'">فتح المصدر</a></p>':'');
    box.appendChild(d);
  });
}
async function pollLatest(){
  clearInterval(pollTimer);
  pollTimer=setInterval(async()=>{
    try{
      const r=await fetch('/api/learn/latest?limit=8'); const j=await r.json();
      render(j.docs||[]);
    }catch(e){}
  }, 5000);
}

// 1) بحث عبر الصف + تشغيل دورة + متابعة النتائج
async function goQueue(){
  const q=document.getElementById('q').value.trim();
  if(!q) return alert('اكتب موضوعًا أولاً');
  show('⏳ إرسال للصف ثم تشغيل دورة التعلّم…');
  try{
    await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})});
    await fetch('/api/learn/run',{method:'POST'});
    hide(); show('✅ تم التنفيذ. يتم تحديث النتائج تلقائيًا بالأسفل.');
    refreshState(); pollLatest();
  }catch(e){ show('❌ خطأ: '+e.message); }
}

// 2) بحث فوري + تعلم فوري (Google → DDG)
async function goImmediate(){
  const q=document.getElementById('q').value.trim();
  const src=document.getElementById('src').value;
  if(!q) return alert('اكتب موضوعًا أولاً');
  show('🔎 بحث فوري جارٍ…');
  try{
    const r=await fetch('/api/search_immediate',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({q, source:src, learn:true})});
    const j=await r.json();
    const list=j.results||[];
    document.getElementById('results').innerHTML='';
    render(list);
    show(`✅ مزوّد: ${j.provider} — النتائج: ${list.length} — تم التعلّم: ${j.learned||0}`);
    refreshState();
  }catch(e){ show('❌ خطأ: '+e.message); }
}

// Enter = بحث فوري
document.getElementById('q').addEventListener('keydown', e=>{ if(e.key==='Enter'){ e.preventDefault(); goImmediate(); }});
refreshState();
</script>
"""
    return HTMLResponse(html)

@app.get("/health")
def health():
    return JSONResponse({"ok": True})

@app.on_event("startup")
def _startup():
    start_scheduler()
