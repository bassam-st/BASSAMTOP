set -euo pipefail
APPDIR="bassam-core/app"

# 1) ملف الذاكرة: SQLite + تلخيص
mkdir -p "$APPDIR"
cat > "$APPDIR/memory.py" <<'PY'
import sqlite3, os, time, textwrap
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "core.db")
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "data"), exist_ok=True)

def _conn():
    return sqlite3.connect(DB_PATH)

def init_memory():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session TEXT, role TEXT, content TEXT,
            ts REAL
        )""")
        c.execute("""CREATE INDEX IF NOT EXISTS idx_session_ts ON messages(session, ts)""")

def save_message(session: str, role: str, content: str):
    with _conn() as c:
        c.execute("INSERT INTO messages(session, role, content, ts) VALUES(?,?,?,?)",
                  (session, role, content, time.time()))

def get_recent(session: str, limit: int = 12):
    with _conn() as c:
        cur = c.execute("SELECT role, content FROM messages WHERE session=? ORDER BY ts DESC LIMIT ?",
                        (session, limit))
        rows = cur.fetchall()[::-1]
    return rows

def summarize_history(session: str, keep:int=8):
    """يلخّص القديم عندما تكبر الجلسة لتبقى خفيفة"""
    with _conn() as c:
        cur = c.execute("SELECT id, role, content FROM messages WHERE session=? ORDER BY ts ASC", (session,))
        rows = cur.fetchall()
        if len(rows) <= keep:
            return
        old = rows[:-keep]
        text = "\n".join([f"{r}: {t}" for _, r, t in old])
        # تلخيص بسيط محلّي (يمكن لاحقًا استبداله باستدعاء نموذج خارجي إذا أردت)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        brief = textwrap.shorten(" | ".join(lines), width=800, placeholder=" ...")
        # امسح القديم واستبدله بسطر مُلخّص
        ids = tuple([i for i,_,_ in old])
        q = "DELETE FROM messages WHERE id IN ({})".format(",".join("?"*len(ids)))
        c.execute(q, ids)
        c.execute("INSERT INTO messages(session, role, content, ts) VALUES(?,?,?,?)",
                  (session, "summary", f"[ملخّص سابق]: {brief}", time.time()))
PY

# 2) تهيئة الجدول (مرة واحدة)
python3 - <<'PY'
from app.memory import init_memory
init_memory()
print("✅ memory table ready")
PY

# 3) ترقيع مسارات الدردشة لربط الذاكرة
ROUTES="$APPDIR/routes/chat_routes.py"
if [ ! -f "$ROUTES" ]; then
  echo "❌ لم أجد $ROUTES — تأكد أن إضافة واجهة الدردشة تمت."
  exit 1
fi

# أضف import للذاكرة إن لم يوجد
grep -q "from app.memory import" "$ROUTES" 2>/dev/null || \
sed -i '1i from app.memory import save_message, get_recent, summarize_history' "$ROUTES"

# أدخل session_id (من كويك بارام أو هيدر) واحفظ التاريخ قبل/بعد الرد
python3 - <<'PY'
from pathlib import Path
p = Path("bassam-core/app/routes/chat_routes.py")
txt = p.read_text(encoding="utf-8")

# اجعل دالة api_chat تستخدم الذاكرة
if "def api_chat" in txt and "save_message(" not in txt:
    txt = txt.replace(
        "@router.post(\"/api/chat\")",
        "@router.post(\"/api/chat\")"
    )
    # حقن منطق الذاكرة داخل api_chat
    txt = txt.replace(
        "async def api_chat(payload: ChatIn):",
        "async def api_chat(payload: ChatIn, request=None):"
    )
    inject = '''
    # 🔸 session: من بارام ?s= أو هيدر X-Session أو "default"
    session = "default"
    try:
        from fastapi import Request
        if request:
            if hasattr(request, "query_params") and request.query_params.get("s"):
                session = request.query_params.get("s")
            elif hasattr(request, "headers") and request.headers.get("X-Session"):
                session = request.headers.get("X-Session")
    except Exception:
        pass

    # احضر آخر المحادثات كـسياق
    history = get_recent(session, limit=12)
    ctx_lines = [f"{r}: {c}" for r,c in history]
    context = "\\n".join(ctx_lines).strip()

    # خزّن رسالة المستخدم
    save_message(session, "user", payload.message)
'''
    txt = txt.replace(
        "reply = answer(payload.message, payload.tone)",
        inject + "\n    reply = answer(payload.message, payload.tone, context=context)"
    )
    # خزّن ردّ المساعد وخصّص التلخيص
    txt = txt.replace(
        "return JSONResponse({\"reply\": reply})",
        "    save_message(session, \"assistant\", reply)\n    summarize_history(session)\n    return JSONResponse({\"reply\": reply, \"session\": session})"
    )

p.write_text(txt, encoding="utf-8")
print("✅ chat_routes patched for memory")
PY

# 4) تعديل دالة answer لدعم context (إن لم تدعمه)
ANS="bassam-core/app/answer.py"
if [ -f "$ANS" ]; then
python3 - <<'PY'
from pathlib import Path, re
p = Path("bassam-core/app/answer.py")
t = p.read_text(encoding="utf-8")

# إذا الدالة answer لا تحتوي بارام context أضفه
if "def answer(" in t and "context:" not in t.split("def answer(")[1].split("):")[0]:
    t = t.replace("def answer(query: str, tone: str", "def answer(query: str, tone: str, context: str = \"\"")
    # مرر السياق لمحرك البحث/التلخيص إذا كان موجودًا، وإلا اضفه إلى النص النهائي كـhint
    if "def deep_search" in t:
        t = t.replace("def deep_search(", "def deep_search(")  # مجرد لمسة لضمان عدم تغيّر
        # لا نعرف داخله؛ لذا نضيف تلميحًا قبل التلخيص النهائي
    if "final_text =" in t:
        t = t.replace("final_text =", "final_text = (f\"[السياق]\\n{context}\\n---\\n\" if context else \"\") + (")
        t = t.replace("return final_text", "return final_text")
    else:
        # fallback: أضف إدراج للسياق قبل الإرجاع إن لم نجد final_text
        t = t.replace("return summary", "return ((\"[السياق]\\n\"+context+\"\\n---\\n\") if context else \"\") + summary")
    print("✅ answer() now accepts context")
p.write_text(t, encoding="utf-8")
PY
fi

echo "✅ Memory added and wired to chat."
