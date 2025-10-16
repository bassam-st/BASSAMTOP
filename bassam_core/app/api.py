# bassam_core/app/api.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# ✅ الاستيراد الصحيح من العامل
from workers.core_worker import enqueue_task, query_index, get_status, get_latest_results

# (اختياري) تشفير/فك تشفير إن كنت تستخدم utils/crypto.py
try:
    from ..utils.crypto import encrypt_json, decrypt_json
except Exception:
    def encrypt_json(x): return x
    def decrypt_json(x): return x

# (اختياري) جلب آخر المستندات من db داخل نفس مجلد app
try:
    from .db import get_recent_docs
except Exception:
    def get_recent_docs(): return []

router = APIRouter()

class SearchRequest(BaseModel):
    q: str

@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    if not req.q.strip():
        raise HTTPException(400, "q is empty")
    # ✅ نضيف المهمة إلى قائمة العمل بالخلفية
    background.add_task(enqueue_task, req.q.strip())
    return {"status": "accepted", "message": "queued", "query": req.q}

@router.get("/status")
async def status():
    return {"queue": query_index(), "worker": get_status()}

@router.get("/news")
async def news():
    return {"docs": get_recent_docs()}

@router.post("/secure")
async def secure_echo(body: dict):
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}
