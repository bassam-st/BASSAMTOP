from fastapi import APIRouter, HTTPException
from typing import List
from workers.core_worker import enqueue_task, query_index, get_status, get_latest_results

router = APIRouter()

@router.post("/learn")
async def post_learn(q: str):
    """أضف استعلام لتتعلمه النواة"""
    enqueue_task(q)
    return {"status":"accepted","q": q}

@router.get("/queries", response_model=List[str])
async def list_queries():
    return query_index()

@router.get("/status")
async def status():
    return get_status()

@router.get("/results")
async def results():
    return get_latest_results()
