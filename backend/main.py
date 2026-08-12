from fastapi import FastAPI

from app.api.v1.users import router as users_router
from app.db.init_db import init_db

app = FastAPI(
    title="TradePilot AI",
    description="AI-powered stock portfolio tracking and analysis platform",
    version="0.1.0",
)

app.include_router(users_router, prefix="/api/v1")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/")
def root():
    return {
        "message": "TradePilot AI API is running",
        "version": "0.1.0",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
