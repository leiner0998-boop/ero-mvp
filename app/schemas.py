from typing import Optional, Literal
from pydantic import BaseModel, Field


# ---------- Contrato del Evento de Acción (Agente -> Gateway) ----------

class AgentRef(BaseModel):
    agent_id: str


class ToolRef(BaseModel):
    tool_id: str


class ActionPayload(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    destination_account: Optional[str] = None
    destination_type: Optional[Literal["internal", "external"]] = "internal"
    extra: Optional[dict] = None  # cualquier dato adicional específico de la acción


class ActionContext(BaseModel):
    session_id: Optional[str] = None
    prior_actions_last_24h: int = 0


class ActionEvent(BaseModel):
    agent: AgentRef
    tool: ToolRef
    action_payload: ActionPayload = ActionPayload()
    context: ActionContext = ActionContext()


# ---------- Registro de Agentes / Tools ----------

class AgentCreate(BaseModel):
    name: str
    owner: str
    tenant_id: str = "default"
    environment: Literal["dev", "staging", "production"] = "production"
    version: str = "1.0.0"


class ToolCreate(BaseModel):
    name: str
    action: str
    description: str = ""
    sensitivity: Literal["low", "medium", "high", "critical"] = "low"
    domain: str = "general"
    reversible: bool = True
    requires_approval_default: bool = False


class PermissionCreate(BaseModel):
    agent_id: str
    tool_id: str
    allowed: bool = True
    max_amount: Optional[float] = None


# ---------- Respuesta del Gateway ----------

class GatewayDecision(BaseModel):
    event_id: str
    decision: Literal["ALLOW", "ALLOW_WITH_LOG", "REQUIRE_HUMAN_APPROVAL", "BLOCK"]
    risk_score: int
    reasoning: dict


class ApprovalAction(BaseModel):
    reviewer: str
    comment: Optional[str] = None
