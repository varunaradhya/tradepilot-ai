from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.analyst_service import analyze_portfolio
from app.ai.trading_intelligence import scan_opportunities
from app.services.alert_service import evaluate_alerts


def build_daily_briefing(db: Session, user_id: int) -> dict:
    portfolio = analyze_portfolio(db, user_id)
    opportunities = scan_opportunities(db, user_id)
    evaluate_alerts(db, user_id, portfolio, opportunities)
    metrics = portfolio["context_summary"]["portfolio"]
    analysis = portfolio["analysis"]
    return {"headline": analysis["summary"], "portfolio_summary": f"Current value {metrics['current_value']:.2f}; total P&L {metrics['total_pnl']:.2f}; return {metrics['return_percent']:.2f}%.", "risk_summary": metrics["risk_summary"], "top_opportunities": opportunities["opportunities"][:3], "top_risks": analysis["risks"], "watch_items": analysis["watch_items"], "generated_at": datetime.now(timezone.utc)}
