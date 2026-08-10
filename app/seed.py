"""
Carga datos de ejemplo que replican el mockup del dashboard:
- FinanceBot -> transfer_money  (esperado: BLOCK / REQUIRE_HUMAN_APPROVAL)
- SalesAgent -> send_email      (esperado: ALLOW)
- DataAgent  -> delete_record   (esperado: REQUIRE_HUMAN_APPROVAL)

Correr con: python -m app.seed
"""
from app.database import SessionLocal, Base, engine
from app import models

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- Agentes ---
agents_data = [
    {"agent_id": "agt_financebot", "name": "FinanceBot", "owner": "finance_team",
     "environment": "production", "version": "2.1.0"},
    {"agent_id": "agt_salesagent", "name": "SalesAgent", "owner": "sales_team",
     "environment": "production", "version": "1.4.2"},
    {"agent_id": "agt_dataagent", "name": "DataAgent", "owner": "data_team",
     "environment": "production", "version": "1.0.0"},
]
for data in agents_data:
    if not db.query(models.Agent).filter_by(agent_id=data["agent_id"]).first():
        db.add(models.Agent(**data, status="active"))

# --- Tools ---
tools_data = [
    {"tool_id": "tool_transfer_money", "name": "Bank Transfer", "action": "transfer_money",
     "sensitivity": "critical", "domain": "finance", "reversible": False,
     "requires_approval_default": False},
    {"tool_id": "tool_send_email", "name": "Send Email", "action": "send_email",
     "sensitivity": "low", "domain": "comms", "reversible": True,
     "requires_approval_default": False},
    {"tool_id": "tool_delete_record", "name": "Delete Record", "action": "delete_record",
     "sensitivity": "high", "domain": "data", "reversible": False,
     "requires_approval_default": True},
]
for data in tools_data:
    if not db.query(models.Tool).filter_by(tool_id=data["tool_id"]).first():
        db.add(models.Tool(**data))

db.commit()

# --- Permisos (con límite de monto para FinanceBot) ---
perms_data = [
    {"agent_id": "agt_financebot", "tool_id": "tool_transfer_money",
     "allowed": True, "max_amount": 5000},
    {"agent_id": "agt_salesagent", "tool_id": "tool_send_email",
     "allowed": True, "max_amount": None},
    {"agent_id": "agt_dataagent", "tool_id": "tool_delete_record",
     "allowed": True, "max_amount": None},
]
for data in perms_data:
    exists = db.query(models.AgentToolPermission).filter_by(
        agent_id=data["agent_id"], tool_id=data["tool_id"]
    ).first()
    if not exists:
        db.add(models.AgentToolPermission(**data))

db.commit()
db.close()

print("✅ Seed completo: 3 agentes, 3 tools, 3 permisos cargados en ero.db")
