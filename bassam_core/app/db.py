# bassam_core/app/db.py
import sqlite3, os, json, time
from typing import List, Dict

DB_PATH = os.getenv("DB_PATH", "/tmp/bassam_core.db")

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS docs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, url TEXT, summary TEXT, source TEXT,
        meta TEXT, ts INTEGER
    )""")
    return c

def save_docs(docs: List[Dict]):
    if not docs: return
    c = _conn()
    now = int(time.time())
    for d in docs:
        c.execute("INSERT INTO docs(title,url,summary,source,meta,ts) VALUES (?,?,?,?,?,?)",
                  (d.get("title"), d.get("url"), d.get("summary"),
                   d.get("source"), json.dumps(d, ensure_ascii=False), now))
    c.commit(); c.close()

def get_recent_docs(limit: int = 10):
    c = _conn()
    cur = c.execute("SELECT id,title,url,summary,source,ts FROM docs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall(); c.close()
    out = []
    for r in rows:
        out.append({"id": r[0], "title": r[1], "url": r[2], "summary": r[3], "source": r[4], "ts": r[5]})
    return out

def get_latest_results(limit: int = 10):
    return get_recent_docs(limit)
