import time
from typing import Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session


class DecisionEngine:
    def __init__(self):
        # Maps decision_type to its evaluation handler
        self._handlers = {
            "LOAN_APPROVAL":      self._evaluate_loan_approval,
            "HR_HIRING":          self._evaluate_hr_hiring,
            "INSURANCE_CLAIM":    self._evaluate_insurance_claim,
            "VENDOR_ONBOARDING":  self._evaluate_vendor_onboarding,
            "EMPLOYEE_LEAVE":     self._evaluate_employee_leave,
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

    # ── BANKING ──────────────────────────────────────────────────────────────

    def _evaluate_loan_approval(
        self, policy_version: str, facts: Dict[str, Any], db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Banking — evaluate a loan application."""
        rules = db_rules or ({"min_credit_score": 700, "min_income": 40000}
                             if policy_version == "v1.0" else
                             {"min_credit_score": 720, "min_income": 50000})

        credit_score = facts.get("credit_score", 0)
        income = facts.get("income", 0)
        min_credit_score = rules.get("min_credit_score", 700)
        min_income = rules.get("min_income", 40000)

        reasons = []
        if credit_score < min_credit_score:
            reasons.append(f"Credit score ({credit_score}) is below minimum ({min_credit_score}).")
        if income < min_income:
            reasons.append(f"Income ({income}) is below minimum ({min_income}).")

        if not reasons:
            return "APPROVED", {
                "loan_amount": income * 0.5,
                "interest_rate": 5.5
            }, {
                "reason": "Applicant meets all minimum requirements.",
                "details": {"credit_score_met": True, "income_met": True}
            }
        return "REJECTED", {}, {
            "reason": "Applicant does not meet the minimum requirements.",
            "details": {"rejections": reasons}
        }

    # ── HUMAN RESOURCES ───────────────────────────────────────────────────────

    def _evaluate_hr_hiring(
        self, policy_version: str, facts: Dict[str, Any], db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Human Resources — evaluate a job applicant."""
        rules = db_rules or {"min_years_experience": 2, "required_degree": "Bachelor"}

        years_exp = facts.get("years_experience", 0)
        degree = facts.get("degree", "None")
        min_exp = rules.get("min_years_experience", 2)
        req_degree = rules.get("required_degree", "Bachelor")

        degree_rank = {"None": 0, "High School": 1, "Associate": 2,
                       "Bachelor": 3, "Master": 4, "PhD": 5}
        applicant_rank = degree_rank.get(degree, 0)
        required_rank = degree_rank.get(req_degree, 3)

        reasons = []
        if years_exp < min_exp:
            reasons.append(f"Experience ({years_exp} yrs) is below required ({min_exp} yrs).")
        if applicant_rank < required_rank:
            reasons.append(f"Degree '{degree}' does not meet required '{req_degree}'.")

        if not reasons:
            return "HIRED", {
                "next_step": "Schedule technical interview",
                "grade_band": "L4" if years_exp >= 5 else "L3"
            }, {
                "reason": "Applicant meets all hiring criteria.",
                "details": {"experience_met": True, "degree_met": True}
            }
        return "REJECTED", {}, {
            "reason": "Applicant does not meet the hiring criteria.",
            "details": {"rejections": reasons}
        }

    # ── INSURANCE ─────────────────────────────────────────────────────────────

    def _evaluate_insurance_claim(
        self, policy_version: str, facts: Dict[str, Any], db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Insurance — evaluate whether a claim should be approved."""
        rules = db_rules or {"max_claim_amount": 50000, "max_days_since_incident": 30}

        claim_amount = facts.get("claim_amount", 0)
        days_since = facts.get("days_since_incident", 0)
        policy_active = facts.get("policy_active", True)
        max_claim = rules.get("max_claim_amount", 50000)
        max_days = rules.get("max_days_since_incident", 30)

        reasons = []
        if not policy_active:
            reasons.append("Insurance policy is inactive at the time of the claim.")
        if claim_amount > max_claim:
            reasons.append(f"Claim amount (${claim_amount:,}) exceeds policy limit (${max_claim:,}).")
        if days_since > max_days:
            reasons.append(f"Incident reported {days_since} days ago, exceeding the {max_days}-day window.")

        if not reasons:
            payout = min(claim_amount, max_claim)
            return "APPROVED", {
                "payout_amount": payout,
                "processing_days": 5
            }, {
                "reason": "Claim meets all policy conditions and is within limits.",
                "details": {"within_limit": True, "within_reporting_window": True}
            }
        return "REJECTED", {}, {
            "reason": "Claim does not meet policy conditions.",
            "details": {"rejections": reasons}
        }

    # ── PROCUREMENT ───────────────────────────────────────────────────────────

    def _evaluate_vendor_onboarding(
        self, policy_version: str, facts: Dict[str, Any], db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Procurement — evaluate whether a vendor should be onboarded."""
        rules = db_rules or {"min_compliance_score": 75, "min_years_in_business": 3}

        compliance = facts.get("compliance_score", 0)
        years_biz = facts.get("years_in_business", 0)
        blacklisted = facts.get("blacklisted", False)
        min_compliance = rules.get("min_compliance_score", 75)
        min_years = rules.get("min_years_in_business", 3)

        reasons = []
        if blacklisted:
            reasons.append("Vendor is on the regulatory blacklist.")
        if compliance < min_compliance:
            reasons.append(f"Compliance score ({compliance}) is below threshold ({min_compliance}).")
        if years_biz < min_years:
            reasons.append(f"Business age ({years_biz} yrs) is below minimum ({min_years} yrs).")

        if not reasons:
            tier = "Gold" if compliance >= 90 else "Silver" if compliance >= 80 else "Bronze"
            return "APPROVED", {
                "vendor_tier": tier,
                "onboarding_sla_days": 14
            }, {
                "reason": "Vendor meets all onboarding requirements.",
                "details": {"compliance_met": True, "tenure_met": True}
            }
        return "REJECTED", {}, {
            "reason": "Vendor does not meet onboarding requirements.",
            "details": {"rejections": reasons}
        }

    # ── HR — LEAVE MANAGEMENT ─────────────────────────────────────────────────

    def _evaluate_employee_leave(
        self, policy_version: str, facts: Dict[str, Any], db_rules: Optional[Dict[str, Any]]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """HR — evaluate an employee leave request."""
        rules = db_rules or {"min_notice_days": 2, "max_consecutive_days": 10}

        days_requested = facts.get("days_requested", 0)
        notice_days = facts.get("notice_days_given", 0)
        balance_remaining = facts.get("leave_balance_remaining", 0)
        min_notice = rules.get("min_notice_days", 2)
        max_consecutive = rules.get("max_consecutive_days", 10)

        reasons = []
        if notice_days < min_notice:
            reasons.append(f"Only {notice_days} day(s) notice given; minimum is {min_notice}.")
        if days_requested > balance_remaining:
            reasons.append(f"Requested {days_requested} days but only {balance_remaining} days remain.")
        if days_requested > max_consecutive:
            reasons.append(f"Cannot approve more than {max_consecutive} consecutive days at once.")

        if not reasons:
            return "APPROVED", {
                "approved_days": days_requested,
                "remaining_balance": balance_remaining - days_requested
            }, {
                "reason": "Leave request meets all policy requirements.",
                "details": {"sufficient_balance": True, "notice_met": True}
            }
        return "REJECTED", {}, {
            "reason": "Leave request does not meet policy requirements.",
            "details": {"rejections": reasons}
        }


# Global engine instance
decision_engine = DecisionEngine()
