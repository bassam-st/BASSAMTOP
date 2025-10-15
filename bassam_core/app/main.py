from fastapi import FastAPI
from workers.core_worker import SCHEDULER
from .api import router as api_router
from .chat_routes import router as chat_router

app = FastAPI(title="Bassam Core (Nucleus)")

# شغّل النواة عند الإقلاع
@app.on_event("startup")
async def startup_event():
    try:
        SCHEDULER.start()
    except Exception as e:
        print("Scheduler start error:", e)

# أوقف النواة عند الإطفاء
@app.on_event("shutdown")
async def shutdown_event():
    try:
        SCHEDULER.shutdown()
    except Exception as e:
        print("Scheduler shutdown error:", e)

# نقاط الـ API
app.include_router(api_router, prefix="/api")
app.include_router(chat_router)
