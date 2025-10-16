# bassam_core/app/api.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

# ✅ استيراد العامل الصحيح من المسار الجديد
from workers.core_worker import enqueue_query, query_index, get_status, get_latest_results

# ✅ استيراد أدوات التشفير (في حال كانت موجودة)
from ..utils.crypto import encrypt_json, decrypt_json

# ✅ استيراد قاعدة البيانات (إن وجدت داخل app/db.py)
from .db import get_recent_docs

# إنشاء الراوتر
router = APIRouter()

# نموذج طلب البحث
class SearchRequest(BaseModel):
    q: str

# 🔹 إضافة استعلام جديد لقائمة المهام
@router.post("/search")
async def search(req: SearchRequest, background: BackgroundTasks):
    if not req.q.strip():
        raise HTTPException(status_code=400, detail="q is empty")
    background.add_task(enqueue_query, req.q.strip())
    return {"status": "accepted", "message": "queued", "query": req.q}

# 🔹 عرض قائمة المهام الحالية
@router.get("/status")
async def status():
    return get_status()

# 🔹 جلب أحدث النتائج أو الأخبار المخزنة
@router.get("/news")
async def news():
    docs = get_latest_results()
    if not docs:
        docs = get_recent_docs() or {}
    return {"docs": docs}

# 🔹 تشفير/فك تشفير JSON للتجارب
@router.post("/secure")
async def secure_echo(body: dict):
    """
    تجربة تشفير/فك تشفير JSON
    """
    token = encrypt_json(body)
    data = decrypt_json(token)
    return {"encrypted": token, "decrypted": data}
