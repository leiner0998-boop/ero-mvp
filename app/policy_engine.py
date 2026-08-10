"""
Policy Engine — reglas determinísticas que se evalúan ANTES del Risk Engine.
Si una política dura se viola, ni siquiera se calcula el score: se bloquea
o se fuerza aprobación de inmediato. Esto es lo que hace que las políticas
"vivan en runtime" y no solo en un documento.
"""


class PolicyViolation(Exception):
    def __init__(self, decision: str, reason: str):
        self.decision = decision  # BLOCK o REQUIRE_HUMAN_APPROVAL
        self.reason = reason
        super().__init__(reason)


def evaluate_policies(agent, tool, permission, action_payload):
    """
    Lanza PolicyViolation si alguna regla dura se incumple.
    Si todo pasa, retorna silenciosamente y el flujo continúa al Risk Engine.
    """

    # 1. El agente debe existir y estar activo
    if agent is None:
        raise PolicyViolation("BLOCK", "Agente no registrado en Agent Registry")

    if agent.status != "active":
        raise PolicyViolation("BLOCK", f"Agente en estado '{agent.status}', no puede ejecutar acciones")

    # 2. La herramienta debe existir
    if tool is None:
        raise PolicyViolation("BLOCK", "Herramienta no registrada en Tool Registry")

    # 3. El agente debe tener permiso explícito sobre la herramienta
    if permission is None or not permission.allowed:
        raise PolicyViolation("BLOCK", "El agente no tiene permiso para usar esta herramienta")

    # 4. Límite económico duro: si se excede, no es solo "riesgo alto", es bloqueo directo
    if permission.max_amount is not None and action_payload.amount is not None:
        if action_payload.amount > float(permission.max_amount) * 1.5:
            raise PolicyViolation(
                "BLOCK",
                f"Monto ({action_payload.amount}) excede en +50% el límite permitido "
                f"({permission.max_amount}) para este agente"
            )

    # 5. Herramientas marcadas como "siempre requieren aprobación humana"
    if tool.requires_approval_default:
        raise PolicyViolation(
            "REQUIRE_HUMAN_APPROVAL",
            f"La herramienta '{tool.action}' requiere aprobación humana por política, "
            f"independientemente del score de riesgo"
        )

    # Si no hay violaciones, no se lanza nada -> continúa al Risk Engine
    return
