"""
SFTR AI Agents — three specialized agents that add intelligence on top of
the deterministic comparison engine.

Agents:
  1. FieldAnalyzer   — explains an unmatch and suggests resolution
  2. TradeAnalyzer   — prioritizes and summarizes all unmatches in a trade
  3. SessionNarrator — generates an executive summary of a full session
"""

from app.services.llm_provider import LLMProvider

SYSTEM_BASE = (
    "Eres un experto en reporting regulatorio SFTR (Reglamento de Operaciones de Financiación de Valores) "
    "para operaciones como repos, préstamos de valores, compraventas con pacto de recompra y préstamos de margen. "
    "Ayudas a los analistas de cumplimiento normativo de Banco Santander a conciliar discrepancias "
    "entre los informes de dos contrapartes enviados a repositorios de operaciones. "
    "Sé conciso, preciso y utiliza terminología regulatoria. "
    "IMPORTANTE: Responde SIEMPRE en español, independientemente del idioma de los datos."
)


# ─── Agent 1: Field Analyzer ─────────────────────────────────────────────────

async def analyze_field(
    provider: LLMProvider,
    field_name: str,
    table_number: int,
    obligation: str,
    emisor_value: str | None,
    receptor_value: str | None,
    root_cause: str | None,
    sft_type: str,
    action_type: str,
) -> dict:
    """
    Explain why an SFTR field is unmatched and suggest resolution steps.
    Returns: {explanation, resolution, risk_level, regulatory_impact}
    """
    system = SYSTEM_BASE + (
        "\n\nTu tarea: analiza una discrepancia en un campo SFTR y proporciona:\n"
        "1. Una breve explicación de por qué ha ocurrido esta discrepancia (2-3 frases)\n"
        "2. Pasos concretos de resolución que debe seguir el analista (2-3 puntos)\n"
        "3. Riesgo regulatorio si no se resuelve (1 frase)\n"
        "Responde ÚNICAMENTE con JSON con las claves: explanation, resolution_steps (array de strings), regulatory_risk"
    )

    user = (
        f"Discrepancia en campo SFTR:\n"
        f"- Campo: {field_name} (Tabla {table_number})\n"
        f"- Obligación: {obligation} ({'Obligatorio' if obligation == 'M' else 'Condicional' if obligation == 'C' else 'Opcional'})\n"
        f"- Tipo SFT: {sft_type} / Acción: {action_type}\n"
        f"- Valor CP1 (Emisor): {emisor_value or 'VACÍO'}\n"
        f"- Valor CP2 (Receptor): {receptor_value or 'VACÍO'}\n"
        f"- Causa raíz detectada: {root_cause or 'desconocida'}\n\n"
        "Analiza esta discrepancia y responde solo con JSON en español."
    )

    raw = await provider.complete(system, user)
    return _parse_json_response(raw, {
        "explanation": raw,
        "resolution_steps": [],
        "regulatory_risk": "",
    })


# ─── Agent 2: Trade Analyzer ─────────────────────────────────────────────────

async def analyze_trade(
    provider: LLMProvider,
    uti: str,
    sft_type: str,
    action_type: str,
    unmatches: list[dict],
) -> dict:
    """
    Summarize and prioritize all unmatches in a single trade.
    Returns: {summary, priority_order, main_risk, recommended_action}
    """
    system = SYSTEM_BASE + (
        "\n\nTu tarea: dado un listado de discrepancias SFTR en una operación, proporciona:\n"
        "1. Un resumen breve de la situación general (2-3 frases)\n"
        "2. El campo más crítico que resolver primero y por qué\n"
        "3. El principal riesgo regulatorio si no se resuelven\n"
        "4. Una acción recomendada\n"
        "Responde ÚNICAMENTE con JSON con las claves: summary, priority_field, main_risk, recommended_action. Todo en español."
    )

    fields_text = "\n".join([
        f"  - [{u['severity']}] {u['field_name']}: CP1={u.get('emisor_value','VACÍO')} vs CP2={u.get('receptor_value','VACÍO')} ({u.get('root_cause','')})"
        for u in unmatches
    ])

    user = (
        f"Operación: {uti or 'UTI desconocido'}\n"
        f"Tipo: {sft_type}/{action_type}\n"
        f"Discrepancias ({len(unmatches)} campos):\n{fields_text}\n\n"
        "Analiza y responde solo con JSON en español."
    )

    raw = await provider.complete(system, user)
    return _parse_json_response(raw, {
        "summary": raw,
        "priority_field": "",
        "main_risk": "",
        "recommended_action": "",
    })


# ─── Agent 3: Session Narrator ────────────────────────────────────────────────

async def generate_session_narrative(
    provider: LLMProvider,
    session_data: dict,
    top_fields: list[dict],
    sample_trades: list[dict],
) -> str:
    """
    Generate an executive summary of a reconciliation session.
    Returns plain text narrative suitable for compliance reporting.
    """
    system = SYSTEM_BASE + (
        "\n\nTu tarea: genera un resumen ejecutivo profesional de una sesión de conciliación SFTR "
        "adecuado para un informe de cumplimiento normativo. Incluye: evaluación general de la calidad, "
        "principales incidencias, campos con más discrepancias y acciones recomendadas. "
        "Escribe en español formal, entre 200 y 300 palabras. No uses JSON, solo texto con formato Markdown."
    )

    trades_text = ""
    if sample_trades:
        trades_text = "\nOperaciones con discrepancias (muestra):\n" + "\n".join([
            f"  - UTI {t.get('uti','?')}: {t.get('total_unmatches',0)} discrepancias ({t.get('critical_count',0)} críticas)"
            for t in sample_trades[:5]
        ])

    top_fields_text = ""
    if top_fields:
        top_fields_text = "\nCampos con más discrepancias:\n" + "\n".join([
            f"  - {f['field_name']}: {f['count']} veces"
            for f in top_fields[:5]
        ])

    user = (
        f"Sesión de conciliación #{session_data.get('id')}:\n"
        f"- Fichero: {session_data.get('filename', 'desconocido')}\n"
        f"- Contrapartes: {session_data.get('emisor_name')} vs {session_data.get('receptor_name')}\n"
        f"- Tipo SFT: {session_data.get('sft_type')} / Acción: {session_data.get('action_type')}\n"
        f"- Total operaciones: {session_data.get('total_trades', 0)}\n"
        f"- Operaciones con discrepancias: {session_data.get('trades_with_unmatches', 0)}\n"
        f"- Total discrepancias: {session_data.get('total_unmatches', 0)}\n"
        f"- Críticas: {session_data.get('critical_count', 0)}\n"
        f"- Advertencias: {session_data.get('warning_count', 0)}\n"
        f"{top_fields_text}"
        f"{trades_text}\n\n"
        "Redacta el resumen ejecutivo en español."
    )

    return await provider.complete(system, user)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_json_response(raw: str, fallback: dict) -> dict:
    import json, re
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
    # Find first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return fallback
