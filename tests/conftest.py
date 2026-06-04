import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from lifeostomanyagent.config import settings
from lifeostomanyagent.server.db.models import Base
from lifeostomanyagent.server.deps import get_service
from lifeostomanyagent.server.main import app
from lifeostomanyagent.server.services import LifeOSService


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    data_root = tmp_path / "data"
    monkeypatch.setattr(settings, "lifeos_data_root", data_root)
    monkeypatch.setattr(settings, "redis_url", None)
    monkeypatch.setattr(settings, "lifeos_intent_classifier", "rules")
    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "worlds").mkdir(parents=True, exist_ok=True)

    import lifeostomanyagent.server.db.models as db_models

    monkeypatch.setattr(db_models, "engine", engine)
    monkeypatch.setattr(db_models, "SessionLocal", testing_session)

    def get_service_override():
        db = testing_session()
        try:
            yield LifeOSService(db)
        finally:
            db.close()

    app.dependency_overrides[get_service] = get_service_override

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
