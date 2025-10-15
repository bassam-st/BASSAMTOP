import sqlite3, json, os
from dotenv import load_dotenv
load_dotenv()
DB = os.getenv("DB_PATH", "bassam.db")

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        summary TEXT,
        meta TEXT,
        ts DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

def save_doc(meta: dict):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO docs (title,url,summary,meta) VALUES (?,?,?,?)",
              (meta.get("title"), meta.get("url"), meta.get("summary"), json.dumps(meta)))
    conn.commit()
    conn.close()

def get_recent_docs(limit=20):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, title, url, summary, meta, ts FROM docs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    out = []
    for r in rows:
        try:
            meta = json.loads(r[4]) if r[4] else {}
        except:
            meta = {}
        out.append({"id": r[0], "title": r[1], "url": r[2], "summary": r[3], "meta": meta, "ts": r[5]})
    return out
