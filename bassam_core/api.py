from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# استيراد الأدوات الداخلية
from .storage import get_state, set_state, recent_summaries, enqueue_query
from workers.run_cycle import run_once

templates = Jinja2Templates(directory="bassam_core/templates")
router = APIRouter()


# ============================================================
# نماذج
# ============================================================

class ChatRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    query: str
    engine: Optional[str] = "auto"


class NewsRequest(BaseModel):
    query: str
    engine: Optional[str] = "auto"
    mode: Optional[str] = "search_and_learn"


class LearnRequest(BaseModel):
    text: str


class CustomsRequest(BaseModel):
    description: str
    weight: Optional[float] = 0
    value: Optional[float] = 0


# ============================================================
# مسارات الحالة والطابور
# ============================================================

@router.get("/state")
def api_state():
    return get_state()


@router.post("/queue")
def api_queue(q: str):
    enqueue_query(q)
    return {"ok": True, "queued": q}


@router.post("/learn/once")
def api_learn_once(q: Optional[str] = None):
    info = run_once(q or None)
    return {"ok": True, **info}


# ============================================================
# 1) /api/chat
# ============================================================

@router.post("/chat")
async def api_chat(payload: ChatRequest):
    query = payload.query.strip()

    if not query:
        return {"ok": False, "error": "النص فارغ"}

    # نموذج بسيط للرد — يمكن استبداله بـ Agent حقيقي لاحقاً
    reply = f"تم استلام رسالتك: {query}"
    return {"ok": True, "answer": reply}


# ============================================================
# 2) /api/search
# ============================================================

@router.post("/search")
async def api_search(payload: SearchRequest):
    query = payload.query.strip()

    if not query:
        return {"ok": False, "error": "الاستعلام فارغ"}

    # بحث تجريبي — تطوير لاحقاً
    result = f"نتيجة البحث عن '{query}' باستخدام المحرك: {payload.engine}"

    return {
        "ok": True,
        "query": query,
        "engine": payload.engine,
        "result": result
    }


# ============================================================
# 3) /api/news
# ============================================================

@router.post("/news")
async def api_news(payload: NewsRequest):
    query = payload.query.strip()
    engine = payload.engine
    mode = payload.mode

    if not query:
        return {"ok": False, "error": "الاستعلام فارغ"}

    # --- بحث فقط بدون تعلم ---
    if mode == "search_only":
        enqueue_query(query)
        return {
            "ok": True,
            "mode": mode,
            "result": f"تم وضع '{query}' في الطابور بدون تشغيل دورة التعلم."
        }

    # --- بحث + تلخيص + تعلم (فوري) ---
    info = run_once(query)

    return {
        "ok": True,
        "mode": mode,
        "engine": engine,
        "result": info.get("summary") if isinstance(info, dict) else str(info),
        "raw": info
    }


# ============================================================
# 4) /api/learn
# ============================================================

@router.post("/learn")
async def api_learn(payload: LearnRequest):
    text = payload.text.strip()

    if not text:
        return {"ok": False, "error": "النص فارغ"}

    # إضافة النص للطابور ليتم تعلمه
    enqueue_query(text)

    return {"ok": True, "stored": text}


# ============================================================
# 5) /api/customs
# ============================================================

@router.post("/customs")
async def api_customs(payload: CustomsRequest):
    desc = payload.description
    weight = payload.weight or 0
    value = payload.value or 0

    # نموذج بسيط — سيتم استبداله بـ Agent جمارك ذكي
    duties = value * 0.05  # مثال: 5% رسوم
    tariff = "غير محدد (سيتم تطوير Custom Agent)"

    return {
        "ok": True,
        "description": desc,
        "weight": weight,
        "value": value,
        "tariff": tariff,
        "duties": duties
    }


# ============================================================
# الصفحة الرئيسية
# ============================================================

@router.get("/")
def index(request: Request):
    st = get_state()
    recents = recent_summaries(6)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": st, "recents": recents},
    )
