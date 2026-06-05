from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.database import engine, get_db
from app.services import decision_engine

app = FastAPI(
    title="Ngenux DAE API",
    description="Decision Automation Engine API",
    version="0.1.0"
)

# Create tables if they don't exist (useful for dev before Alembic is fully configured)
# models.Base.metadata.create_all(bind=engine)

@app.post("/decisions", response_model=schemas.DecisionOutput)
def create_decision(envelope: schemas.DecisionInputEnvelope, db: Session = Depends(get_db)):
    # 1. Create Decision Record
    new_decision = models.Decision(
        decision_type=envelope.request_info.decision_type,
        request_id=envelope.request_info.request_id,
        status="PENDING",
        input_context=envelope.model_dump(),
        output_result={},  # Initial empty result until processing
        policy_version_used=envelope.policy_reference.policy_version
    )
    
    db.add(new_decision)
    db.flush() # Flush to get the generated decision_id

    # 2. Evaluate Decision
    final_status, output_result, explanation, metadata = decision_engine.evaluate_decision(
        decision_type=envelope.request_info.decision_type,
        policy_version=envelope.policy_reference.policy_version,
        facts=envelope.context_facts.facts,
        db=db
    )
    
    new_decision.status = final_status
    new_decision.output_result = output_result
    new_decision.explanation = explanation
    new_decision.execution_metadata = metadata

    # 3. Create Audit Logs
    audit_log_created = models.AuditLog(
        decision_id=new_decision.decision_id,
        action="DECISION_CREATED",
        actor=envelope.actor_info.actor_id
    )
    audit_log_evaluated = models.AuditLog(
        decision_id=new_decision.decision_id,
        action=f"EVALUATION_COMPLETED (Result: {final_status})",
        actor="system_engine"
    )
    
    db.add(audit_log_created)
    db.add(audit_log_evaluated)
    
    # Commit transaction
    db.commit()
    db.refresh(new_decision)

    # 4. Return required output schema
    return schemas.DecisionOutput(
        decision_id=new_decision.decision_id,
        status=new_decision.status,
        output_result=new_decision.output_result,
        explanation=new_decision.explanation,
        execution_metadata=new_decision.execution_metadata
    )

@app.get("/decisions", response_model=List[schemas.DecisionListOutput])
def list_decisions(db: Session = Depends(get_db)):
    decisions = db.query(models.Decision).order_by(models.Decision.created_at.desc()).all()
    return decisions

@app.get("/decisions/{decision_id}", response_model=schemas.DecisionDetailOutput)
def get_decision(decision_id: str, db: Session = Depends(get_db)):
    decision = db.query(models.Decision).filter(models.Decision.decision_id == decision_id).first()
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    logs = db.query(models.AuditLog).filter(models.AuditLog.decision_id == decision_id).order_by(models.AuditLog.timestamp.asc()).all()
    
    audit_logs = [
        schemas.AuditLogOutput(
            log_id=log.log_id,
            action=log.action,
            actor=log.actor,
            timestamp=log.timestamp.isoformat() if log.timestamp else ""
        ) for log in logs
    ]
    
    return schemas.DecisionDetailOutput(
        decision_id=decision.decision_id,
        decision_type=decision.decision_type,
        request_id=decision.request_id,
        status=decision.status,
        input_context=decision.input_context,
        output_result=decision.output_result,
        explanation=decision.explanation,
        execution_metadata=decision.execution_metadata,
        policy_version_used=decision.policy_version_used,
        audit_logs=audit_logs
    )

# ── Policy Store Endpoints ──────────────────────────────────────────────────

@app.post("/policies", response_model=schemas.PolicyOutput)
def create_policy(policy_in: schemas.PolicyCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Policy).filter(models.Policy.name == policy_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Policy name already exists")
    
    new_policy = models.Policy(
        name=policy_in.name,
        decision_type=policy_in.decision_type,
        description=policy_in.description
    )
    db.add(new_policy)
    db.commit()
    db.refresh(new_policy)
    return new_policy

@app.get("/policies", response_model=List[schemas.PolicyOutput])
def list_policies(db: Session = Depends(get_db)):
    return db.query(models.Policy).order_by(models.Policy.created_at.desc()).all()

@app.post("/policies/{policy_id}/versions", response_model=schemas.PolicyVersionOutput)
def create_policy_version(policy_id: str, version_in: schemas.PolicyVersionCreate, db: Session = Depends(get_db)):
    policy = db.query(models.Policy).filter(models.Policy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    new_version = models.PolicyVersion(
        policy_id=policy_id,
        version_tag=version_in.version_tag,
        rules=version_in.rules
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version

@app.get("/policies/{policy_id}/versions", response_model=List[schemas.PolicyVersionOutput])
def list_policy_versions(policy_id: str, db: Session = Depends(get_db)):
    policy = db.query(models.Policy).filter(models.Policy.policy_id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return db.query(models.PolicyVersion).filter(models.PolicyVersion.policy_id == policy_id).order_by(models.PolicyVersion.created_at.desc()).all()

@app.get("/policies/{policy_id}/versions/{version_tag}", response_model=schemas.PolicyVersionOutput)
def get_policy_version(policy_id: str, version_tag: str, db: Session = Depends(get_db)):
    version = db.query(models.PolicyVersion).filter(
        models.PolicyVersion.policy_id == policy_id,
        models.PolicyVersion.version_tag == version_tag
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Policy version not found")
    return version

