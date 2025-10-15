# bassam_core/app/main.py

from fastapi import FastAPI

# ملاحظة: نستخدم واردات نسبية لأننا نشغّل Uvicorn مع --app-dir bassam_core
from .api import router as api_router                 # /api/* endpoints
from .routes import root as root_routes               # صفحات/مسارات عامة (إن وُجدت)
from .chat_routes import router as chat_router        # مسارات الدردشة (إن وُجدت)

# وظائف الخلفية/الجدولة
from ..workers.scheduler import AutoIndexer           # جدولة فهرسة تلقائية
from ..workers.news_worker import SCHEDULER           # جدولة أخبار (إن وُجدت)

app = FastAPI(title="Bassam Core (Light)")

# ربط الراوترات
app.include_router(api_router, prefix="/api")
app.include_router(root_routes.router)
app.include_router(chat_router)

# مبدّل الفهرسة التلقائي كل 15 دقيقة ويبدأ فوراً عند التشغيل
auto_indexer = AutoIndexer(interval_minutes=15, run_immediately=True)

@app.on_event("startup")
async def on_startup():
    # تشغيل أي جداول وظائف عند الإقلاع
    try:
        auto_indexer.start()
    except Exception as e:
        print("Failed to start AutoIndexer:", e)

    try:
        # إن كان الـ SCHEDULER يحتاج start() ففعّله
        if hasattr(SCHEDULER, "start"):
            SCHEDULER.start()
    except Exception as e:
        print("Failed to start news SCHEDULER:", e)

@app.on_event("shutdown")
async def on_shutdown():
    # إيقاف الجداول عند الإغلاق
    try:
        auto_indexer.shutdown()
    except Exception as e:
        print("Failed to shutdown AutoIndexer:", e)

    try:
        if hasattr(SCHEDULER, "shutdown"):
            SCHEDULER.shutdown()
    except Exception as e:
        print("Failed to shutdown news SCHEDULER:", e)


# نقطة فحص بسيطة للصحة
@app.get("/health")
async def health():
    return {"status": "ok"}
