import sqlite3, os, json

DB_PATH = os.path.join(os.path.dirname(__file__), "docs.sqlite")

def ensure_tables():
    """يتأكد من وجود جدول docs"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        url TEXT,
        summary TEXT,
        meta TEXT,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def add_doc(title, url, summary, meta=None):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO docs (title, url, summary, meta) VALUES (?, ?, ?, ?)",
        (title, url, summary, json.dumps(meta or {}))
    )
    conn.commit()
    conn.close()

def get_recent_docs(limit: int = 10):
    ensure_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, title, url, summary, meta, ts FROM docs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    docs = []
    for r in rows:
        docs.append({
            "id": r[0],
            "title": r[1],
            "url": r[2],
            "summary": r[3],
            "meta": json.loads(r[4] or "{}"),
            "ts": r[5],
        })
    return list(reversed(docs))
