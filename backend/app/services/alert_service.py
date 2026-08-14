import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import TRADEPILOT_ALERT_COOLDOWN_SECONDS
from app.models.alert import Alert


def create_alert(db: Session, user_id: int, type_: str, severity: str, title: str, message: str, symbol: str | None = None, metadata: dict | None = None) -> Alert | None:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=TRADEPILOT_ALERT_COOLDOWN_SECONDS)
    existing = db.query(Alert).filter(Alert.user_id == user_id, Alert.type == type_, Alert.symbol == symbol, Alert.created_at >= cutoff).first()
    if existing:
        return None
    alert = Alert(user_id=user_id, type=type_, severity=severity, symbol=symbol, title=title, message=message, metadata_json=json.dumps(metadata) if metadata else None)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def evaluate_alerts(db: Session, user_id: int, portfolio: dict, opportunities: dict) -> list[Alert]:
    created = []
    concentration = portfolio["context_summary"]["portfolio"]["concentration_percent"]
    if concentration > 50:
        item = create_alert(db, user_id, "CONCENTRATION", "HIGH", "Portfolio concentration is elevated", f"Your largest holding represents {concentration:.1f}% of tracked portfolio value.", metadata={"concentration_percent": concentration})
        if item: created.append(item)
    for candidate in opportunities["opportunities"][:3]:
        if candidate["signal"] == "BUY" and candidate["score"] >= 70:
            item = create_alert(db, user_id, "OPPORTUNITY", "INFO", f"Potential setup: {candidate['symbol']}", f"Deterministic opportunity score is {candidate['score']} with a BUY signal.", candidate["symbol"], {"score": candidate["score"]})
            if item: created.append(item)
        if candidate["signal"] == "SELL":
            item = create_alert(db, user_id, "SIGNAL_CHANGE", "WARNING", f"Attention: {candidate['symbol']}", "Deterministic technical signal is SELL; review the associated risk.", candidate["symbol"])
            if item: created.append(item)
    return created


def list_alerts(db: Session, user_id: int) -> list[Alert]:
    return db.query(Alert).filter(Alert.user_id == user_id).order_by(Alert.is_read.asc(), Alert.created_at.desc()).all()


def mark_read(db: Session, user_id: int, alert_id: int) -> Alert | None:
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()
    if alert:
        alert.is_read = True
        db.commit()
        db.refresh(alert)
    return alert


def mark_all_read(db: Session, user_id: int) -> int:
    count = db.query(Alert).filter(Alert.user_id == user_id, Alert.is_read.is_(False)).update({Alert.is_read: True}, synchronize_session=False)
    db.commit()
    return count
