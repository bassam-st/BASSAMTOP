from fastapi import APIRouter, Request, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional

from .storage import get_state, set_state, recent_summaries, enqueue_query
from workers.run_cycle import run_once  # يستخدم نفس الدالة

templates = Jinja2Templates(directory="bassam_core/templates")
router = APIRouter()

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

@router.get("/")
def index(request: Request):
    st = get_state()
    recents = recent_summaries(6)
    return templates.TemplateResponse("index.html", {"request": request, "state": st, "recents": recents})
