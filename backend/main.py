from app.api.v1.signals import router as signals_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.advanced_analytics import router as advanced_analytics_router
from app.api.v1.reconciliation import router as reconciliation_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.valuation import router as valuation_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.watchlist import router as watchlist_router
from app.api.v1.brokers import router as brokers_router
from app.api.v1.users import router as users_router
from app.api.v1.market import router as market_router
from app.db.init_db import init_db


app = FastAPI(
    title="TradePilot AI",
    description="AI-powered stock portfolio tracking and analysis platform",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(
    users_router,
    prefix="/api/v1",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)
app.include_router(
    portfolio_router,
    prefix="/api/v1",
)
app.include_router(
    valuation_router,
    prefix="/api/v1",
)
app.include_router(
    transactions_router,
    prefix="/api/v1",
)
app.include_router(
    analytics_router,
    prefix="/api/v1",
)
app.include_router(
    watchlist_router,
    prefix="/api/v1",
)
app.include_router(
    brokers_router,
    prefix="/api/v1",
)
app.include_router(
    market_router,
    prefix="/api/v1",
)
app.include_router(reconciliation_router, prefix="/api/v1")
app.include_router(advanced_analytics_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")

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
        "status": "healthy",
    }
