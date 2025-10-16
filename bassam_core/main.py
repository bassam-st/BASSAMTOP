from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from .api import router as api_router

app = FastAPI(title="Bassam Core", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(api_router, prefix="/api", tags=["API"])

@app.get("/")
def root():
    # يعاد توجيه الجذر إلى صفحة الواجهة
    return {"message": "Bassam Core is running. Visit /api/ or use /api/ endpoints."}
