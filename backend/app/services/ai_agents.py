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


async def generate_analytics_narrative(
    provider: LLMProvider,
    overview: dict,
    daily_items: list[dict],
    top_fields: list[dict],
    counterparties: list[dict],
) -> str:
    system = SYSTEM_BASE + (
        "\n\nTu tarea: generar un informe ejecutivo sobre la analítica agregada de conciliación SFTR "
        "para un rango de fechas. Debes resumir la evolución temporal, identificar los días más problemáticos, "
        "explicar la relación entre unpair y unmatch, destacar los campos y contrapartes con más incidencias "
        "y cerrar con recomendaciones operativas. "
        "Escribe en español formal, entre 250 y 400 palabras, con Markdown simple."
    )

    top_days = sorted(daily_items, key=lambda item: item.get("total_unmatches", 0), reverse=True)[:5]
    days_text = "\n".join(
        f"  - {item.get('date')}: {item.get('total_unmatches', 0)} discrepancias, "
        f"{item.get('critical_count', 0)} críticas, {item.get('unpair_trades', 0)} unpair"
        for item in top_days
    ) or "  - No hay datos diarios disponibles"

    top_fields_text = "\n".join(
        f"  - {item.get('field_name')}: {item.get('count', 0)} discrepancias"
        for item in top_fields[:5]
    ) or "  - No hay campos destacados"

    counterparties_text = "\n".join(
        f"  - {item.get('emisor_name')} vs {item.get('receptor_name')}: "
        f"{item.get('total_unmatches', 0)} discrepancias en {item.get('sessions', 0)} sesiones"
        for item in counterparties[:5]
    ) or "  - No hay contrapartes destacadas"

    user = (
        "Rango analítico seleccionado:\n"
        f"- Desde: {overview.get('date_from') or 'inicio disponible'}\n"
        f"- Hasta: {overview.get('date_to') or 'fin disponible'}\n"
        f"- Sesiones: {overview.get('sessions', 0)}\n"
        f"- Operaciones: {overview.get('total_trades', 0)}\n"
        f"- Operaciones con discrepancias: {overview.get('trades_with_unmatches', 0)}\n"
        f"- Discrepancias totales: {overview.get('total_unmatches', 0)}\n"
        f"- Críticas: {overview.get('critical_count', 0)}\n"
        f"- Advertencias: {overview.get('warning_count', 0)}\n"
        f"- Unpair: {overview.get('unpair_trades', 0)}\n"
        f"- Unmatch: {overview.get('unmatch_trades', 0)}\n"
        f"- Limpias: {overview.get('clean_trades', 0)}\n"
        f"- Tasa de calidad: {overview.get('quality_rate', 0)}%\n"
        f"- Tasa de resolución: {overview.get('resolution_rate', 0)}%\n\n"
        "Días con más incidencias:\n"
        f"{days_text}\n\n"
        "Campos con más incidencias:\n"
        f"{top_fields_text}\n\n"
        "Contrapartes con más incidencias:\n"
        f"{counterparties_text}\n\n"
        "Redacta el informe en español."
    )

    return await provider.complete(system, user)


