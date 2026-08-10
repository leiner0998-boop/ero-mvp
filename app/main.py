from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from app.database import Base, engine, get_db
from app import models, schemas
from app.risk_engine import calculate_risk
from app.policy_engine import evaluate_policies, PolicyViolation

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ERO — Action Gateway",
    description="Evento de Riesgo Operativo: gateway que intercepta, evalúa y controla tool calls de agentes de IA.",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Agent Registry
# ---------------------------------------------------------------------------

@app.post("/agents", response_model=None, tags=["Agent Registry"])
def create_agent(payload: schemas.AgentCreate, db: Session = Depends(get_db)):
    agent = models.Agent(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@app.get("/agents", tags=["Agent Registry"])
def list_agents(db: Session = Depends(get_db)):
    return db.query(models.Agent).all()


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

@app.post("/tools", tags=["Tool Registry"])
def create_tool(payload: schemas.ToolCreate, db: Session = Depends(get_db)):
    tool = models.Tool(**payload.model_dump())
    db.add(tool)
    db.commit()
    db.refresh(tool)
    return tool


@app.get("/tools", tags=["Tool Registry"])
def list_tools(db: Session = Depends(get_db)):
    return db.query(models.Tool).all()


@app.post("/permissions", tags=["Tool Registry"])
def create_permission(payload: schemas.PermissionCreate, db: Session = Depends(get_db)):
    perm = models.AgentToolPermission(**payload.model_dump())
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


# ---------------------------------------------------------------------------
# Action Gateway — el endpoint central
# ---------------------------------------------------------------------------

@app.post("/gateway/action", response_model=schemas.GatewayDecision, tags=["Gateway"])
def gateway_action(event: schemas.ActionEvent, db: Session = Depends(get_db)):
    agent = db.query(models.Agent).filter_by(agent_id=event.agent.agent_id).first()
    tool = db.query(models.Tool).filter_by(tool_id=event.tool.tool_id).first()
    permission = None
    if agent and tool:
        permission = (
            db.query(models.AgentToolPermission)
            .filter_by(agent_id=agent.agent_id, tool_id=tool.tool_id)
            .first()
        )

    # --- 1. Policy Engine: reglas duras primero ---
    try:
        evaluate_policies(agent, tool, permission, event.action_payload)
        policy_forced_decision = None
        policy_reason = None
    except PolicyViolation as violation:
        policy_forced_decision = violation.decision
        policy_reason = violation.reason

    # --- 2. Risk Engine: solo si hay agente y tool válidos para puntuar ---
    if agent and tool:
        score, reasoning, risk_decision = calculate_risk(
            tool, event.action_payload, event.context, permission
        )
    else:
        score, reasoning, risk_decision = 100, {"error": "agent/tool no encontrados"}, "BLOCK"

    # --- 3. Decision Engine: la política dura manda sobre el score ---
    if policy_forced_decision:
        final_decision = policy_forced_decision
        reasoning["policy_override"] = policy_reason
    else:
        final_decision = risk_decision

    if agent:
        agent.last_seen_at = datetime.utcnow()

    # --- 4. Audit Log: se registra SIEMPRE, sin excepción ---
    log = models.AuditLog(
        agent_id=event.agent.agent_id,
        tool_id=event.tool.tool_id,
        action=tool.action if tool else "unknown",
        risk_score=score,
        decision=final_decision,
        reasoning=reasoning,
        payload_summary={
            "amount": event.action_payload.amount,
            "destination_type": event.action_payload.destination_type,
        },
        approval_status="pending" if final_decision == "REQUIRE_HUMAN_APPROVAL" else None,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return schemas.GatewayDecision(
        event_id=log.event_id,
        decision=final_decision,
        risk_score=score,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------

@app.get("/audit-log", tags=["Audit Log"])
def get_audit_log(limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(models.AuditLog)
        .order_by(desc(models.AuditLog.created_at))
        .limit(limit)
        .all()
    )


# ---------------------------------------------------------------------------
# Approval Flow
# ---------------------------------------------------------------------------

@app.get("/approvals/pending", tags=["Approval Flow"])
def pending_approvals(db: Session = Depends(get_db)):
    return db.query(models.AuditLog).filter_by(approval_status="pending").all()


@app.post("/approvals/{event_id}/approve", tags=["Approval Flow"])
def approve_event(event_id: str, payload: schemas.ApprovalAction, db: Session = Depends(get_db)):
    log = db.query(models.AuditLog).filter_by(event_id=event_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    log.approval_status = "approved"
    log.reasoning = {**log.reasoning, "approved_by": payload.reviewer, "comment": payload.comment}
    db.commit()
    return {"event_id": event_id, "status": "approved"}


@app.post("/approvals/{event_id}/reject", tags=["Approval Flow"])
def reject_event(event_id: str, payload: schemas.ApprovalAction, db: Session = Depends(get_db)):
    log = db.query(models.AuditLog).filter_by(event_id=event_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    log.approval_status = "rejected"
    log.reasoning = {**log.reasoning, "rejected_by": payload.reviewer, "comment": payload.comment}
    db.commit()
    return {"event_id": event_id, "status": "rejected"}


@app.get("/", tags=["Root"])
def root():
    return {
        "product": "ERO — Evento de Riesgo Operativo",
        "status": "running",
        "docs": "/docs",
    }
