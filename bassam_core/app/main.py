# bassam_core/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router
from workers.core_worker import start_scheduler

# ✅ إنشاء تطبيق FastAPI الرئيسي
app = FastAPI(
    title="Bassam Core AI",
    description="النواة الذكية لتطبيق بسام — بحث وتعلم تلقائي وجدولة خلفية",
    version="2.0.0"
)

# ✅ السماح بالوصول من أي نطاق (للواجهة أو تطبيقات أخرى)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ تسجيل الراوتر الرئيسي
app.include_router(api_router, prefix="/api", tags=["Bassam Core API"])

# ✅ بدء المجدول الآمن (التعلم الذاتي الدوري)
@app.on_event("startup")
async def startup_event():
    """يبدأ المجدول فور تشغيل السيرفر"""
    start_scheduler()
    print("✅ Scheduler started successfully")

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "🔥 Bassam Core is running and learning automatically 🔁",
        "api_endpoints": ["/api/search", "/api/status", "/api/news", "/api/secure"]
    }