async def generate_regulatory_narrative(
    provider: LLMProvider,
    report: dict,
) -> str:
    overview = report["overview"]
    top_fields = report.get("top_fields", [])[:5]
    top_counterparties = report.get("top_counterparties", [])[:5]
    open_items = report.get("open_items", [])[:10]
    daily_items = report.get("daily_summary", [])[:10]
    risk_residual = report.get("risk_residual") or {}
    previous_comparison = report.get("comparison_to_previous_period") or {}
    deltas = previous_comparison.get("deltas", {})

    system = SYSTEM_BASE + (
        "\n\nTu tarea: redactar un informe regulatorio ejecutivo sobre un rango de conciliación SFTR. "
        "Debes apoyarte exclusivamente en los agregados proporcionados y no inventar cifras. "
        "Incluye: alcance, resultado global, focos de riesgo, backlog abierto, remediación visible y riesgo residual. "
        "Escribe en español formal, entre 250 y 450 palabras, con Markdown simple."
    )

    daily_text = "\n".join(
        f"- {item.get('date')}: {item.get('total_unmatches', 0)} discrepancias, {item.get('critical_count', 0)} críticas, {item.get('unpair_trades', 0)} unpair"
        for item in daily_items
    ) or "- No hay resumen diario disponible"
    top_fields_text = "\n".join(
        f"- {item.get('field_name')}: {item.get('count', 0)} discrepancias"
        for item in top_fields
    ) or "- No hay campos destacados"
    counterparties_text = "\n".join(
        f"- {item.get('emisor_name')} vs {item.get('receptor_name')}: {item.get('total_unmatches', 0)} discrepancias"
        for item in top_counterparties
    ) or "- No hay contrapartes destacadas"
    open_items_text = "\n".join(
        f"- {item.get('business_date')} · UTI {item.get('uti') or '—'} · {item.get('field_name')} · {item.get('severity')} · {item.get('status')} · {item.get('assignee') or 'Sin asignar'}"
        for item in open_items
    ) or "- No hay open items disponibles"

    user = (
        f"Periodo: {report.get('date_from') or 'inicio disponible'} a {report.get('date_to') or 'fin disponible'}\n"
        f"Sesiones: {report.get('sessions', 0)}\n"
        f"Operaciones: {overview.get('total_trades', 0)}\n"
        f"Operaciones con discrepancias: {overview.get('trades_with_unmatches', 0)}\n"
        f"UNPAIR: {overview.get('unpair_trades', 0)}\n"
        f"UNMATCH: {overview.get('unmatch_trades', 0)}\n"
        f"Discrepancias totales: {overview.get('total_unmatches', 0)}\n"
        f"Críticas: {overview.get('critical_count', 0)}\n"
        f"Advertencias: {overview.get('warning_count', 0)}\n"
        f"Pendientes: {overview.get('pending_fields', 0)}\n"
        f"Resueltas: {overview.get('resolved_fields', 0)}\n"
        f"Calidad: {overview.get('quality_rate', 0)}%\n"
        f"Resolución: {overview.get('resolution_rate', 0)}%\n"
        f"Open items: {report.get('open_items_count', 0)}\n"
        f"Critical open items: {report.get('critical_open_items_count', 0)}\n\n"
        "Resumen diario:\n"
        f"{daily_text}\n\n"
        "Top fields:\n"
        f"{top_fields_text}\n\n"
        "Top counterparties:\n"
        f"{counterparties_text}\n\n"
        "Open items destacados:\n"
        f"{open_items_text}\n\n"
        "Comparación con el periodo anterior:\n"
        f"- Periodo anterior: {previous_comparison.get('previous_date_from', 'n/d')} a {previous_comparison.get('previous_date_to', 'n/d')}\n"
        f"- Delta discrepancias: {deltas.get('total_unmatches', {}).get('abs', 0):+}\n"
        f"- Delta críticas: {deltas.get('critical_count', {}).get('abs', 0):+}\n"
        f"- Delta UNPAIR: {deltas.get('unpair_trades', {}).get('abs', 0):+}\n"
        f"- Delta calidad: {deltas.get('quality_rate', {}).get('abs', 0):+}\n"
        f"- Delta resolución: {deltas.get('resolution_rate', {}).get('abs', 0):+}\n\n"
        "Riesgo residual:\n"
        f"- Nivel: {risk_residual.get('level', 'n/d')}\n"
        f"- Resumen: {risk_residual.get('summary', 'n/d')}\n\n"
        "Redacta el informe ejecutivo en español."
    )

    return await provider.complete(system, user)


async def generate_comparison_narrative(
    provider: LLMProvider,
    period_a: dict,
    period_b: dict,
    deltas: dict,
    top_fields_comparison: list[dict],
) -> str:
    system = SYSTEM_BASE + (
        "\n\nTu tarea: generar un informe ejecutivo comparativo entre dos periodos analíticos SFTR. "
        "Debes explicar si la calidad mejora o empeora, destacar cambios en discrepancias, críticas, unpair, "
        "calidad y resolución, y señalar los campos que más empeoran o mejoran. "
        "Cierra con una recomendación operativa concreta. "
        "Escribe en español formal, entre 220 y 350 palabras, con Markdown simple."
    )

    top_worsening = [item for item in top_fields_comparison if item.get("delta", 0) > 0][:5]
    top_improving = [item for item in sorted(top_fields_comparison, key=lambda item: item.get("delta", 0)) if item.get("delta", 0) < 0][:5]

    worsening_text = "\n".join(
        f"  - {item.get('field_name')} (Tabla {item.get('table_number')}): {item.get('count_a', 0)} -> {item.get('count_b', 0)} (delta {item.get('delta', 0):+d})"
        for item in top_worsening
    ) or "  - No hay empeoramientos relevantes"

    improving_text = "\n".join(
        f"  - {item.get('field_name')} (Tabla {item.get('table_number')}): {item.get('count_a', 0)} -> {item.get('count_b', 0)} (delta {item.get('delta', 0):+d})"
        for item in top_improving
    ) or "  - No hay mejoras relevantes"

    user = (
        f"Periodo A: {period_a.get('date_from')} a {period_a.get('date_to')}\n"
        f"- Sesiones: {period_a.get('sessions', 0)}\n"
        f"- Operaciones: {period_a.get('total_trades', 0)}\n"
        f"- Discrepancias: {period_a.get('total_unmatches', 0)}\n"
        f"- Críticas: {period_a.get('critical_count', 0)}\n"
        f"- Unpair: {period_a.get('unpair_trades', 0)}\n"
        f"- Calidad: {period_a.get('quality_rate', 0)}%\n"
        f"- Resolución: {period_a.get('resolution_rate', 0)}%\n\n"
        f"Periodo B: {period_b.get('date_from')} a {period_b.get('date_to')}\n"
        f"- Sesiones: {period_b.get('sessions', 0)}\n"
        f"- Operaciones: {period_b.get('total_trades', 0)}\n"
        f"- Discrepancias: {period_b.get('total_unmatches', 0)}\n"
        f"- Críticas: {period_b.get('critical_count', 0)}\n"
        f"- Unpair: {period_b.get('unpair_trades', 0)}\n"
        f"- Calidad: {period_b.get('quality_rate', 0)}%\n"
        f"- Resolución: {period_b.get('resolution_rate', 0)}%\n\n"
        "Deltas clave:\n"
        f"  - Discrepancias: {deltas.get('total_unmatches', {}).get('abs', 0):+}\n"
        f"  - Críticas: {deltas.get('critical_count', {}).get('abs', 0):+}\n"
        f"  - Unpair: {deltas.get('unpair_trades', {}).get('abs', 0):+}\n"
        f"  - Calidad: {deltas.get('quality_rate', {}).get('abs', 0):+}\n"
        f"  - Resolución: {deltas.get('resolution_rate', {}).get('abs', 0):+}\n\n"
        "Campos que empeoran:\n"
        f"{worsening_text}\n\n"
        "Campos que mejoran:\n"
        f"{improving_text}\n\n"
        "Redacta el informe comparativo en español."
    )

    return await provider.complete(system, user)


