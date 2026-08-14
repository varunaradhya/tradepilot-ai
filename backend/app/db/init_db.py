from app.models.user import User
from app.models.transaction import Transaction
from app.models.watchlist import Watchlist
from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.models.ai_analysis_history import AIAnalysisHistory
from app.models.alert import Alert

from app.db.database import Base, engine
from app.core.config import TRADEPILOT_AUTO_CREATE_SCHEMA


def init_db():
    if TRADEPILOT_AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)
