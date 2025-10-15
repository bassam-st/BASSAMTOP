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
