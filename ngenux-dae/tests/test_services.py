"""
Unit tests for the DecisionEngine service.
Tests cover all policy branches: approve, reject (score), reject (income),
reject (both), unsupported type, and the execution metadata shape.
"""

import pytest
from app.services import DecisionEngine


@pytest.fixture()
def engine() -> DecisionEngine:
    return DecisionEngine()


# ---------------------------------------------------------------------------
# LOAN_APPROVAL – policy v1.0
# ---------------------------------------------------------------------------

class TestLoanApprovalV1:
    POLICY = "v1.0"

    def test_approved_when_all_criteria_met(self, engine):
        status, result, explanation, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 750, "income": 50000}
        )
        assert status == "APPROVED"
        assert "loan_amount" in result
        assert "interest_rate" in result
        assert explanation["details"]["credit_score_met"] is True
        assert explanation["details"]["income_met"] is True

    def test_rejected_when_credit_score_too_low(self, engine):
        status, result, explanation, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 600, "income": 50000}
        )
        assert status == "REJECTED"
        assert result == {}
        rejections = explanation["details"]["rejections"]
        assert any("credit score" in r.lower() for r in rejections)

    def test_rejected_when_income_too_low(self, engine):
        status, result, explanation, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 750, "income": 30000}
        )
        assert status == "REJECTED"
        rejections = explanation["details"]["rejections"]
        assert any("income" in r.lower() for r in rejections)

    def test_rejected_when_both_criteria_fail(self, engine):
        status, result, explanation, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 500, "income": 20000}
        )
        assert status == "REJECTED"
        rejections = explanation["details"]["rejections"]
        assert len(rejections) == 2

    def test_approved_at_exact_threshold(self, engine):
        """Boundary: exactly at the minimum values should still APPROVE."""
        status, *_ = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 700, "income": 40000}
        )
        assert status == "APPROVED"

    def test_loan_amount_is_half_of_income(self, engine):
        _, result, *_ = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 750, "income": 80000}
        )
        assert result["loan_amount"] == 40000.0


# ---------------------------------------------------------------------------
# LOAN_APPROVAL – default / unknown policy version
# ---------------------------------------------------------------------------

class TestLoanApprovalDefaultPolicy:
    POLICY = "v99.0"  # falls back to stricter defaults

    def test_stricter_thresholds_apply(self, engine):
        # Would pass v1.0 but fail the stricter default (720 / 50000)
        status, *_ = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 710, "income": 45000}
        )
        assert status == "REJECTED"

    def test_passes_stricter_thresholds(self, engine):
        status, *_ = engine.evaluate_decision(
            "LOAN_APPROVAL", self.POLICY, {"credit_score": 720, "income": 50000}
        )
        assert status == "APPROVED"


# ---------------------------------------------------------------------------
# Unsupported decision type
# ---------------------------------------------------------------------------

class TestUnsupportedDecisionType:
    def test_returns_rejected_for_unknown_type(self, engine):
        status, result, explanation, metadata = engine.evaluate_decision(
            "UNKNOWN_POLICY", "v1.0", {}
        )
        assert status == "REJECTED"
        assert "error" in explanation

    def test_cost_is_zero_for_unknown_type(self, engine):
        *_, metadata = engine.evaluate_decision("UNKNOWN_POLICY", "v1.0", {})
        assert metadata["cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# Execution metadata shape
# ---------------------------------------------------------------------------

class TestExecutionMetadata:
    def test_metadata_has_latency_and_cost(self, engine):
        *_, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", "v1.0", {"credit_score": 750, "income": 50000}
        )
        assert "latency_ms" in metadata
        assert "cost_usd" in metadata

    def test_latency_is_positive_number(self, engine):
        *_, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", "v1.0", {"credit_score": 750, "income": 50000}
        )
        assert metadata["latency_ms"] >= 0

    def test_cost_is_nonzero_for_valid_decision(self, engine):
        *_, metadata = engine.evaluate_decision(
            "LOAN_APPROVAL", "v1.0", {"credit_score": 750, "income": 50000}
        )
        assert metadata["cost_usd"] > 0
