"""
Pytest configuration and test fixtures.
Sets up an in-memory SQLite database, overrides dependencies, and provides auth fixtures.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest, CentreTest
from app.core.security import get_password_hash

# Use in-memory SQLite database for test isolation
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Create a standard patient user."""
    user = User(
        email="patient@test.com",
        full_name="Test Patient",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def other_user(db_session):
    """Create a secondary patient user for authorization testing."""
    user = User(
        email="other@test.com",
        full_name="Other Patient",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_staff=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def staff_user(db_session):
    """Create a staff/admin user."""
    user = User(
        email="admin@test.com",
        full_name="Admin Staff",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_staff=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_headers(client, test_user):
    """Obtain Bearer token headers for standard test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "patient@test.com", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_headers(client, other_user):
    """Obtain Bearer token headers for secondary test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "other@test.com", "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def staff_headers(client, staff_user):
    """Obtain Bearer token headers for staff user."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_catalogue(db_session):
    """Seed sample diagnostic centre, test, and pricing mapping."""
    test = DiagnosticTest(
        code="CBC",
        name="Complete Blood Count",
        description="Comprehensive blood screening",
    )
    centre = DiagnosticCentre(
        name="Apollo Diagnostic Lab",
        location="Indiranagar, Bangalore",
        contact_phone="+91 80 1234 5678",
        is_active=True,
    )
    db_session.add_all([test, centre])
    db_session.flush()

    centre_test = CentreTest(
        centre_id=centre.id,
        test_id=test.id,
        price=Decimal("450.00"),
        is_available=True,
    )
    db_session.add(centre_test)
    db_session.commit()

    return {
        "centre": centre,
        "test": test,
        "centre_test": centre_test,
        "price": Decimal("450.00"),
    }
