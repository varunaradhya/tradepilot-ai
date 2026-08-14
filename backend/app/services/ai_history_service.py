from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.ai_analysis_history import AIAnalysisHistory


def get_cached_analysis(db: Session, user_id: int, analysis_type: str, symbol: str | None, ttl_seconds: int) -> AIAnalysisHistory | None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    return db.query(AIAnalysisHistory).filter(AIAnalysisHistory.user_id == user_id, AIAnalysisHistory.analysis_type == analysis_type, AIAnalysisHistory.symbol == symbol, AIAnalysisHistory.context_version == "v1", AIAnalysisHistory.generated_at >= cutoff).order_by(AIAnalysisHistory.generated_at.desc()).first()


def store_analysis(db: Session, user_id: int, analysis_type: str, symbol: str | None, provider: str, analysis: dict) -> AIAnalysisHistory:
    item = AIAnalysisHistory(user_id=user_id, analysis_type=analysis_type, symbol=symbol, provider=provider, signal=analysis["signal"], confidence=int(analysis["confidence"]), summary=analysis["summary"], generated_at=analysis["generated_at"])
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_history(db: Session, user_id: int, analysis_type: str | None, symbol: str | None, limit: int) -> list[AIAnalysisHistory]:
    query = db.query(AIAnalysisHistory).filter(AIAnalysisHistory.user_id == user_id)
    if analysis_type:
        query = query.filter(AIAnalysisHistory.analysis_type == analysis_type)
    if symbol:
        query = query.filter(AIAnalysisHistory.symbol == symbol.upper())
    return query.order_by(AIAnalysisHistory.generated_at.desc()).limit(limit).all()
