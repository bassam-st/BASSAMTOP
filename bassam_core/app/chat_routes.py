from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from .assistant import answer, analyze_tone
from workers.core_worker import enqueue_dialog  # <-- الجديد

router = APIRouter()

class ChatIn(BaseModel):
    message: str
    tone: str | None = None

@router.get("/chat", response_class=HTMLResponse)
def chat_page():
    html = """
<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"/>
<title>💬 الدردشة مع نواة بسام الذكي</title>
<style>
body{background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;
display:flex;flex-direction:column;align-items:center;gap:16px;margin:0;padding:24px}
.card{width:min(900px,96%);background:#12182a;border:1px solid #24314d;
border-radius:14px;padding:16px;box-shadow:0 0 12px #0005}
h1{margin:0 0 10px;text-align:center}
#log{height:50vh;overflow:auto;background:#0f1424;border:1px solid #1f2b45;
border-radius:12px;padding:12px;font-size:15px;line-height:1.6}
.msg{margin:6px 0;padding:10px;border-radius:10px;max-width:80%}
.user{background:#1f2b45;align-self:flex-end}
.bot{background:#19324e;align-self:flex-start}
.row{display:flex;gap:8px;width:100%}
input,select,button{border-radius:10px;border:1px solid #2b3e63;
background:#0b1324;color:#fff;padding:10px}
button{cursor:pointer;transition:0.2s}
button:hover{background:#1a2648}
.mic{border:1px dashed #3c6}
</style>

<div class="card">
  <h1>🤖 دردشة بسام الذكي</h1>
  <div id="log" class="scroll"></div>
  <div class="row">
    <input id="msg" placeholder="اكتب سؤالك..." style="flex:1"/>
    <select id="tone">
      <option value="">نبرة تلقائية</option>
      <option value="friendly">ودية</option>
      <option value="supportive">داعمة</option>
      <option value="calm">هادئة</option>
      <option value="excited">متحمسة</option>
    </select>
    <button id="speakBtn" title="نطق آخر رد">🔊</button>
    <button id="micBtn" class="mic" title="تفعيل الصوت">🎙️</button>
    <button id="send" title="إرسال الرسالة">📤</button>
  </div>
</div>

<script>
const log=document.getElementById('log');
const msg=document.getElementById('msg');
const tone=document.getElementById('tone');
const send=document.getElementById('send');
const micBtn=document.getElementById('micBtn');
const speakBtn=document.getElementById('speakBtn');

function add(type,text){
  const d=document.createElement('div');
  d.className='msg '+type; d.textContent=text;
  log.appendChild(d); log.scrollTop=log.scrollHeight;
}
async function callAPI(m){ 
  const payload={message:m, tone: tone.value||null};
  const r=await fetch('/api/chat',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(payload)});
  const j=await r.json(); 
  return j.reply;
}

send.onclick=async ()=>{
  const m=msg.value.trim(); 
  if(!m) return;
  add('user',m); msg.value='';
  add('bot','...جاري التفكير والتعلّم 🔄');
  const reply=await callAPI(m);
  log.lastChild.textContent=reply;
  speak(reply);
};
msg.addEventListener('keydown',e=>{ if(e.key==='Enter'){send.click()} });

function speak(text){
  if(!('speechSynthesis' in window)) return;
  const u=new SpeechSynthesisUtterance(text);
  u.lang='ar';
  speechSynthesis.speak(u);
}
speakBtn.onclick=()=>{
  const last=[...document.querySelectorAll('.msg.bot')].pop();
  if(last) speak(last.textContent);
};

let rec;
micBtn.onclick=()=>{
  if(!('webkitSpeechRecognition' in window)){
    alert('❌ المتصفح لا يدعم التعرف الصوتي'); return;
  }
  if(rec){ rec.stop(); rec=null; micBtn.textContent='🎙️'; return; }
  rec=new webkitSpeechRecognition(); rec.lang='ar';
  rec.onresult=(e)=>{
    msg.value=e.results[0][0].transcript; send.click();
  };
  rec.onend=()=>{ micBtn.textContent='🎙️'; rec=null; };
  micBtn.textContent='⏹️'; rec.start();
};
</script>
"""
    return HTMLResponse(html)

@router.post("/api/chat")
async def api_chat(payload: ChatIn):
    """واجهة دردشة ذكية + تعليم تلقائي بالحوار"""
    user_msg = (payload.message or "").strip()
    tn = payload.tone or analyze_tone(user_msg)

    reply = answer(user_msg, tn)

    # الجديد: علّم النواة من الحوار (يدوّن الاستفسار + الرد)
    enqueue_dialog(user_msg, reply, tn)

    return JSONResponse({"reply": reply, "learned": True})
