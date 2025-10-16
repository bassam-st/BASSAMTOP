from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal

from workers.core_worker import (
    enqueue_task, query_index, get_status, get_latest_results,
    run_cycle_once, do_search, learn_from_query
)

# تشفير/فك تشفير (اختياري)
try:
    from ..utils.crypto import encrypt_json, decrypt_json
except Exception:
    def encrypt_json(x): return x
    def decrypt_json(x): return x

# DB (للاحتياط)
try:
    from .db import get_recent_docs
except Exception:
    def get_recent_docs(limit: int = 10): return get_latest_results(limit)

router = APIRouter()

# ===== نماذج الإدخال =====
class SearchRequest(BaseModel):
    q: str
    source: Optional[Literal["auto", "google", "ddg", "both"]] = "auto"
    learn: Optional[bool] = False  # لو True يَحفظ النتائج في قاعدة المعرفة

class LearnRunIn(BaseModel):
    topics: Optional[List[str]] = None   # إن تركتها فارغة يستخدم TOPICS من البيئة

# ===== البحث الفوري (مع خيار التعلّم) =====
@router.post("/search")
async def search(req: SearchRequest):
    q = (req.q or "").strip()
    if not q:
        raise HTTPException(400, "q is empty")

    # بحث فوري (Google أولاً إذا مفاتيحه موجودة، ثم DDG تلقائياً)
    results = do_search(q, source=req.source or "auto", max_results=8)

    learned = 0
    learned_sample = []
    if req.learn:
        lr = learn_from_query(q, source=req.source)
        learned = lr.get("learned", 0)
        learned_sample = lr.get("docs", [])

    return {
        "status": "ok",
        "query": q,
        "provider": req.source or "auto",
        "results": results,
        "learned": learned,
        "learned_sample": learned_sample
    }

# ===== صفّ المهام (لمن يريد الإرسال المؤجّل) =====
@router.get("/status")
async def status():
    return {"queue": query_index()}

# ===== آخر ما تعلّمه النظام =====
@router.get("/news")
async def news():
    return {"docs": get_recent_docs()}

# ===== تجربة تشفير/فك تشفير (اختياري) =====
@router.post("/secure")
async def secure_echo(body: dict):
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}

# ===== تشغيل دورة تعلّم يدوياً =====
@router.post("/learn/run")
async def learn_run(payload: LearnRunIn | None = None):
    topics = payload.topics if payload else None
    res = run_cycle_once(topics)
    return {"ok": True, **res}

# ===== حالة المجدول =====
@router.get("/learn/state")
async def learn_state():
    return get_status()

# ===== أحدث النتائج من المستودع =====
@router.get("/learn/latest")
async def learn_latest(limit: int = 10):
    return {"docs": get_latest_results(limit=limit)}
