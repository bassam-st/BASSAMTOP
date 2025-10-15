from fastapi import FastAPI
from . import api
from workers.core_worker import CORE_WORKER, SCHEDULER

app = FastAPI(title="BassamCore - Nucleus")

app.include_router(api.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    # شغّل الـscheduler (سيشغل الجولة الأولى فوراً لو run_immediately=True)
    SCHEDULER.start()

@app.on_event("shutdown")
async def shutdown_event():
    SCHEDULER.shutdown()
