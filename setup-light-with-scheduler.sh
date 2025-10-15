#!/usr/bin/env bash
set -e

# ----------------------------
# setup-light-with-scheduler.sh
# نسخة خفيفة مع مجدول (يحترم robots.txt ويعمل جولة أولى فور البدء)
# لصقه مرة واحدة في Shell داخل Replit (في جذر workspace).
# ----------------------------

# تنظيف نسخة قديمة
rm -rf bassam-core
mkdir -p bassam-core/{app,workers,utils,keys,scripts}

# requirements خفيفة
cat > bassam-core/requirements.txt <<'REQEOF'
fastapi
uvicorn[standard]
requests
beautifulsoup4
duckduckgo_search
readability-lxml
python-dotenv
tqdm
sqlalchemy
cryptography
scikit-learn
numpy
scipy
apscheduler
python-dotenv
REQEOF

# .env.example
cat > bassam-core/.env.example <<'ENVEOF'
FERNET_KEY=
RSA_PRIVATE_PATH=keys/rsa_private.pem
RSA_PUBLIC_PATH=keys/rsa_public.pem
DB_PATH=bassam.db
PORT=3000
HOST=0.0.0.0
ENVEOF

# README صغير
cat > bassam-core/README.md <<'REMEOF'
Bassam-Core (LIGHT + Scheduler)
تشغيل مؤقت (Replit):
  1) قم بتعيين FERNET_KEY في Secrets بعد توليده.
  2) source venv/bin/activate
  3) uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir .
المجدول يقوم بجولات بحث كل 15 دقيقة. الجولة الأولى تعمل فور البدء.
REMEOF

# scripts/generate_keys.py
cat > bassam-core/scripts/generate_keys.py <<'PY'
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

OUT_DIR = "keys"
os.makedirs(OUT_DIR, exist_ok=True)

def gen_fernet_key():
    key = Fernet.generate_key()
    path = os.path.join(OUT_DIR, "fernet.key")
    with open(path, "wb") as f:
        f.write(key)
    print("FERNET_KEY (base64) saved to:", path)
    print(key.decode())

def gen_rsa_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(os.path.join(OUT_DIR, "rsa_private.pem"), "wb") as f:
        f.write(priv_pem)
    with open(os.path.join(OUT_DIR, "rsa_public.pem"), "wb") as f:
        f.write(pub_pem)
    print("RSA keys saved to:", OUT_DIR)

if __name__ == "__main__":
    gen_fernet_key()
    gen_rsa_keys()
    print("Done. انسخ قيمة FERNET_KEY وأضفها إلى Secrets في Replit أو إلى .env")
PY
# scripts/init_db.py
cat > bassam-core/scripts/init_db.py <<'PY'
from app.db import init_db
if __name__ == "__main__":
    init_db()
    print("DB initialized.")
PY

# app/main.py
cat > bassam-core/app/main.py <<'PY'
from fastapi import FastAPI
from app.api import router as api_router
from workers.scheduler import AutoIndexer

app = FastAPI(title="Bassam Core (Light)")
app.include_router(api_router, prefix="/api")

# مجدول: 15 دقيقة + تشغيل الجولة الأولى فورياً
auto_indexer = AutoIndexer(interval_minutes=15, run_immediately=True)

@app.on_event("startup")
async def startup_event():
    try:
        auto_indexer.start()
    except Exception as e:
        print("Failed to start AutoIndexer:", e)

@app.on_event("shutdown")
async def shutdown_event():
    try:
        auto_indexer.shutdown()
    except Exception as e:
        print("Failed to shutdown AutoIndexer:", e)
PY

# app/api.py
cat > bassam-core/app/api.py <<'PY'
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from workers.news_worker import enqueue_query, query_index
from app.db import get_recent_docs
from utils.crypto import encrypt_json, decrypt_json

router = APIRouter()

class SearchRequest(BaseModel):
    q: str

@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    background.add_task(enqueue_query, req.q)
    return {"status":"accepted","message":"query enqueued","query":req.q}

@router.get("/status")
def status():
    return {"status":"ok"}

@router.get("/docs/recent")
def recent_docs():
    docs = get_recent_docs(limit=10)
    return {"count": len(docs), "docs": docs}

@router.post("/encrypt")
def api_encrypt(payload: dict):
    token = encrypt_json(payload)
    return {"token": token}

@router.post("/decrypt")
def api_decrypt(body: dict):
    token = body.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    data = decrypt_json(token)
    return {"data": data}

@router.post("/query_index")
def api_query_index(body: dict):
    q = body.get("q")
    if not q:
        raise HTTPException(status_code=400, detail="q required")
    results = query_index(q, k=5)
    return {"query": q, "results": results}
PY

# app/db.py
cat > bassam-core/app/db.py <<'PY'
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
PY

