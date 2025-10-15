from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from workers.core_worker import enqueue_query, query_index
from ..utils.crypto import encrypt_json, decrypt_json
from ..app.db import get_recent_docs

router = APIRouter()

class SearchRequest(BaseModel):
    q: str

@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    if not req.q.strip():
        raise HTTPException(400, "q is empty")
    background.add_task(enqueue_query, req.q.strip())
    return {"status": "accepted", "message": "queued", "query": req.q}

@router.get("/status")
async def status():
    return {"queue": query_index()}

@router.get("/news")
async def news():
    docs = get_recent_docs()
    return {"docs": docs}

@router.post("/secure")
async def secure_echo(body: dict):
    """تجربة تشفير/فك تشفير JSON"""
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}
