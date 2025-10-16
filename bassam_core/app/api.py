# bassam_core/app/api.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# عامل التشغيل والمجدول
from workers.core_worker import (
    enqueue_task, query_index, get_status, get_latest_results, run_cycle_once
)

# تشفير/فك تشفير (اختياري إن كان لديك utils/crypto.py)
try:
    from ..utils.crypto import encrypt_json, decrypt_json
except Exception:
    def encrypt_json(x): return x
    def decrypt_json(x): return x

# دوال من db داخل نفس مجلّد app (إن وُجدت)
try:
    from .db import get_recent_docs
except Exception:
    def get_recent_docs(limit: int = 10): return get_latest_results(limit)

router = APIRouter()

# ===== نماذج الإدخال =====
class SearchRequest(BaseModel):
    q: str

class LearnRunIn(BaseModel):
    topics: Optional[List[str]] = None   # إن تركتها فارغة يستخدم TOPICS الافتراضية

# ===== المسارات الأساسية =====
@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    if not req.q.strip():
        raise HTTPException(400, "q is empty")
    background.add_task(enqueue_task, req.q.strip())
    return {"status": "accepted", "message": "queued", "query": req.q}

@router.get("/status")
async def status():
    return {"queue": query_index()}

@router.get("/news")
async def news():
    return {"docs": get_recent_docs()}

@router.post("/secure")
async def secure_echo(body: dict):
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}

# ===== مسارات التحكم بالتعلّم الذاتي =====
@router.post("/learn/run")
async def learn_run(payload: LearnRunIn | None = None):
    topics = payload.topics if payload else None
    res = run_cycle_once(topics)
    return {"ok": True, **res}

@router.get("/learn/state")
async def learn_state():
    return get_status()

@router.get("/learn/latest")
async def learn_latest(limit: int = 10):
    return {"docs": get_latest_results(limit=limit)}