async def generate_analytics_chat_response(
    provider: LLMProvider,
    question: str,
    overview: dict,
    daily_items: list[dict],
    top_fields: list[dict],
    counterparties: list[dict],
) -> dict:
    system = SYSTEM_BASE + (
        "\n\nTu tarea: responder preguntas analíticas sobre sesiones SFTR usando solo los datos agregados proporcionados. "
        "No inventes cifras. Si la pregunta no puede responderse completamente con los datos dados, dilo de forma explícita y responde con la mejor aproximación posible. "
        "Da respuestas ejecutivas, claras y accionables, en español, con Markdown simple y entre 80 y 220 palabras. "
        "Cuando sea útil, sugiere una visualización para acompañar la respuesta. "
        "Responde ÚNICAMENTE con JSON con las claves: answer, suggested_visual. "
        "suggested_visual debe ser uno de: none, daily_trend, top_fields, counterparties, day_sessions, comparison."
    )

    top_days = sorted(daily_items, key=lambda item: item.get("total_unmatches", 0), reverse=True)[:5]
    days_text = "\n".join(
        f"  - {item.get('date')}: {item.get('total_unmatches', 0)} discrepancias, "
        f"{item.get('critical_count', 0)} críticas, {item.get('unpair_trades', 0)} unpair, {item.get('total_trades', 0)} operaciones"
        for item in top_days
    ) or "  - No hay datos diarios disponibles"

    top_fields_text = "\n".join(
        f"  - {item.get('field_name')}: {item.get('count', 0)} discrepancias"
        for item in top_fields[:10]
    ) or "  - No hay campos destacados"

    counterparties_text = "\n".join(
        f"  - {item.get('emisor_name')} vs {item.get('receptor_name')}: "
        f"{item.get('total_unmatches', 0)} discrepancias, {item.get('critical_count', 0)} críticas"
        for item in counterparties[:10]
    ) or "  - No hay contrapartes destacadas"

    user = (
        f"Pregunta del usuario:\n{question}\n\n"
        "Contexto analítico disponible:\n"
        f"- Rango: {overview.get('date_from') or 'inicio disponible'} a {overview.get('date_to') or 'fin disponible'}\n"
        f"- Sesiones: {overview.get('sessions', 0)}\n"
        f"- Operaciones: {overview.get('total_trades', 0)}\n"
        f"- Operaciones con discrepancias: {overview.get('trades_with_unmatches', 0)}\n"
        f"- Discrepancias totales: {overview.get('total_unmatches', 0)}\n"
        f"- Críticas: {overview.get('critical_count', 0)}\n"
        f"- Advertencias: {overview.get('warning_count', 0)}\n"
        f"- Unpair: {overview.get('unpair_trades', 0)}\n"
        f"- Unmatch: {overview.get('unmatch_trades', 0)}\n"
        f"- Limpias: {overview.get('clean_trades', 0)}\n"
        f"- Tasa de calidad: {overview.get('quality_rate', 0)}%\n"
        f"- Tasa de resolución: {overview.get('resolution_rate', 0)}%\n\n"
        "Días más problemáticos:\n"
        f"{days_text}\n\n"
        "Campos con más discrepancias:\n"
        f"{top_fields_text}\n\n"
        "Contrapartes con más discrepancias:\n"
        f"{counterparties_text}\n\n"
        "Responde en español."
    )

    raw = await provider.complete(system, user)
    return _parse_json_response(raw, {
        "answer": raw,
        "suggested_visual": "none",
    })


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
