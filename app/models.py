import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, Integer, Numeric, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Agent(Base):
    """Agent Registry: identidad del agente, dueño, entorno, versión, estado."""
    __tablename__ = "agents"

    agent_id = Column(String, primary_key=True, default=lambda: gen_id("agt"))
    name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    tenant_id = Column(String, nullable=False, default="default")
    environment = Column(String, nullable=False, default="production")  # dev/staging/production
    version = Column(String, default="1.0.0")
    status = Column(String, default="active")  # active/suspended/revoked
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=True)

    permissions = relationship("AgentToolPermission", back_populates="agent")


class Tool(Base):
    """Tool Registry: qué existe, qué hace, qué tan sensible es."""
    __tablename__ = "tools"

    tool_id = Column(String, primary_key=True, default=lambda: gen_id("tool"))
    name = Column(String, nullable=False)
    action = Column(String, nullable=False)  # ej: transfer_money, send_email, delete_record
    description = Column(String, default="")
    sensitivity = Column(String, default="low")  # low/medium/high/critical
    domain = Column(String, default="general")   # finance/infra/data/comms...
    reversible = Column(Boolean, default=True)
    requires_approval_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    permissions = relationship("AgentToolPermission", back_populates="tool")


class AgentToolPermission(Base):
    """Qué agente puede usar qué herramienta, con qué límites."""
    __tablename__ = "agent_tool_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False)
    tool_id = Column(String, ForeignKey("tools.tool_id"), nullable=False)
    allowed = Column(Boolean, default=True)
    max_amount = Column(Numeric, nullable=True)  # límite opcional (ej. transfer_money)

    agent = relationship("Agent", back_populates="permissions")
    tool = relationship("Tool", back_populates="permissions")


class AuditLog(Base):
    """Evidencia inmutable de cada decisión tomada por el Gateway."""
    __tablename__ = "audit_log"

    event_id = Column(String, primary_key=True, default=lambda: gen_id("evt"))
    agent_id = Column(String, nullable=False)
    tool_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    risk_score = Column(Integer, nullable=False)
    decision = Column(String, nullable=False)  # ALLOW/ALLOW_WITH_LOG/REQUIRE_HUMAN_APPROVAL/BLOCK
    reasoning = Column(JSON, nullable=False)     # desglose de factores del Risk Engine
    payload_summary = Column(JSON, nullable=True)  # datos no sensibles del payload
    approval_status = Column(String, nullable=True)  # pending/approved/rejected/null
    created_at = Column(DateTime, default=datetime.utcnow)