# utils/safe_fetch.py
cat > bassam-core/utils/safe_fetch.py <<'PY'
import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse
import time
import urllib.robotparser

HEADERS = {"User-Agent": "BassamCoreBot/1.0 (+https://example.local)"}
RATE_SLEEP = 5  # وقت انتظار بين طلبات نفس الموقع (ثوان)

_cache_robots = {}

def allowed_by_robots(url):
    try:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in _cache_robots:
            rp = _cache_robots[base]
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(base + "/robots.txt")
            try:
                rp.read()
            except:
                pass
            _cache_robots[base] = rp
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return False

def fetch_page_text(url, timeout=10):
    try:
        if not allowed_by_robots(url):
            return None
        time.sleep(RATE_SLEEP)
        r = requests.get(url, timeout=timeout, headers=HEADERS)
        r.raise_for_status()
        doc = Document(r.text)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "html.parser")
        text = soup.get_text(separator="\\n")
        return text
    except Exception:
        return None
PY

# utils/crypto.py
cat > bassam-core/utils/crypto.py <<'PY'
import os, json
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from dotenv import load_dotenv
load_dotenv()
FERNET_KEY = os.getenv("FERNET_KEY")
RSA_PRIVATE_PATH = os.getenv("RSA_PRIVATE_PATH", "keys/rsa_private.pem")
RSA_PUBLIC_PATH  = os.getenv("RSA_PUBLIC_PATH",  "keys/rsa_public.pem")
def _get_fernet():
    global FERNET_KEY
    if not FERNET_KEY:
        try:
            with open("keys/fernet.key","rb") as f:
                FERNET_KEY = f.read().strip().decode()
        except:
            raise RuntimeError("FERNET_KEY not set. Run scripts/generate_keys.py and set FERNET_KEY.")
    key = FERNET_KEY.encode() if isinstance(FERNET_KEY, str) else FERNET_KEY
    return Fernet(key)
def encrypt_json(obj: dict) -> str:
    f = _get_fernet()
    raw = json.dumps(obj, ensure_ascii=False).encode()
    token = f.encrypt(raw)
    return token.decode()
def decrypt_json(token: str) -> dict:
    f = _get_fernet()
    try:
        raw = f.decrypt(token.encode())
        return json.loads(raw.decode())
    except InvalidToken as e:
        raise RuntimeError("Invalid token or wrong key.") from e
PY
# workers/news_worker.py
cat > bassam-core/workers/news_worker.py <<'PY'
import os, time, json
from duckduckgo_search import DDGS
from utils.safe_fetch import fetch_page_text
from utils.crypto import encrypt_json
from app.db import save_doc
from dotenv import load_dotenv
load_dotenv()

def summarize(text, max_chars=800):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    joined = " ".join(lines)
    return joined[:max_chars] + ("..." if len(joined) > max_chars else "")

def enqueue_query(q):
    print("🔍 Running deep search for:", q)
    docs = []
    with DDGS() as ddgs:
        for r in ddgs.text(q, region='wt-wt', safesearch='moderate', max_results=5):
            url = r.get("href")
            title = r.get("title")
            if not url: continue
            text = fetch_page_text(url)
            if not text: continue
            snippet = summarize(text)
            meta = {"title": title, "url": url, "summary": snippet}
            save_doc(meta)
            docs.append(meta)
    print("✅ Saved", len(docs), "docs")

def query_index(q, k=5):
    print("query_index placeholder:", q)
    return [{"title": f"result {i}", "score": 1.0 - i*0.1} for i in range(k)]
PY

# workers/scheduler.py
cat > bassam-core/workers/scheduler.py <<'PY'
import threading, time
from workers.news_worker import enqueue_query

class AutoIndexer:
    def __init__(self, interval_minutes=15, run_immediately=True):
        self.interval = interval_minutes * 60
        self.run_immediately = run_immediately
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
    def start(self):
        print(f"🕒 Scheduler started, every {self.interval/60} min")
        self.thread.start()
    def _loop(self):
        if self.run_immediately:
            enqueue_query("latest AI programming frameworks")
        while not self._stop_event.is_set():
            time.sleep(self.interval)
            enqueue_query("AI + programming + networking + systems")
    def shutdown(self):
        print("🛑 Scheduler stopped")
        self._stop_event.set()
PY

# setup virtualenv + init db automatically
echo "🔧 Preparing Bassam-Core light environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r bassam-core/requirements.txt
export PYTHONPATH=$PWD/bassam-core
python3 bassam-core/scripts/generate_keys.py || true
python3 bassam-core/scripts/init_db.py || true
echo "✅ Setup complete. Run using:"
echo "uvicorn app.main:app --host 0.0.0.0 --port \$PORT --app-dir bassam-core"
