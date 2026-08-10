"""
Risk Engine — MVP determinístico (sin ML).
Calcula un score 0-100 a partir de una suma ponderada de 6 factores.
Cada factor queda documentado en 'reasoning' para que la decisión sea
auditable y defendible, no una caja negra.
"""

SENSITIVITY_WEIGHTS = {"low": 5, "medium": 15, "high": 30, "critical": 45}

# Umbrales de decisión sobre el score final (0-100)
THRESHOLDS = {
    "ALLOW": 30,                     # score < 30
    "ALLOW_WITH_LOG": 50,            # 30 <= score < 50
    "REQUIRE_HUMAN_APPROVAL": 80,    # 50 <= score < 80
    # score >= 80 -> BLOCK
}


def _economic_impact_score(amount: float | None, max_amount: float | None) -> int:
    """
    Impacto económico. Si hay un límite definido para el agente (max_amount),
    se pondera relativo a ese límite (más grave si se acerca/excede).
    Si no hay límite, se usa una escala absoluta simple.
    """
    if amount is None:
        return 0

    if max_amount:
        ratio = amount / float(max_amount)
        if ratio > 1:
            return 25  # excede el límite permitido
        if ratio > 0.75:
            return 18
        if ratio > 0.4:
            return 10
        return 3

    # Sin límite configurado: escala absoluta (ajustable por negocio)
    if amount >= 50000:
        return 25
    if amount >= 10000:
        return 18
    if amount >= 1000:
        return 10
    return 3


def _pattern_deviation_score(prior_actions_last_24h: int) -> int:
    """Desviación simple de patrón: muchas acciones en 24h = más sospechoso."""
    if prior_actions_last_24h >= 10:
        return 15
    if prior_actions_last_24h >= 5:
        return 8
    if prior_actions_last_24h >= 2:
        return 3
    return 0


def calculate_risk(tool, action_payload, context, permission) -> tuple[int, dict, str]:
    """
    Devuelve (score, reasoning_breakdown, decision)
    """
    reasoning = {}

    # 1. Sensibilidad de la herramienta/dato
    sens_score = SENSITIVITY_WEIGHTS.get(tool.sensitivity, 5)
    reasoning["sensitivity"] = {"value": tool.sensitivity, "points": sens_score}

    # 2. Impacto económico
    max_amount = float(permission.max_amount) if (permission and permission.max_amount) else None
    econ_score = _economic_impact_score(action_payload.amount, max_amount)
    reasoning["economic_impact"] = {
        "amount": action_payload.amount, "limit": max_amount, "points": econ_score
    }

    # 3. Irreversibilidad
    irrev_score = 0 if tool.reversible else 20
    reasoning["irreversibility"] = {"reversible": tool.reversible, "points": irrev_score}

    # 4. Privilegios de la herramienta (proxy: dominio + approval por defecto)
    priv_score = 10 if tool.requires_approval_default else 0
    reasoning["tool_privilege"] = {
        "requires_approval_default": tool.requires_approval_default, "points": priv_score
    }

    # 5. Destino externo
    dest_score = 15 if action_payload.destination_type == "external" else 0
    reasoning["external_destination"] = {
        "destination_type": action_payload.destination_type, "points": dest_score
    }

    # 6. Desviación del patrón esperado
    pattern_score = _pattern_deviation_score(context.prior_actions_last_24h)
    reasoning["pattern_deviation"] = {
        "prior_actions_last_24h": context.prior_actions_last_24h, "points": pattern_score
    }

    total = sens_score + econ_score + irrev_score + priv_score + dest_score + pattern_score
    total = min(total, 100)

    if total < THRESHOLDS["ALLOW"]:
        decision = "ALLOW"
    elif total < THRESHOLDS["ALLOW_WITH_LOG"]:
        decision = "ALLOW_WITH_LOG"
    elif total < THRESHOLDS["REQUIRE_HUMAN_APPROVAL"]:
        decision = "REQUIRE_HUMAN_APPROVAL"
    else:
        decision = "BLOCK"

    reasoning["total_score"] = total
    return total, reasoning, decision
