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
.wrap{max-width:900px;margin:24px auto;padding:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{padding:4px 10px;border-radius:999px;border:1px solid var(--line);font-size:12px}
.badge.ok{border-color:#2b9856;color:#a6f3c0}
.badge.idle{border-color:#8a8a8a;color:#ddd}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
select, input{background:#0b1324;border:1px solid var(--line);color:#fff;border-radius:10px;padding:10px}
input{min-width:260px}
.btn{border:1px solid var(--line);background:#14223a;color:#fff;border-radius:10px;padding:10px 12px;cursor:pointer}
small,.muted{color:#a5b4d4}
.grid{margin-top:12px; display:grid; gap:10px; grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.item{background:#0b1628;border:1px solid var(--line);border-radius:10px;padding:10px}
.item h4{margin:0 0 6px 0; font-size:15px}
.item p{margin:0; font-size:13px; line-height:1.5}
.notice{margin-top:10px; font-family:ui-monospace,monospace; background:#0b1324; border:1px dashed var(--line); padding:8px; border-radius:8px; color:#cde; display:none}
a{color:#9ad}
</style>

<div class="wrap">
  <div class="card">
    <div class="header">
      <h3 style="margin:0;">Bassam Core 🧠</h3>
      <span id="stateBadge" class="badge idle">الحالة: غير نشط</span>
      <span class="muted">— <a href="/docs" target="_blank">Swagger</a> — <a href="/api/news" target="_blank">/api/news</a></span>
    </div>

    <div class="controls">
      <select id="src">
        <option value="auto">Auto (Google → DDG)</option>
        <option value="google">Google فقط</option>
        <option value="ddg">DuckDuckGo فقط</option>
        <option value="both">Google + DDG</option>
      </select>
      <input id="q" placeholder="اكتب موضوعًا… مثال: مباريات اليوم" />
      <button class="btn" onclick="go('fast')">بحث فوري + تعلّم</button>
      <button class="btn" onclick="go('queued')">بحث (صف + تعلّم)</button>
    </div>
    <small class="muted">الأول: يبحث الآن ويخزّن ويعرض. الثاني: يضيف للصف ثم يشغّل دورة ويعرض.</small>

    <div id="notice" class="notice"></div>
    <div id="results" class="grid"></div>
  </div>
</div>

<script>
let pollTimer=null;

function setBadge(running){
  const el=document.getElementById('stateBadge');
  if(running){ el.className='badge ok'; el.textContent='الحالة: يعمل الآن'; }
  else{ el.className='badge idle'; el.textContent='الحالة: غير نشط'; }
}
function show(msg){ const n=document.getElementById('notice'); n.style.display='block'; n.textContent=typeof msg==='string'?msg:JSON.stringify(msg,null,2); }
function hide(){ const n=document.getElementById('notice'); n.style.display='none'; }
function esc(s){return String(s||'').replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[m]))}

async function api(path, opt={}){
  const res = await fetch(path, Object.assign({headers:{'Content-Type':'application/json'}}, opt));
  if(!res.ok) throw new Error('HTTP '+res.status);
  try{ return await res.json(); }catch{ return {}; }
}

async function refreshState(){
  try{ const st=await api('/api/learn/state'); setBadge(!!st.running); }catch(e){}
}

function render(items){
  const box=document.getElementById('results'); box.innerHTML='';
  (Array.isArray(items)?items:[]).forEach(x=>{
    const d=document.createElement('div'); d.className='item';
    const title=esc(x.title||x.query||x.topic||'بدون عنوان');
    const sum=esc(x.summary||x.snippet||x.text||'');
    const url=x.url||x.link;
    d.innerHTML='<h4>'+title+'</h4>'+(sum?'<p>'+sum+'</p>':'')+(url?'<p style="margin-top:6px"><a target="_blank" href="'+url+'">فتح المصدر</a></p>':'');
    box.appendChild(d);
  });
}

async function startPolling(){
  clearInterval(pollTimer);
  pollTimer=setInterval(async()=>{ try{
    const data=await api('/api/learn/latest?limit=8');
    render(data.docs||data||[]);
    refreshState();
  }catch(e){} }, 4000);
}

async function go(mode){
  const q=document.getElementById('q').value.trim();
  const src=document.getElementById('src').value;
  if(!q) return alert('اكتب موضوعًا أولاً');

  try{
    if(mode==='fast'){ // تعلّم فوري لسؤال واحد
      show('⏳ يبحث الآن ويتعلّم…');
      await api('/api/learn/fast?q='+encodeURIComponent(q)+'&source='+encodeURIComponent(src), {method:'POST'});
    }else{            // صف + تعلّم
      show('⏳ إضافة للصف ثم تشغيل دورة…');
      await api('/api/search',{method:'POST',body:JSON.stringify({q})});
      await api('/api/learn/run',{method:'POST',body:JSON.stringify({topics:[q]})});
    }
    hide(); show('✅ تم — يتم تحديث النتائج أسفل تلقائيًا.');
    startPolling();
  }catch(e){
    show('❌ خطأ: '+e.message);
  }
}

// Enter = بحث فوري
document.getElementById('q').addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); go('fast'); }});
refreshState(); startPolling();
</script>
"""
    return HTMLResponse(html)

@app.get("/health")
def health():
    return JSONResponse({"ok": True})

@app.on_event("startup")
def _startup():
    start_scheduler()
