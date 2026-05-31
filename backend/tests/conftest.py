import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+pysqlite:////tmp/clarifi_test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["ENABLE_PGVECTOR"] = "false"

from fastapi.testclient import TestClient
import pytest

from app.db.session import engine
from app.models.finance import Base
from main import app


@pytest.fixture(autouse=True)
def clean_db():
    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    test_db = Path("/tmp/clarifi_test.db")
    if test_db.exists():
        test_db.unlink()


@pytest.fixture
def client():
    return TestClient(app)
