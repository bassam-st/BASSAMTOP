from fastapi import FastAPI
from app.api import router as api_router
from workers.scheduler import AutoIndexer

app = FastAPI(title="Bassam Core (Light)")
app.include_router(api_router, prefix="/api")

# مجدول: 15 دقيقة + تشغيل الجولة الأولى فورياً
auto_indexer = AutoIndexer(interval_minutes=15, run_immediately=True)

@app.on_event("startup")
async def startup_event():
    try:
        auto_indexer.start()
    except Exception as e:
        print("Failed to start AutoIndexer:", e)

@app.on_event("shutdown")
async def shutdown_event():
    try:
        auto_indexer.shutdown()
    except Exception as e:
        print("Failed to shutdown AutoIndexer:", e)

from app.routes import root as root_routes
app.include_router(root_routes.router)

from .chat_routes import router as chat_router
app.include_router(chat_router)

from workers.news_worker import SCHEDULER
