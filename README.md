# ERO — MVP del Action Gateway

Gateway funcional: intercepta acciones de agentes, evalúa con Policy Engine +
Risk Engine, decide ALLOW / ALLOW_WITH_LOG / REQUIRE_HUMAN_APPROVAL / BLOCK,
y deja evidencia en Audit Log.

## Instalación en Termux

```bash
pkg update && pkg install python -y
pip install -r requirements.txt
```

## Cargar datos de ejemplo (FinanceBot, SalesAgent, DataAgent)

```bash
python -m app.seed
```

## Levantar el servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docs interactivos (Swagger) en: http://localhost:8000/docs

## Probar los 3 casos del dashboard

**1. FinanceBot transfiere $15,000 (excede su límite de $5,000) → debería BLOQUEAR**
```bash
curl -X POST http://localhost:8000/gateway/action \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {"agent_id": "agt_financebot"},
    "tool": {"tool_id": "tool_transfer_money"},
    "action_payload": {"amount": 15000, "currency": "USD", "destination_type": "external"},
    "context": {"prior_actions_last_24h": 3}
  }'
```

**2. SalesAgent envía un email → debería PERMITIR**
```bash
curl -X POST http://localhost:8000/gateway/action \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {"agent_id": "agt_salesagent"},
    "tool": {"tool_id": "tool_send_email"},
    "action_payload": {"destination_type": "internal"},
    "context": {"prior_actions_last_24h": 1}
  }'
```

**3. DataAgent elimina un registro → debería REQUERIR APROBACIÓN HUMANA**
```bash
curl -X POST http://localhost:8000/gateway/action \
  -H "Content-Type: application/json" \
  -d '{
    "agent": {"agent_id": "agt_dataagent"},
    "tool": {"tool_id": "tool_delete_record"},
    "action_payload": {"destination_type": "internal"},
    "context": {"prior_actions_last_24h": 0}
  }'
```

## Ver el Audit Log completo

```bash
curl http://localhost:8000/audit-log
```

## Ver aprobaciones pendientes

```bash
curl http://localhost:8000/approvals/pending
```

## Aprobar/rechazar un evento (usa el event_id que te devolvió el gateway)

```bash
curl -X POST http://localhost:8000/approvals/<event_id>/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewer": "jose_perez", "comment": "Verificado con el equipo"}'
```

## Estructura del proyecto

```
ero_mvp/
├── app/
│   ├── main.py            # Action Gateway (endpoints FastAPI)
│   ├── models.py          # Agent Registry, Tool Registry, Audit Log (SQLAlchemy)
│   ├── schemas.py         # Contrato del evento (Pydantic)
│   ├── risk_engine.py     # Score 0-100, determinístico, explicable
│   ├── policy_engine.py   # Reglas duras (evalúan antes que el score)
│   └── seed.py            # Datos de ejemplo
├── requirements.txt
└── ero.db                 # se crea solo al arrancar (SQLite)
```

## Notas para producción (no MVP)

- Cambiar `DATABASE_URL` en `database.py` a Postgres cuando salgas de prototipo.
- Añadir autenticación real (API keys por agente / OAuth2 para el dashboard).
- `payload_summary` en Audit Log NO debe incluir datos sensibles crudos —
  hoy es una versión simplificada, hay que revisarla antes de producción.
