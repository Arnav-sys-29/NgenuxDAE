"""
Integration tests for FastAPI endpoints.
Uses an in-memory SQLite database so no live PostgreSQL is needed.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import get_db
from app.models import Base

# ---------------------------------------------------------------------------
# Test database setup – isolated SQLite per test session
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///./test_ngenux.db"

test_engine = create_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests run, drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    """Provide a TestClient with the DB override applied."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _loan_payload(credit_score: int = 750, income: int = 50000, policy: str = "v1.0") -> dict:
    return {
        "request_info": {"request_id": "REQ-TEST-001", "decision_type": "LOAN_APPROVAL"},
        "actor_info": {"actor_id": "test_agent", "role": "system"},
        "policy_reference": {"policy_version": policy},
        "context_facts": {"facts": {"credit_score": credit_score, "income": income}},
    }


# ---------------------------------------------------------------------------
# POST /decisions
# ---------------------------------------------------------------------------

class TestCreateDecision:
    def test_approved_decision_returns_200(self, client):
        resp = client.post("/decisions", json=_loan_payload(750, 50000))
        assert resp.status_code == 200

    def test_approved_decision_has_correct_status(self, client):
        resp = client.post("/decisions", json=_loan_payload(750, 50000))
        assert resp.json()["status"] == "APPROVED"

    def test_rejected_decision_has_correct_status(self, client):
        resp = client.post("/decisions", json=_loan_payload(500, 20000))
        assert resp.json()["status"] == "REJECTED"

    def test_response_contains_explanation(self, client):
        resp = client.post("/decisions", json=_loan_payload(750, 50000))
        body = resp.json()
        assert "explanation" in body
        assert "reason" in body["explanation"]

    def test_response_contains_execution_metadata(self, client):
        resp = client.post("/decisions", json=_loan_payload(750, 50000))
        body = resp.json()
        assert "execution_metadata" in body
        assert "latency_ms" in body["execution_metadata"]
        assert "cost_usd" in body["execution_metadata"]

    def test_response_has_decision_id(self, client):
        resp = client.post("/decisions", json=_loan_payload())
        assert "decision_id" in resp.json()


# ---------------------------------------------------------------------------
# GET /decisions
# ---------------------------------------------------------------------------

class TestListDecisions:
    def test_list_returns_200(self, client):
        resp = client.get("/decisions")
        assert resp.status_code == 200

    def test_list_is_a_list(self, client):
        resp = client.get("/decisions")
        assert isinstance(resp.json(), list)

    def test_created_decision_appears_in_list(self, client):
        create_resp = client.post("/decisions", json=_loan_payload())
        decision_id = create_resp.json()["decision_id"]

        list_resp = client.get("/decisions")
        ids = [d["decision_id"] for d in list_resp.json()]
        assert decision_id in ids


# ---------------------------------------------------------------------------
# GET /decisions/{decision_id}
# ---------------------------------------------------------------------------

class TestGetDecisionDetail:
    def test_detail_returns_200_for_valid_id(self, client):
        create_resp = client.post("/decisions", json=_loan_payload())
        decision_id = create_resp.json()["decision_id"]

        resp = client.get(f"/decisions/{decision_id}")
        assert resp.status_code == 200

    def test_detail_returns_404_for_unknown_id(self, client):
        resp = client.get("/decisions/nonexistent-id-xyz")
        assert resp.status_code == 404

    def test_detail_contains_audit_logs(self, client):
        create_resp = client.post("/decisions", json=_loan_payload())
        decision_id = create_resp.json()["decision_id"]

        detail = client.get(f"/decisions/{decision_id}").json()
        assert len(detail["audit_logs"]) >= 2  # CREATED + EVALUATION_COMPLETED

    def test_detail_explanation_and_metadata_present(self, client):
        create_resp = client.post("/decisions", json=_loan_payload())
        decision_id = create_resp.json()["decision_id"]

        detail = client.get(f"/decisions/{decision_id}").json()
        assert "explanation" in detail
        assert "execution_metadata" in detail
