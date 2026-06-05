import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Policy, PolicyVersion

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ngenux_dae")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed_db():
    db = SessionLocal()
    
    # Check if policy exists
    existing_policy = db.query(Policy).filter(Policy.name == "loan_approval_policy").first()
    if existing_policy:
        print("Policy already exists. Skipping seed.")
        db.close()
        return

    # 1. Create Policy
    policy = Policy(
        name="loan_approval_policy",
        decision_type="LOAN_APPROVAL",
        description="Core policy for evaluating loan applications"
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    
    # 2. Create Policy Version v1.0
    rules = {
        "min_credit_score": 700,
        "min_income": 40000
    }
    version = PolicyVersion(
        policy_id=policy.policy_id,
        version_tag="v1.0",
        rules=rules
    )
    db.add(version)
    db.commit()
    
    print("Successfully seeded LOAN_APPROVAL policy and v1.0 rules!")
    db.close()

if __name__ == "__main__":
    seed_db()
