from fastapi import FastAPI

from app.db.init_db import init_db

app = FastAPI(
    title="TradePilot AI",
    description="AI-powered stock portfolio tracking and analysis platform",
    version="0.1.0",
)


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