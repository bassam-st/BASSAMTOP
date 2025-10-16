import json, os, time, uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

PERSIST_DIR = Path(os.environ.get("PERSIST_DIR", "./data")).resolve()
DOCS_DIR = PERSIST_DIR / "docs"
SUM_DIR = PERSIST_DIR / "summaries"
STATE_FILE = PERSIST_DIR / "state.json"
QUEUE_FILE = PERSIST_DIR / "queue.json"

for d in (DOCS_DIR, SUM_DIR):
    d.mkdir(parents=True, exist_ok=True)
PERSIST_DIR.mkdir(parents=True, exist_ok=True)

def _read_json(p: Path, default):
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def _write_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def get_state() -> Dict[str, Any]:
    st = _read_json(STATE_FILE, {})
    st.setdefault("active", False)
    st.setdefault("last_run", None)
    st.setdefault("runs", 0)
    st.setdefault("last_query", None)
    return st

def set_state(**kwargs):
    st = get_state()
    st.update(kwargs)
    _write_json(STATE_FILE, st)
    return st

def enqueue_query(q: str):
    q = (q or "").strip()
    if not q:
        return
    Q = _read_json(QUEUE_FILE, [])
    Q.append({"id": str(uuid.uuid4()), "q": q, "ts": int(time.time())})
    _write_json(QUEUE_FILE, Q)

def dequeue_query() -> Optional[str]:
    Q = _read_json(QUEUE_FILE, [])
    if not Q:
        return None
    item = Q.pop(0)
    _write_json(QUEUE_FILE, Q)
    return item.get("q")

def save_doc(url: str, title: str, content: str) -> str:
    doc_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    path = DOCS_DIR / f"{doc_id}.json"
    _write_json(path, {"id": doc_id, "url": url, "title": title, "content": content})
    return doc_id

def save_summary(query: str, items: List[Dict[str, Any]], combined: str) -> str:
    sum_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    path = SUM_DIR / f"{sum_id}.json"
    _write_json(path, {
        "id": sum_id,
        "query": query,
        "items": items,
        "summary": combined,
        "ts": int(time.time()),
    })
    return sum_id

def recent_summaries(n: int = 10) -> List[Dict[str, Any]]:
    files = sorted(SUM_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in files[:n]:
        out.append(_read_json(p, {}))
    return out
