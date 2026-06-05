import time
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session


class DecisionEngine:
    def __init__(self):
        # Maps decision_type to its evaluation handler
        self._handlers = {
            "LOAN_APPROVAL": self._evaluate_loan_approval
        }

    def evaluate_decision(
        self,
        decision_type: str,
        policy_version: str,
        facts: Dict[str, Any],
        db: Optional[Session] = None
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        """
        Evaluates a decision. If a db session is provided, loads rules from the
        Policy Store. Falls back to hardcoded defaults otherwise.
        Returns (status, output_result, explanation, execution_metadata).
        """
        start_time = time.perf_counter()
        handler = self._handlers.get(decision_type)

        if not handler:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return "REJECTED", {}, {
                "error": f"Unsupported decision_type: {decision_type}",
                "reason": "No policy logic implemented for this decision type."
            }, {"latency_ms": round(latency_ms, 2), "cost_usd": 0.0}

        # Load rules from DB if available
        db_rules = self._load_rules_from_db(db, decision_type, policy_version) if db else None

        try:
            status, output_result, explanation = handler(policy_version, facts, db_rules)
            latency_ms = (time.perf_counter() - start_time) * 1000
            metadata = {
                "latency_ms": round(latency_ms, 2),
                "cost_usd": 0.001,
                "rules_source": "database" if db_rules else "hardcoded"
            }
            return status, output_result, explanation, metadata
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return "ERROR", {}, {
                "error": str(e),
                "reason": "An unexpected error occurred during evaluation."
            }, {"latency_ms": round(latency_ms, 2), "cost_usd": 0.0}

    def _load_rules_from_db(
        self, db: Session, decision_type: str, version_tag: str
    ) -> Optional[Dict[str, Any]]:
        """Look up the policy rules JSON from the policy_versions table."""
        try:
            from app import models
            policy = db.query(models.Policy).filter(
                models.Policy.decision_type == decision_type,
                models.Policy.is_active == True
            ).first()
            if not policy:
                return None

            version = db.query(models.PolicyVersion).filter(
                models.PolicyVersion.policy_id == policy.policy_id,
                models.PolicyVersion.version_tag == version_tag,
                models.PolicyVersion.is_active == True
            ).first()
            return version.rules if version else None
        except Exception:
            return None

    def _evaluate_loan_approval(
        self,
        policy_version: str,
        facts: Dict[str, Any],
        db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Policy logic for LOAN_APPROVAL — prefers DB rules, falls back to hardcoded."""
        credit_score = facts.get("credit_score", 0)
        income = facts.get("income", 0)

        if db_rules:
            min_credit_score = db_rules.get("min_credit_score", 700)
            min_income = db_rules.get("min_income", 40000)
        elif policy_version == "v1.0":
            min_credit_score = 700
            min_income = 40000
        else:
            min_credit_score = 720
            min_income = 50000

        if credit_score >= min_credit_score and income >= min_income:
            return "APPROVED", {
                "loan_amount": income * 0.5,
                "interest_rate": 5.5
            }, {
                "reason": "Applicant meets the minimum credit score and income requirements.",
                "details": {"credit_score_met": True, "income_met": True}
            }
        else:
            reasons = []
            if credit_score < min_credit_score:
                reasons.append(f"Credit score ({credit_score}) is below minimum ({min_credit_score}).")
            if income < min_income:
                reasons.append(f"Income ({income}) is below minimum ({min_income}).")
            return "REJECTED", {}, {
                "reason": "Applicant does not meet the minimum requirements.",
                "details": {"rejections": reasons}
            }


# Global engine instance
decision_engine = DecisionEngine()
