from app.models.paper_ml_model import PaperMlModel


def test_ml_model_defaults_are_safe():
    model = PaperMlModel(
        user_id=1, strategy_version="V1", version="ML_V1",
        algorithm="LOGISTIC_REGRESSION", feature_names_json="[]",
        model_json="{}", metrics_json="{}", training_samples=0,
    )
    assert model.validated is False
    assert model.active is False
