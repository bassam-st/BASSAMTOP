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
.wrap{max-width:820px;margin:24px auto;padding:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.badge{padding:4px 10px;border-radius:999px;border:1px solid var(--line);font-size:12px}
.badge.ok{border-color:#2b9856;color:#a6f3c0}
.badge.idle{border-color:#8a8a8a;color:#ddd}
.search{position:relative;margin-top:10px}
.search input{
  width:100%; max-width:520px;
  padding:12px 44px 12px 12px; border-radius:12px;
  border:1px solid var(--line); background:#0b1324; color:#fff; outline:none;
}
.search button{
  position:absolute; right:2px; top:2px; bottom:2px; width:40px;
  border:1px solid var(--line); background:#14223a; color:#fff;
  border-radius:10px; cursor:pointer;
}
small,.muted{color:var(--muted)}
.grid{margin-top:12px; display:grid; gap:10px; grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
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

    <div class="search">
      <input id="q" placeholder="اكتب موضوعًا… مثال: أساسيات الشبكات" />
      <button id="goBtn" title="بحث" onclick="go()">🔎</button>
    </div>
    <small class="muted">عند الضغط على بحث: إضافة للصف → تشغيل دورة تعلّم فورية → عرض النتائج أدناه.</small>

    <div id="notice" class="notice"></div>
    <div id="results" class="grid"></div>
  </div>
</div>

<script>
let pollTimer=null, stateTimer=null;

function setBadge(state, nextTs){
  const el=document.getElementById('stateBadge');
  if(state==='running'){ el.className='badge ok'; el.textContent='الحالة: يعمل الآن'; }
  else{ el.className='badge idle'; el.textContent='الحالة: غير نشط' + (nextTs? ' — الدورة القادمة: '+new Date(nextTs).toLocaleTimeString(): ''); }
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
  try{ const st=await api('/api/learn/state'); setBadge(st.state||st.status||'idle', st.next_run_at); }catch(e){}
}

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

async function startPolling(){
  clearInterval(pollTimer);
  pollTimer=setInterval(async()=>{ try{
    const data=await api('/api/learn/latest?limit=8');
    render(data.docs||data||[]);
  }catch(e){} }, 5000);
}

async function go(){
  const btn=document.getElementById('goBtn'); const q=document.getElementById('q').value.trim();
  if(!q) return alert('اكتب موضوعًا أولاً');
  btn.disabled=true; show('⏳ إرسال الطلب وتشغيل دورة التعلّم…');
  try{
    await api('/api/search',{method:'POST',body:JSON.stringify({q})});
    await api('/api/learn/run',{method:'POST',body:JSON.stringify({topics:[q]})});
    hide(); show('✅ تم التنفيذ. يتم تحديث النتائج تلقائيًا أسفل.');
    refreshState(); startPolling();
  }catch(e){ show('❌ خطأ: '+e.message); }
  finally{ btn.disabled=false; }
}

// Enter = بحث
document.getElementById('q').addEventListener('keydown',e=>{ if(e.key==='Enter'){ e.preventDefault(); go(); }});

stateTimer=setInterval(refreshState, 6000);
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
