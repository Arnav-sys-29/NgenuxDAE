import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Policy, PolicyVersion

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ngenux_dae")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

POLICIES = [
    {
        "name": "loan_approval_policy",
        "decision_type": "LOAN_APPROVAL",
        "description": "Banking — evaluate loan applications based on credit score and income",
        "version_tag": "v1.0",
        "rules": {
            "min_credit_score": 700,
            "min_income": 40000
        }
    },
    {
        "name": "hr_hiring_policy",
        "decision_type": "HR_HIRING",
        "description": "Human Resources — evaluate job applicants based on experience and degree",
        "version_tag": "v1.0",
        "rules": {
            "min_years_experience": 2,
            "required_degree": "Bachelor"
        }
    },
    {
        "name": "insurance_claim_policy",
        "decision_type": "INSURANCE_CLAIM",
        "description": "Insurance — approve or reject claims based on amount and reporting window",
        "version_tag": "v1.0",
        "rules": {
            "max_claim_amount": 50000,
            "max_days_since_incident": 30
        }
    },
    {
        "name": "vendor_onboarding_policy",
        "decision_type": "VENDOR_ONBOARDING",
        "description": "Procurement — evaluate vendors based on compliance score and business tenure",
        "version_tag": "v1.0",
        "rules": {
            "min_compliance_score": 75,
            "min_years_in_business": 3
        }
    },
    {
        "name": "employee_leave_policy",
        "decision_type": "EMPLOYEE_LEAVE",
        "description": "HR — approve or reject employee leave requests based on balance and notice",
        "version_tag": "v1.0",
        "rules": {
            "min_notice_days": 2,
            "max_consecutive_days": 10
        }
    }
]

def seed_db():
    db = SessionLocal()

    for p in POLICIES:
        existing = db.query(Policy).filter(Policy.name == p["name"]).first()
        if existing:
            print(f"  [SKIP] '{p['name']}' already exists.")
            continue

        policy = Policy(
            name=p["name"],
            decision_type=p["decision_type"],
            description=p["description"]
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)

        version = PolicyVersion(
            policy_id=policy.policy_id,
            version_tag=p["version_tag"],
            rules=p["rules"]
        )
        db.add(version)
        db.commit()
        print(f"  [OK]   Seeded '{p['name']}' ({p['version_tag']})")

    db.close()
    print("\nAll policies seeded successfully!")

if __name__ == "__main__":
    seed_db()
