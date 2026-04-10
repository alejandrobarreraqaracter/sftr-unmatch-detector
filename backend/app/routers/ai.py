import re
from datetime import datetime
from pydantic import BaseModel
import httpx

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from io import BytesIO

from app.routers.analytics import _get_filtered_sessions, _get_pairing_by_trade, compare_periods
from app.database import get_db
from app.models import Session as SessionModel, TradeRecord, FieldComparison, LLMUsageEvent
from app.schemas import (
    ActivateLLMProfileRequest,
    DemoUserResponse,
    LLMProfileResponse,
    LLMUsageByModelItem,
    LLMUsageByUserItem,
    LLMUsageDailyItem,
    LLMUsageLimitStatus,
    LLMUsageOverview,
)
from app.services.ai_agents import (
    analyze_field,
    analyze_trade,
    generate_session_narrative,
    generate_analytics_narrative,
    generate_comparison_narrative,
    generate_analytics_chat_response,
    is_analytics_question_in_scope,
)
from app.services.demo_users import get_demo_user
from app.services.llm_runtime import (
    activate_profile,
    enforce_usage_limit,
    get_active_profile,
    get_provider_for_request,
    get_usage_limit_status,
    list_llm_profiles,
    record_usage_event,
)
from app.services.report_export import generate_pdf_report, generate_word_report_html
from app.config import OLLAMA_BASE_URL

router = APIRouter(prefix="/api/ai", tags=["ai"])
DATE_IN_FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


class AnalyticsReportExportRequest(BaseModel):
    format: str
    narrative: str
    date_from: str | None = None
    date_to: str | None = None
    provider: str | None = None
    model: str | None = None
    product_type: str | None = None


class AnalyticsChatRequest(BaseModel):
    question: str
    date_from: str | None = None
    date_to: str | None = None
    product_type: str | None = None
    selected_day: str | None = None
    compare_from_a: str | None = None
    compare_to_a: str | None = None
    compare_from_b: str | None = None
    compare_to_b: str | None = None


def _raise_provider_unavailable(exc: Exception, provider_name: str, model_name: str) -> None:
    message = (
        f"No se pudo conectar con el proveedor IA configurado ({provider_name}/{model_name}). "
        "Revisa la configuración del provider y su conectividad de red."
    )
    if provider_name == "ollama":
        message += (
            " Si estás usando Docker y Ollama corre en tu máquina host, configura "
            f"`OLLAMA_BASE_URL={OLLAMA_BASE_URL}` o el endpoint correcto, y reinicia el backend si procede."
        )
    raise HTTPException(status_code=503, detail=message) from exc


def _get_request_user(x_demo_user: str | None) -> tuple[str, str]:
    user = get_demo_user(x_demo_user)
    if user:
        return user["username"], user["display_name"]
    return "anonymous", "Invitado"


def _prepare_llm_request(db: DBSession, x_demo_user: str | None):
    usage_status = enforce_usage_limit(db, x_demo_user)
    profile, provider = get_provider_for_request(db)
    return usage_status, profile, provider


@router.get("/status")
async def ai_status(db: DBSession = Depends(get_db)):
    """Check which AI provider is active and whether it's reachable."""
    profile, provider = get_provider_for_request(db)
    available = await provider.is_available()
    return {
        "provider": profile.provider,
        "model": profile.model,
        "label": profile.label,
        "profile_key": profile.profile_key,
        "available": available,
    }


@router.get("/profiles", response_model=list[LLMProfileResponse])
def get_profiles(db: DBSession = Depends(get_db)):
    return list_llm_profiles(db)


