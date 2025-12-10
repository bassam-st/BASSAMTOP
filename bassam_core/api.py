from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .storage import get_state, set_state, recent_summaries, enqueue_query
from workers.run_cycle import run_once  # يستخدم نفس الدالة

templates = Jinja2Templates(directory="bassam_core/templates")
router = APIRouter()


# --------- نماذج الطلبات (لـ /api/news) ---------
class NewsRequest(BaseModel):
    query: str
    engine: Optional[str] = "auto"
    mode: Optional[str] = "search_and_learn"


# --------- API بسيطة للحالة والطابور ---------
@router.get("/state")
def api_state():
    return get_state()


@router.post("/queue")
def api_queue(q: str):
    enqueue_query(q)
    return {"ok": True, "queued": q}


@router.post("/learn/once")
def api_learn_once(q: Optional[str] = None):
    """
    هذا المسار القديم ما زال موجوداً لو حبيت تستخدمه يدوياً،
    لكنه الآن ليس ضرورياً للواجهة.
    """
    info = run_once(q or None)
    return {"ok": True, **info}


# --------- المسار الجديد الذي تستخدمه الواجهة ---------
@router.post("/news")
async def api_news(payload: NewsRequest):
    """
    هذا هو المسار الذي تناديه الواجهة من index.html:
    - يستقبل query و engine و mode
    - حسب mode يقرر:
        * search_only          -> يضيف للطابور فقط
        * search_and_learn     -> يشغّل دورة run_once
        * quick_search_and_learn -> نفس السابق لكن نعلّم أنه سريع
    """
    q = (payload.query or "").strip()
    if not q:
        return JSONResponse(
            {"ok": False, "error": "الاستعلام فارغ"},
            status_code=400,
        )

    mode = payload.mode or "search_and_learn"

    # 1) بحث فقط بدون تشغيل الدورة الآن (مثلاً يخليها للـ worker)
    if mode == "search_only":
        enqueue_query(q)
        return {
            "ok": True,
            "mode": mode,
            "queued": True,
            "message": "تم إضافة الطلب إلى الطابور فقط بدون تشغيل الدورة الآن.",
        }

    # 2) بحث + تلخيص + تعلّم (فوري)
    # نستخدم run_once الموجودة أصلاً في workers.run_cycle
    info = run_once(q or None)

    # نضيف بعض المعلومات الإضافية للواجهة
    response = {
        "ok": True,
        "mode": mode,
        "engine": payload.engine,
    }

    # info هي dict نرجعها كما هي بالإضافة للحقول السابقة
    if isinstance(info, dict):
        response.update(info)
    else:
        # لو رجعت شيء غير dict نحوله لنص
        response["result"] = str(info)

    return response


# --------- صفحة الواجهة ---------
@router.get("/")
def index(request: Request):
    st = get_state()
    recents = recent_summaries(6)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "state": st, "recents": recents},
    )
