from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.paper_ml_model import PaperMlModel


def test_ml_model_defaults_are_safe():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=[PaperMlModel.__table__])
    with Session(engine) as db:
        model = PaperMlModel(
            user_id=1, strategy_version="V1", version="ML_V1",
            algorithm="LOGISTIC_REGRESSION", feature_names_json="[]",
            model_json="{}", metrics_json="{}", training_samples=0,
        )
        db.add(model)
        db.commit()
        assert model.validated is False
        assert model.active is False
