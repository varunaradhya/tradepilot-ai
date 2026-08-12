import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.models.user import User
from main import app


@pytest.fixture
def client(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    test_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client, test_session_local
    app.dependency_overrides.clear()
    test_engine.dispose()


def test_get_users_returns_empty_list_when_database_is_empty(client):
    test_client, _ = client

    response = test_client.get("/api/v1/users/")

    assert response.status_code == 200
    assert response.json() == []


def test_get_users_returns_existing_users_without_security_fields(client):
    test_client, test_session_local = client
    db = test_session_local()
    db.add(
        User(
            full_name="Varun Aradhya",
            email="varun@example.com",
            password_hash="temporary-test-hash",
        )
    )
    db.commit()
    db.close()

    response = test_client.get("/api/v1/users/")

    assert response.status_code == 200
    users = response.json()
    assert len(users) == 1
    assert users[0]["full_name"] == "Varun Aradhya"
    assert users[0]["email"] == "varun@example.com"
    assert "password_hash" not in users[0]
    assert "password" not in users[0]
