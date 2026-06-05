import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Decision(Base):
    __tablename__ = "decisions"

    decision_id = Column(String(36), primary_key=True, default=generate_uuid)
    decision_type = Column(String, nullable=False)
    request_id = Column(String, index=True, nullable=False)
    status = Column(String, nullable=False, default="PENDING")
    input_context = Column(JSON, nullable=False)
    output_result = Column(JSON, nullable=False, default=dict)
    explanation = Column(JSON, nullable=True, default=dict)
    execution_metadata = Column(JSON, nullable=True, default=dict)
    policy_version_used = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String(36), primary_key=True, default=generate_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.decision_id"), nullable=False)
    action = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Policy(Base):
    __tablename__ = "policies"

    policy_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True)
    decision_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    version_id = Column(String(36), primary_key=True, default=generate_uuid)
    policy_id = Column(String(36), ForeignKey("policies.policy_id"), nullable=False)
    version_tag = Column(String, nullable=False)          # e.g. "v1.0"
    rules = Column(JSON, nullable=False)                  # the actual thresholds
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