@router.post("/profiles/activate", response_model=LLMProfileResponse)
def activate_llm_profile(request: ActivateLLMProfileRequest, db: DBSession = Depends(get_db)):
    try:
        return activate_profile(db, request.profile_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/usage/overview", response_model=LLMUsageOverview)
def usage_overview(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
):
    query = db.query(LLMUsageEvent)
    if date_from:
        query = query.filter(func.date(LLMUsageEvent.created_at) >= date_from)
    if date_to:
        query = query.filter(func.date(LLMUsageEvent.created_at) <= date_to)

    rows = query.all()
    return LLMUsageOverview(
        total_requests=len(rows),
        total_input_tokens=sum(row.input_tokens for row in rows),
        total_output_tokens=sum(row.output_tokens for row in rows),
        total_cached_input_tokens=sum(row.cached_input_tokens for row in rows),
        total_cost=round(sum(row.estimated_total_cost for row in rows), 6),
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/usage/limits/me", response_model=LLMUsageLimitStatus)
def usage_limits_me(
    db: DBSession = Depends(get_db),
    x_demo_user: str | None = Header(default=None),
):
    return LLMUsageLimitStatus(**get_usage_limit_status(db, x_demo_user))


@router.get("/usage/daily", response_model=list[LLMUsageDailyItem])
def usage_daily(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
):
    query = db.query(LLMUsageEvent)
    if date_from:
        query = query.filter(func.date(LLMUsageEvent.created_at) >= date_from)
    if date_to:
        query = query.filter(func.date(LLMUsageEvent.created_at) <= date_to)

    grouped: dict[str, dict[str, float | int]] = {}
    for row in query.all():
        key = row.created_at.date().isoformat()
        bucket = grouped.setdefault(
            key,
            {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
        )
        bucket["requests"] += 1
        bucket["input_tokens"] += row.input_tokens
        bucket["output_tokens"] += row.output_tokens
        bucket["total_cost"] += row.estimated_total_cost

    return [
        LLMUsageDailyItem(
            date=date,
            requests=int(values["requests"]),
            input_tokens=int(values["input_tokens"]),
            output_tokens=int(values["output_tokens"]),
            total_cost=round(float(values["total_cost"]), 6),
        )
        for date, values in sorted(grouped.items())
    ]


@router.get("/usage/by-user", response_model=list[LLMUsageByUserItem])
def usage_by_user(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
):
    query = db.query(LLMUsageEvent)
    if date_from:
        query = query.filter(func.date(LLMUsageEvent.created_at) >= date_from)
    if date_to:
        query = query.filter(func.date(LLMUsageEvent.created_at) <= date_to)

    grouped: dict[str, dict[str, float | int | str]] = {}
    for row in query.all():
        bucket = grouped.setdefault(
            row.username,
            {
                "display_name": row.display_name,
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost": 0.0,
            },
        )
        bucket["requests"] += 1
        bucket["input_tokens"] += row.input_tokens
        bucket["output_tokens"] += row.output_tokens
        bucket["total_cost"] += row.estimated_total_cost

    return sorted(
        [
            LLMUsageByUserItem(
                username=username,
                display_name=str(values["display_name"]),
                requests=int(values["requests"]),
                input_tokens=int(values["input_tokens"]),
                output_tokens=int(values["output_tokens"]),
                total_cost=round(float(values["total_cost"]), 6),
            )
            for username, values in grouped.items()
        ],
        key=lambda item: item.total_cost,
        reverse=True,
    )


@router.get("/usage/by-model", response_model=list[LLMUsageByModelItem])
def usage_by_model(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
):
    query = db.query(LLMUsageEvent)
    if date_from:
        query = query.filter(func.date(LLMUsageEvent.created_at) >= date_from)
    if date_to:
        query = query.filter(func.date(LLMUsageEvent.created_at) <= date_to)

    grouped: dict[tuple[str, str], dict[str, float | int]] = {}
    for row in query.all():
        key = (row.provider, row.model)
        bucket = grouped.setdefault(
            key,
            {"requests": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
        )
        bucket["requests"] += 1
        bucket["input_tokens"] += row.input_tokens
        bucket["output_tokens"] += row.output_tokens
        bucket["total_cost"] += row.estimated_total_cost

    return sorted(
        [
            LLMUsageByModelItem(
                provider=provider,
                model=model,
                requests=int(values["requests"]),
                input_tokens=int(values["input_tokens"]),
                output_tokens=int(values["output_tokens"]),
                total_cost=round(float(values["total_cost"]), 6),
            )
            for (provider, model), values in grouped.items()
        ],
        key=lambda item: item.total_cost,
        reverse=True,
    )


@router.post("/field-comparisons/{fc_id}/analyze")
async def analyze_field_comparison(fc_id: int, db: DBSession = Depends(get_db), x_demo_user: str | None = Header(default=None)):
    """Agent 1: Analyze a single field discrepancy."""
    fc = db.query(FieldComparison).filter(FieldComparison.id == fc_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Field comparison not found")
    if fc.result != "UNMATCH":
        raise HTTPException(status_code=400, detail="Field is not an unmatch")

    trade = db.query(TradeRecord).filter(TradeRecord.id == fc.trade_id).first()

    try:
        _, profile, provider = _prepare_llm_request(db, x_demo_user)
        result = await analyze_field(
            provider=provider,
            field_name=fc.field_name,
            table_number=fc.table_number,
            obligation=fc.obligation or "M",
            emisor_value=fc.emisor_value,
            receptor_value=fc.receptor_value,
            root_cause=fc.root_cause,
            sft_type=trade.sft_type if trade else "Repo",
            action_type=trade.action_type if trade else "NEWT",
        )
        record_usage_event(db, profile, provider, "field_analysis", x_demo_user)
        return {"field_id": fc_id, "field_name": fc.field_name, **result}
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)


@router.post("/trades/{trade_id}/analyze")
async def analyze_trade_endpoint(trade_id: int, db: DBSession = Depends(get_db), x_demo_user: str | None = Header(default=None)):
    """Agent 2: Summarize and prioritize all unmatches in a trade."""
    trade = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    unmatches = [
        {
            "field_name": fc.field_name,
            "severity": fc.severity,
            "obligation": fc.obligation,
            "emisor_value": fc.emisor_value,
            "receptor_value": fc.receptor_value,
            "root_cause": fc.root_cause,
        }
        for fc in trade.field_comparisons
        if fc.result == "UNMATCH"
    ]

    if not unmatches:
        return {"trade_id": trade_id, "summary": "No unmatches found in this trade.", "priority_field": None, "main_risk": None, "recommended_action": None}

    try:
        _, profile, provider = _prepare_llm_request(db, x_demo_user)
        result = await analyze_trade(
            provider=provider,
            uti=trade.uti or f"Trade #{trade.row_number}",
            sft_type=trade.sft_type or "Repo",
            action_type=trade.action_type or "NEWT",
            unmatches=unmatches,
        )
        record_usage_event(db, profile, provider, "trade_analysis", x_demo_user)
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)
    return {"trade_id": trade_id, "uti": trade.uti, **result}


@router.post("/sessions/{session_id}/narrative")
async def session_narrative(session_id: int, db: DBSession = Depends(get_db), x_demo_user: str | None = Header(default=None)):
    """Agent 3: Generate executive narrative for a reconciliation session."""
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Top unmatched fields
    top_fields_raw = (
        db.query(
            FieldComparison.field_name,
            func.count(FieldComparison.id).label("count"),
        )
        .filter(FieldComparison.session_id == session_id, FieldComparison.result == "UNMATCH")
        .group_by(FieldComparison.field_name)
        .order_by(func.count(FieldComparison.id).desc())
        .limit(5)
        .all()
    )
    top_fields = [{"field_name": r[0], "count": r[1]} for r in top_fields_raw]

    # Sample trades with unmatches
    sample_trades_raw = (
        db.query(TradeRecord)
        .filter(TradeRecord.session_id == session_id, TradeRecord.has_unmatches == True)
        .order_by(TradeRecord.critical_count.desc())
        .limit(5)
        .all()
    )
    sample_trades = [
        {"uti": t.uti, "total_unmatches": t.total_unmatches, "critical_count": t.critical_count}
        for t in sample_trades_raw
    ]

    session_data = {
        "id": session.id,
        "filename": session.filename,
        "emisor_name": session.emisor_name,
        "receptor_name": session.receptor_name,
        "sft_type": session.sft_type,
        "action_type": session.action_type,
        "total_trades": session.total_trades,
        "trades_with_unmatches": session.trades_with_unmatches,
        "total_unmatches": session.total_unmatches,
        "critical_count": session.critical_count,
        "warning_count": session.warning_count,
    }

    try:
        _, profile, provider = _prepare_llm_request(db, x_demo_user)
        narrative = await generate_session_narrative(provider, session_data, top_fields, sample_trades)
        record_usage_event(db, profile, provider, "session_narrative", x_demo_user)
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)
    return {
        "session_id": session_id,
        "provider": profile.provider,
        "model": profile.model,
        "narrative": narrative,
    }


@router.post("/analytics/report")
async def analytics_report(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    product_type: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
    x_demo_user: str | None = Header(default=None),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    session_ids = [session.id for session in sessions]

    overview = {
        "date_from": date_from,
        "date_to": date_to,
        "sessions": len(sessions),
        "total_trades": sum(session.total_trades for session in sessions),
        "trades_with_unmatches": sum(session.trades_with_unmatches for session in sessions),
        "total_unmatches": sum(session.total_unmatches for session in sessions),
        "critical_count": sum(session.critical_count for session in sessions),
        "warning_count": sum(session.warning_count for session in sessions),
        "quality_rate": 0,
        "resolution_rate": 0,
        "unpair_trades": 0,
        "unmatch_trades": 0,
        "clean_trades": 0,
    }

    if overview["total_trades"]:
        overview["quality_rate"] = round(((overview["total_trades"] - overview["trades_with_unmatches"]) / overview["total_trades"]) * 100, 2)

    if session_ids:
        trade_pairing = _get_pairing_by_trade(db, session_ids)
        overview["unpair_trades"] = sum(1 for status in trade_pairing.values() if status == "UNPAIR")
        overview["unmatch_trades"] = sum(1 for status in trade_pairing.values() if status == "UNMATCH")
        overview["clean_trades"] = sum(1 for status in trade_pairing.values() if status == "CLEAN")

        resolved_fields = (
            db.query(func.count(FieldComparison.id))
            .filter(FieldComparison.session_id.in_(session_ids), FieldComparison.status == "RESOLVED")
            .scalar()
        ) or 0
        if overview["total_unmatches"]:
            overview["resolution_rate"] = round((resolved_fields / overview["total_unmatches"]) * 100, 2)

    daily_map: dict[str, dict] = {}
    for session in sessions:
        day = session.filename or ""
        daily_key = session.created_at.date().isoformat()
        match = __import__("re").search(r"(\d{4}-\d{2}-\d{2})", day)
        if match:
            daily_key = match.group(1)
        bucket = daily_map.setdefault(
            daily_key,
            {"date": daily_key, "sessions": 0, "total_trades": 0, "total_unmatches": 0, "critical_count": 0, "unpair_trades": 0},
        )
        bucket["sessions"] += 1
        bucket["total_trades"] += session.total_trades
        bucket["total_unmatches"] += session.total_unmatches
        bucket["critical_count"] += session.critical_count

    top_fields_raw = []
    counterparties = []
    if session_ids:
        top_fields_raw = (
            db.query(FieldComparison.field_name, func.count(FieldComparison.id).label("count"))
            .filter(FieldComparison.session_id.in_(session_ids), FieldComparison.result == "UNMATCH")
            .group_by(FieldComparison.field_name)
            .order_by(func.count(FieldComparison.id).desc())
            .limit(5)
            .all()
        )
        counterparty_map: dict[tuple[str, str], dict] = {}
        for session in sessions:
            key = (session.emisor_name or "—", session.receptor_name or "—")
            bucket = counterparty_map.setdefault(key, {
                "emisor_name": key[0],
                "receptor_name": key[1],
                "sessions": 0,
                "total_unmatches": 0,
            })
            bucket["sessions"] += 1
            bucket["total_unmatches"] += session.total_unmatches
        counterparties = sorted(counterparty_map.values(), key=lambda item: item["total_unmatches"], reverse=True)[:5]

    top_fields = [{"field_name": name, "count": count} for name, count in top_fields_raw]
    daily_items = sorted(daily_map.values(), key=lambda item: item["date"])

    try:
        _, profile, provider = _prepare_llm_request(db, x_demo_user)
        narrative = await generate_analytics_narrative(provider, overview, daily_items, top_fields, counterparties)
        record_usage_event(db, profile, provider, "analytics_report", x_demo_user)
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)
    return {
        "provider": profile.provider,
        "model": profile.model,
        "date_from": date_from,
        "date_to": date_to,
        "narrative": narrative,
    }


@router.post("/analytics/chat")
async def analytics_chat(
    request: AnalyticsChatRequest,
    db: DBSession = Depends(get_db),
    x_demo_user: str | None = Header(default=None),
):
    usage_status, profile, provider = _prepare_llm_request(db, x_demo_user)
    if not is_analytics_question_in_scope(request.question):
        return {
            "provider": profile.provider,
            "model": profile.model,
            "date_from": request.date_from,
            "date_to": request.date_to,
            "question": request.question,
            "answer": (
                "Solo puedo responder preguntas relacionadas con la analítica, las discrepancias, "
                "los periodos comparados, las contrapartes, los campos y el riesgo operativo del rango seleccionado."
            ),
            "suggested_visual": "none",
            "selected_day": request.selected_day,
            "product_type": request.product_type,
            "guardrail_triggered": True,
            "usage_status": usage_status,
        }
    sessions = _get_filtered_sessions(db, request.date_from, request.date_to, request.product_type)
    session_ids = [session.id for session in sessions]

    overview = {
        "date_from": request.date_from,
        "date_to": request.date_to,
        "sessions": len(sessions),
        "total_trades": sum(session.total_trades for session in sessions),
        "trades_with_unmatches": sum(session.trades_with_unmatches for session in sessions),
        "total_unmatches": sum(session.total_unmatches for session in sessions),
        "critical_count": sum(session.critical_count for session in sessions),
        "warning_count": sum(session.warning_count for session in sessions),
        "quality_rate": 0,
        "resolution_rate": 0,
        "unpair_trades": 0,
        "unmatch_trades": 0,
        "clean_trades": 0,
    }

    if overview["total_trades"]:
        overview["quality_rate"] = round(((overview["total_trades"] - overview["trades_with_unmatches"]) / overview["total_trades"]) * 100, 2)

    daily_map: dict[str, dict] = {}
    top_fields = []
    counterparties = []

    if session_ids:
        trade_pairing = _get_pairing_by_trade(db, session_ids)
        overview["unpair_trades"] = sum(1 for status in trade_pairing.values() if status == "UNPAIR")
        overview["unmatch_trades"] = sum(1 for status in trade_pairing.values() if status == "UNMATCH")
        overview["clean_trades"] = sum(1 for status in trade_pairing.values() if status == "CLEAN")

        resolved_fields = (
            db.query(func.count(FieldComparison.id))
            .filter(FieldComparison.session_id.in_(session_ids), FieldComparison.status == "RESOLVED")
            .scalar()
        ) or 0
        if overview["total_unmatches"]:
            overview["resolution_rate"] = round((resolved_fields / overview["total_unmatches"]) * 100, 2)

        for session in sessions:
            day = session.filename or ""
            daily_key = session.created_at.date().isoformat()
            match = __import__("re").search(r"(\d{4}-\d{2}-\d{2})", day)
            if match:
                daily_key = match.group(1)
            bucket = daily_map.setdefault(
                daily_key,
                {"date": daily_key, "sessions": 0, "total_trades": 0, "total_unmatches": 0, "critical_count": 0, "unpair_trades": 0},
            )
            bucket["sessions"] += 1
            bucket["total_trades"] += session.total_trades
            bucket["total_unmatches"] += session.total_unmatches
            bucket["critical_count"] += session.critical_count

        top_fields_raw = (
            db.query(FieldComparison.field_name, func.count(FieldComparison.id).label("count"))
            .filter(FieldComparison.session_id.in_(session_ids), FieldComparison.result == "UNMATCH")
            .group_by(FieldComparison.field_name)
            .order_by(func.count(FieldComparison.id).desc())
            .limit(10)
            .all()
        )
        top_fields = [{"field_name": name, "count": count} for name, count in top_fields_raw]

        counterparty_map: dict[tuple[str, str], dict] = {}
        for session in sessions:
            key = (session.emisor_name or "—", session.receptor_name or "—")
            bucket = counterparty_map.setdefault(key, {
                "emisor_name": key[0],
                "receptor_name": key[1],
                "sessions": 0,
                "total_unmatches": 0,
                "critical_count": 0,
            })
            bucket["sessions"] += 1
            bucket["total_unmatches"] += session.total_unmatches
            bucket["critical_count"] += session.critical_count
        counterparties = sorted(counterparty_map.values(), key=lambda item: item["total_unmatches"], reverse=True)[:10]

    context_lines: list[str] = []

    if request.selected_day:
        day_sessions = [
            session
            for session in sessions
            if (
                (match := __import__("re").search(r"(\d{4}-\d{2}-\d{2})", session.filename or ""))
                and match.group(1) == request.selected_day
            ) or (
                not __import__("re").search(r"(\d{4}-\d{2}-\d{2})", session.filename or "")
                and session.created_at.date().isoformat() == request.selected_day
            )
        ]
        if day_sessions:
            context_lines.append(f"Día seleccionado: {request.selected_day}")
            context_lines.append(
                f"- Sesiones del día: {len(day_sessions)} | Operaciones: {sum(s.total_trades for s in day_sessions)} | "
                f"Discrepancias: {sum(s.total_unmatches for s in day_sessions)} | Críticas: {sum(s.critical_count for s in day_sessions)}"
            )

    if all([request.compare_from_a, request.compare_to_a, request.compare_from_b, request.compare_to_b]):
        comparison = compare_periods(
            from_a=request.compare_from_a,
            to_a=request.compare_to_a,
            from_b=request.compare_from_b,
            to_b=request.compare_to_b,
            product_type=request.product_type,
            db=db,
        )
        deltas = comparison["deltas"]
        context_lines.append(
            f"Comparación activa: A({request.compare_from_a} a {request.compare_to_a}) vs "
            f"B({request.compare_from_b} a {request.compare_to_b})"
        )
        context_lines.append(
            f"- Delta discrepancias: {deltas['total_unmatches']['abs']:+} | "
            f"Delta críticas: {deltas['critical_count']['abs']:+} | "
            f"Delta unpair: {deltas['unpair_trades']['abs']:+}"
        )
        top_changes = comparison["top_fields_comparison"][:5]
        if top_changes:
            context_lines.append("Campos con mayor variación:")
            context_lines.extend(
                [
                    f"- {item['field_name']} (Tabla {item['table_number']}): {item['count_a']} -> {item['count_b']} ({item['delta']:+})"
                    for item in top_changes
                ]
            )

    question = request.question
    if context_lines:
        question = f"{request.question}\n\nContexto adicional activo:\n" + "\n".join(context_lines)

    try:
        chat_result = await generate_analytics_chat_response(
            provider,
            question,
            overview,
            sorted(daily_map.values(), key=lambda item: item["date"]),
            top_fields,
            counterparties,
        )
        record_usage_event(db, profile, provider, "analytics_chat", x_demo_user)
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)
    return {
        "provider": profile.provider,
        "model": profile.model,
        "date_from": request.date_from,
        "date_to": request.date_to,
        "question": request.question,
        "answer": chat_result.get("answer", ""),
        "suggested_visual": chat_result.get("suggested_visual", "none"),
        "selected_day": request.selected_day,
        "product_type": request.product_type,
        "guardrail_triggered": False,
        "usage_status": usage_status,
    }


@router.post("/analytics/compare-report")
async def analytics_compare_report(
    from_a: str = Query(...),
    to_a: str = Query(...),
    from_b: str = Query(...),
    to_b: str = Query(...),
    product_type: str | None = Query(default=None),
    db: DBSession = Depends(get_db),
    x_demo_user: str | None = Header(default=None),
):
    comparison = compare_periods(from_a=from_a, to_a=to_a, from_b=from_b, to_b=to_b, product_type=product_type, db=db)
    try:
        _, profile, provider = _prepare_llm_request(db, x_demo_user)
        narrative = await generate_comparison_narrative(
            provider,
            comparison["period_a"],
            comparison["period_b"],
            comparison["deltas"],
            comparison["top_fields_comparison"],
        )
        record_usage_event(db, profile, provider, "analytics_compare_report", x_demo_user)
    except httpx.HTTPError as exc:
        _raise_provider_unavailable(exc, profile.provider, profile.model)
    return {
        "provider": profile.provider,
        "model": profile.model,
        "date_from": f"{from_a} | {from_b}",
        "date_to": f"{to_a} | {to_b}",
        "narrative": narrative,
    }


@router.post("/analytics/report/export")
async def analytics_report_export(request: AnalyticsReportExportRequest):
    if request.format not in {"pdf", "doc"}:
        raise HTTPException(status_code=400, detail="Invalid format")
    is_predatadas = request.product_type == "predatadas"
    title = "Informe Analítico Predatadas" if is_predatadas else "Informe Analítico SFTR"
    subtitle = (
        f"Rango: {request.date_from or 'inicio disponible'} - {request.date_to or 'fin disponible'} "
        f"| Generado con {request.provider or 'provider'} / {request.model or 'model'}"
    )
    narrative = request.narrative or ""

    date_label = request.date_from or datetime.utcnow().date().isoformat()
    safe_date = DATE_IN_FILENAME_RE.search(date_label)
    filename_date = safe_date.group(1) if safe_date else datetime.utcnow().strftime("%Y-%m-%d")
    filename_prefix = "predatadas" if is_predatadas else "sftr"

    if request.format == "pdf":
        payload = generate_pdf_report(title, subtitle, narrative)
        filename = f"{filename_prefix}_analytics_report_{filename_date}.pdf"
        media_type = "application/pdf"
    else:
        payload = generate_word_report_html(title, subtitle, narrative)
        filename = f"{filename_prefix}_analytics_report_{filename_date}.doc"
        media_type = "application/msword"

    return StreamingResponse(
        BytesIO(payload),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
