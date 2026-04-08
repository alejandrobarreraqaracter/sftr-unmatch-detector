"""
Test configuration and fixtures for SFTR Unmatch Detector.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test_sftr.db"

from app.main import app
from app.database import Base, get_db


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    engine = create_engine("sqlite:///./test_sftr.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with a fresh database."""
    engine = db_session.get_bind()
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_csv_path():
    """Path to the sample CSV file."""
    return os.path.join(
        os.path.dirname(__file__), "..", "sample_data", "sftr_reconciliation_sample.csv"
    )


@pytest.fixture
def sample_csv_bytes(sample_csv_path):
    """Raw bytes of the sample CSV file."""
    with open(sample_csv_path, "rb") as f:
        return f.read()


@pytest.fixture
def minimal_csv_bytes():
    """Minimal CSV with 1 row and a few fields for fast unit tests."""
    header = "UTI;SFT_Type;Action_Type;Reporting timestamp_CP1;Reporting timestamp_CP2;Report submitting entity_CP1;Report submitting entity_CP2;Principal amount on value date_CP1;Principal amount on value date_CP2"
    row = "UTI001;Repo;NEWT;2024-03-15T09:32:00Z;2024-03-15T09:32:00Z;R0MUWSFPU8MPRO8K5P83;R0MUWSFPU8MPRO8K5P83;5000000.00;4950000.00"
    return f"{header}\n{row}".encode("utf-8")
