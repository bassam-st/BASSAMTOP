#!/usr/bin/env bash
set -e

# Simple light setup script for Bassam-Core (RAG + chatbot stub)
# Usage: paste this into Replit shell at ~/workspace$ and run

ROOT="$PWD"
APPDIR="$ROOT/bassam-core"
mkdir -p "$APPDIR/app" "$APPDIR/scripts" "$APPDIR/keys"

echo "Creating files..."

# 1) requirements
cat > "$APPDIR/requirements.txt" <<'PYREQ'
uvicorn[standard]
fastapi
openai
beautifulsoup4
readability-lxml
ddgs
python-dotenv
cryptography
sqlalchemy
pydantic
PYREQ

# 2) app/main.py
cat > "$APPDIR/app/main.py" <<'PYMAIN'
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
app = FastAPI(title="Bassam-Core")

# simple home page
@app.get("/", response_class=HTMLResponse)
def home():
    html = """
    <html>
      <head><meta charset="utf-8"/><title>Bassam-Core Online</title></head>
      <body style="background:#0b0f19;color:#fff;font-family:Tahoma,Arial,sans-serif;text-align:center;margin-top:10%">
        <h1>✅ Bassam-Core Online</h1>
        <p>API: <code>/api/chat</code></p>
        <p>Use POST /api/chat with JSON { "query": "..." }</p>
      </body>
    </html>
    """
    return html

# try to include routes if present
try:
    from app.routes import root as root_routes
    app.include_router(root_routes)
except Exception:
    pass

# include chatbot router if available
try:
    from app.chatbot import router as chat_router
    app.include_router(chat_router, prefix="/api")
except Exception:
    pass
PYMAIN

# 3) app/chatbot.py
cat > "$APPDIR/app/chatbot.py" <<'PYCHAT'
from fastapi import APIRouter, Body
import os, time
router = APIRouter()

# try to import openai (optional)
try:
    import openai
except Exception:
    openai = None

from typing import List, Dict
# try import query_index from app.index if exists
def query_index(query, k=5):
    try:
        from app.index import query_index as _q
        return _q(query, k=k)
    except Exception:
        return []

def summarize_text(text, max_chars=1000):
    if not text:
        return ""
    t = " ".join(text.split())
    return t[:max_chars] + ("..." if len(t) > max_chars else "")

def build_rag_prompt(query, docs):
    header = "You are an expert assistant. Use the provided documents to answer precisely and cite sources.\n\n"
    docs_text = ""
    for i,d in enumerate(docs):
        title = d.get("meta",{}).get("title") or f"doc{i+1}"
        snippet = (d.get("text") or d.get("snippet") or "")[:2000]
        docs_text += f"--- doc {i+1}: {title}\n{snippet}\n\n"
    prompt = f"{header}QUESTION: {query}\n\nDOCUMENTS:\n{docs_text}\n\nProvide a clear step-by-step answer, include code blocks if needed, and cite document numbers."
    return prompt

def call_openai(prompt, max_tokens=512):
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAIKEY")
    if not api_key or openai is None:
        return None
    openai.api_key = api_key
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You are an expert assistant."},
                      {"role":"user","content":prompt}],
            max_tokens=max_tokens,
            temperature=0.1
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[OpenAI error: {e}]"

@router.post("/chat")
async def chat(query: str = Body(..., embed=True), k:int = Body(5), history: List[Dict]=Body(default=[])):
    docs_raw = query_index(query, k=k)
    docs = []
    for r in docs_raw:
        if isinstance(r, (list,tuple)) and len(r)>=2:
            docs.append({"text": r[0], "meta": r[1]})
        elif isinstance(r, dict):
            docs.append(r)
    prompt = build_rag_prompt(query, docs)
    # try OpenAI
    answer = None
    if openai is not None and (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAIKEY")):
        answer = call_openai(prompt, max_tokens=700)
    if not answer:
        combined = "\n\n".join([d.get("text","") for d in docs]) or "No docs found."
        answer = "[Local summary]\\n" + summarize_text(combined, max_chars=1500)
    return {"query": query, "answer": answer, "sources":[d.get("meta",{}) for d in docs], "timestamp": time.time()}
