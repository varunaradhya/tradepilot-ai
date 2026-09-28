from app.models.user import User
from app.models.transaction import Transaction
from app.models.watchlist import Watchlist
from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.models.ai_analysis_history import AIAnalysisHistory
from app.models.alert import Alert
from app.models.paper_trade import PaperTrade
from app.models.strategy_paper_authorization import StrategyPaperAuthorization
from app.models.paper_signal_request import PaperSignalRequest
from app.models.paper_session_state import PaperSessionState
from app.models.paper_historical_run import PaperHistoricalRun
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.models.paper_ml_model import PaperMlModel
from app.models.paper_ml_deployment import PaperMlDeployment
from app.models.paper_ml_prediction import PaperMlPrediction
from app.models.operational_kill_switch import OperationalKillSwitch
from app.models.operational_audit_event import OperationalAuditEvent

from app.db.database import Base, engine
from app.core.config import TRADEPILOT_AUTO_CREATE_SCHEMA


def init_db():
    if TRADEPILOT_AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)
