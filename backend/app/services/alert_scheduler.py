from sqlalchemy.orm import Session

from app.ai.analyst_service import analyze_portfolio
from app.ai.trading_intelligence import scan_opportunities
from app.services.alert_service import evaluate_alerts


def evaluate_user_alerts(db: Session, user_id: int):
    """Manual/worker-safe deterministic alert entry point; it never trades or calls an LLM."""
    return evaluate_alerts(db, user_id, analyze_portfolio(db, user_id), scan_opportunities(db, user_id))
