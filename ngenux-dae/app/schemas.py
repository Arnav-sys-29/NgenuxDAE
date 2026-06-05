from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class RequestInfo(BaseModel):
    request_id: str = Field(..., description="Unique identifier for the request")
    decision_type: str = Field(..., description="Type of decision to be made")

class ActorInfo(BaseModel):
    actor_id: str = Field(..., description="Identifier of the actor making the request")
    role: str = Field(..., description="Role of the actor")

class PolicyReference(BaseModel):
    policy_version: str = Field(..., description="Version of the policy to use")

class ContextFacts(BaseModel):
    facts: Dict[str, Any] = Field(..., description="Key-value pairs of context facts")

class DecisionInputEnvelope(BaseModel):
    request_info: RequestInfo
    actor_info: ActorInfo
    policy_reference: PolicyReference
    context_facts: ContextFacts

class DecisionOutput(BaseModel):
    decision_id: str
    status: str
    output_result: Dict[str, Any]
    explanation: Dict[str, Any]
    execution_metadata: Dict[str, Any]

class DecisionListOutput(BaseModel):
    decision_id: str
    decision_type: str
    request_id: str
    status: str

class AuditLogOutput(BaseModel):
    log_id: str
    action: str
    actor: str
    timestamp: str

class DecisionDetailOutput(BaseModel):
    decision_id: str
    decision_type: str
    request_id: str
    status: str
    input_context: Dict[str, Any]
    output_result: Dict[str, Any]
    explanation: Dict[str, Any]
    execution_metadata: Dict[str, Any]
    policy_version_used: str
    audit_logs: list[AuditLogOutput]

# ── Policy Store Schemas ──────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    name: str = Field(..., description="Unique human-readable name, e.g. loan_approval_policy")
    decision_type: str = Field(..., description="Decision type this policy applies to")
    description: Optional[str] = None

class PolicyOutput(BaseModel):
    policy_id: str
    name: str
    decision_type: str
    description: Optional[str]
    is_active: bool

class PolicyVersionCreate(BaseModel):
    version_tag: str = Field(..., description="Semantic version tag, e.g. v1.0")
    rules: Dict[str, Any] = Field(..., description="JSON rules/thresholds for the decision engine")

class PolicyVersionOutput(BaseModel):
    version_id: str
    policy_id: str
    version_tag: str
    rules: Dict[str, Any]
    is_active: bool
