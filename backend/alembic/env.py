from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.database import Base, DATABASE_URL
from app.models.ai_analysis_history import AIAnalysisHistory
from app.models.alert import Alert
from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.models.paper_historical_run import PaperHistoricalRun
from app.models.paper_market_state import PaperMarketState
from app.models.paper_validation_day import PaperValidationDay
from app.models.paper_validation_symbol import PaperValidationSymbol
from app.models.paper_validation_manifest import PaperValidationManifest
from app.models.paper_trade_learning import PaperTradeLearningEvent
from app.models.paper_ml_model import PaperMlModel
from app.models.paper_ml_deployment import PaperMlDeployment
from app.models.paper_ml_prediction import PaperMlPrediction
from app.models.transaction import Transaction
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.research_experiment import ResearchExperiment
from app.models.corporate_action import CorporateAction

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=DATABASE_URL, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
