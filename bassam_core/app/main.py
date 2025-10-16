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
:root{--bg:#0b1220;--card:#0f1a2b;--muted:#a5b4d4;--line:#1e2b44;--accent:#5aa9ff}
*{box-sizing:border-box} body{background:var(--bg);color:#fff;font-family:Tahoma,Arial;margin:0}
.wrap{max-width:1000px;margin:40px auto;padding:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px}
.row{display:flex;gap:8px;margin-top:10px}
input{flex:1;padding:12px 14px;border-radius:12px;border:1px solid var(--line);background:#0b1324;color:#fff;outline:none}
button{padding:12px 16px;border-radius:12px;border:1px solid var(--line);background:#14223a;color:#fff;cursor:pointer}
button[disabled]{opacity:.6;cursor:not-allowed}
small, .muted{color:var(--muted)}
a{color:#9ad}
.badge{display:inline-flex;align-items:center;gap:6px;background:#0d1f36;border:1px solid var(--line);padding:5px 10px;border-radius:999px;font-size:13px}
.badge.ok{border-color:#2b9856;color:#a6f3c0}
.badge.idle{border-color:#8a8a8a;color:#ddd}
.res{margin-top:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.item{background:#0b1628;border:1px solid var(--line);border-radius:12px;padding:12px}
.item h4{margin:0 0 8px 0;font-size:16px}
.item p{margin:0;font-size:14px;line-height:1.5}
.code{font-family:ui-monospace, SFMono-Regular, Menlo, monospace;background:#0b1324;border:1px dashed var(--line);padding:8px;border-radius:8px;color:#cde}
.hr{height:1px;background:var(--line);margin:14px 0}
.kbd{background:#0b1324;border:1px solid var(--line);padding:2px 6px;border-radius:6px}
</style>

<div class="wrap">
  <div class="card">
    <h2 style="margin:0 0 6px 0;">Bassam Core 🧠</h2>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span id="stateBadge" class="badge idle">الحالة: غير نشط</span>
      <span class="muted">– افتح <a href="/docs" target="_blank">Swagger</a> أو جرّب من هنا مباشرة</span>
    </div>

    <div class="row">
      <input id="q" placeholder="اكتب موضوعًا للبحث والتعلّم... مثال: أساسيات الشبكات" />
      <button id="goBtn" onclick="go()">بحث</button>
    </div>

    <div class="muted" style="margin-top:10px">
      ✔️ عند الضغط على <b>بحث</b> سيتم: إضافة الطلب إلى الصفّ → تشغيل دورة تعلّم فورية → عرض أحدث النتائج هنا.  
      روابط سريعة: <a href="/api/news" target="_blank">/api/news</a> – <span class="kbd">POST</span> <code>/api/secure</code>
    </div>

    <div class="hr"></div>

    <div id="notice" class="code" style="display:none"></div>
    <div id="results" class="res"></div>
  </div>
</div>

<script>
let pollTimer=null, stateTimer=null;

function setBadge(state, nextTs){
  const el=document.getElementById('stateBadge');
  if(!el) return;
  if(state==='running'){ el.className='badge ok'; el.textContent='الحالة: يعمل الآن'; }
  else {
    el.className='badge idle';
    el.textContent = 'الحالة: غير نشط' + (nextTs ? ' – دورة قادمة: ' + new Date(nextTs).toLocaleTimeString() : '');
  }
}

function show(msg){
  const n=document.getElementById('notice');
  n.style.display='block';
  n.textContent=typeof msg==='string'?msg:JSON.stringify(msg,null,2);
}

function clearNotice(){ const n=document.getElementById('notice'); n.style.display='none'; n.textContent=''; }

async function api(path, opt={}){
  const res = await fetch(path, Object.assign({headers:{'Content-Type':'application/json'}}, opt));
  if(!res.ok){ throw new Error('HTTP '+res.status); }
  return await res.json().catch(()=>({ok:true}));
}

async function refreshState(){
  try{
    const st = await api('/api/learn/state');
    setBadge(st.state || st.status || 'idle', st.next_run_at || null);
  }catch(e){ /* ignore */ }
}

async function pollLatest(filterTopic){
  clearInterval(pollTimer);
  pollTimer = setInterval(async ()=>{
    try{
      const data = await api('/api/learn/latest?limit=8');
      renderResults(data.docs || data || [], filterTopic);
    }catch(e){/* ignore */}
  }, 5000);
}

function renderResults(items, filterTopic){
  const g = document.getElementById('results');
  g.innerHTML='';
  const list = Array.isArray(items) ? items : [];
  const filtered = filterTopic
    ? list.filter(x => (x.topic||'').toLowerCase().includes(filterTopic.toLowerCase()))
    : list;
  (filtered.length?filtered:list).forEach(x=>{
    const div=document.createElement('div'); div.className='item';
    const title = x.title || x.topic || 'بدون عنوان';
    const sum = x.summary || x.snippet || x.text || '';
    const url = x.url || x.link;
    div.innerHTML = '<h4>'+escapeHtml(title)+'</h4>'
      + (sum?'<p>'+escapeHtml(sum)+'</p>':'')
      + (url?'<p style="margin-top:8px"><a href="'+url+'" target="_blank">فتح المصدر</a></p>':'');
    g.appendChild(div);
  });
}

function escapeHtml(s){return String(s).replace(/[&<>"']/g,m=>({ "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;" }[m]))}

async function go(){
  const btn=document.getElementById('goBtn');
  const q=document.getElementById('q').value.trim();
  if(!q) return alert('اكتب موضوعًا أولاً');
  btn.disabled=true; show('⏳ يتم الإرسال والتشغيل…');

  try{
    // 1) أضف للصف
    const add = await api('/api/search',{method:'POST',body:JSON.stringify({q})});
    // 2) شغّل دورة واحدة ومرّر الموضوع لتحفيز الأولوية
    const run = await api('/api/learn/run',{method:'POST',body:JSON.stringify({topics:[q]})});
    show('✅ تمت إضافة المهمة وتشغيل دورة التعلّم. سيتم تحديث النتائج تلقائيًا أدناه.');
    refreshState();
    pollLatest(q);
  }catch(e){
    show('❌ حدث خطأ أثناء التنفيذ: '+e.message);
  }finally{
    btn.disabled=false;
  }
}

// تشغيل مراقبة الحالة الدورية
stateTimer = setInterval(refreshState, 6000);
refreshState();
pollLatest(null);
</script>
"""
    return HTMLResponse(html)

@app.get("/health")
def health():
    return JSONResponse({"ok": True})

@app.on_event("startup")
def _startup():
    # تشغيل المجدول مع بدء الخادم
    start_scheduler()
