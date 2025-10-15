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
if __name__ == "__main__":
    import os
    import sqlite3

    data_dir = "bassam-core/data"
    os.makedirs(data_dir, exist_ok=True)

    db_path = os.path.join(data_dir, "memory.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # إنشاء جدول لتخزين الذاكرة
    c.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            content TEXT,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print(f"✅ memory.db created successfully at {db_path}")