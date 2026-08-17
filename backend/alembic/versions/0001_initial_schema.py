"""baseline schema for production PostgreSQL

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-17
"""

from alembic import op

from app.db.database import Base
from app.models.ai_analysis_history import AIAnalysisHistory
from app.models.alert import Alert
from app.models.broker_connection import BrokerConnection
from app.models.holding import Holding
from app.models.transaction import Transaction
from app.models.user import User
from app.models.watchlist import Watchlist
from app.models.paper_trade import PaperTrade

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
