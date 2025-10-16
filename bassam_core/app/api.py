# bassam_core/app/api.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# نستخدم العامل (worker) للتعلّم والبحث
from workers.core_worker import (
    enqueue_task,
    query_index,
    get_status,
    get_latest_results,
    run_cycle_once,
    learn_from_query,  # دالة في العامل تقوم بالبحث والتلخيص
)

# تشفير اختياري
try:
    from ..utils.crypto import encrypt_json, decrypt_json
except Exception:
    def encrypt_json(x): return x
    def decrypt_json(x): return x

router = APIRouter()

# ===== نماذج =====
class SearchRequest(BaseModel):
    q: str

class LearnRunIn(BaseModel):
    topics: Optional[List[str]] = None

# ===== المسارات الأساسية =====
@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    q = (req.q or "").strip()
    if not q:
        raise HTTPException(400, "q is empty")
    background.add_task(enqueue_task, q)
    return {"status": "accepted", "message": "queued", "query": q}

@router.get("/status")
async def status():
    return {"queue": query_index()}

@router.get("/news")
async def news(limit: int = 10):
    return {"docs": get_latest_results(limit=limit)}

@router.post("/secure")
async def secure_echo(body: dict):
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}

# ===== التحكم بالتعلّم الذاتي =====
@router.post("/learn/run")
async def learn_run(payload: Optional[LearnRunIn] = None):
    topics = payload.topics if payload else None
    res = run_cycle_once(topics)
    return {"ok": True, **res}

@router.get("/learn/state")
async def learn_state():
    return get_status()

@router.get("/learn/latest")
async def learn_latest(limit: int = 10):
    return {"docs": get_latest_results(limit=limit)}

# ===== تعلّم فوري لسؤال واحد =====
@router.post("/learn/fast")
async def learn_fast(
    q: str = Query(..., description="سؤال أو موضوع للتعلّم الفوري"),
    source: str = Query("auto", description="auto | google | ddg | both")
) -> Dict[str, Any]:
    q = (q or "").strip()
    if not q:
        raise HTTPException(400, "q is empty")
    out = learn_from_query(q, source=source)
    return {"ok": True, "query": q, **out}
