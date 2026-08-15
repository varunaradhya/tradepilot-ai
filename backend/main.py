from app.api.v1.signals import router as signals_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.advanced_analytics import router as advanced_analytics_router
from app.api.v1.reconciliation import router as reconciliation_router
from app.api.v1.trading_general import router as trading_general_router
from app.api.v1.algo import router as algo_router
from app.api.v1.market_risk import router as market_risk_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
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
from app.db.database import engine
from app.core.config import TRADEPILOT_CORS_ORIGINS

app = FastAPI(title="TradePilot AI", description="AI-powered stock portfolio tracking and analysis platform", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=TRADEPILOT_CORS_ORIGINS, allow_credentials=False, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["*"])
for router in [users_router, auth_router, portfolio_router, valuation_router, transactions_router, analytics_router, watchlist_router, brokers_router, market_router]: app.include_router(router, prefix="/api/v1")
for router in [reconciliation_router, advanced_analytics_router, signals_router, intelligence_router, alerts_router, trading_general_router, algo_router, market_risk_router]: app.include_router(router, prefix="/api/v1")

@app.on_event("startup")
def startup_event(): init_db()
@app.get("/")
def root(): return {"message": "TradePilot AI API is running", "version": "0.1.0"}
@app.get("/health")
def health_check(): return {"status": "healthy"}
@app.get("/ready", tags=["Operations"], summary="Check critical dependency readiness")
def readiness_check():
    try:
        with engine.connect() as connection: connection.execute(text("SELECT 1"))
    except Exception: return {"status": "not_ready", "database": "unavailable"}
    return {"status": "ok", "database": "available"}
