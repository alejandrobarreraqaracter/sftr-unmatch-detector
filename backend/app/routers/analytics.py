import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import FieldComparison, Session as SessionModel, TradeRecord
from app.schemas import TopFieldItem

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

UNPAIR_FIELDS = {"UTI", "Other counterparty"}
DATE_IN_FILENAME_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _parse_date(date_value: Optional[str]) -> Optional[date]:
    if not date_value:
        return None
    return datetime.strptime(date_value, "%Y-%m-%d").date()


def _session_business_date(session: SessionModel) -> date:
    if session.filename:
        match = DATE_IN_FILENAME_RE.search(session.filename)
        if match:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    created_at = session.created_at or datetime.utcnow()
    return created_at.date()


def _get_filtered_sessions(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    product_type: Optional[str] = None,
) -> list[SessionModel]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)

    query = db.query(SessionModel).order_by(SessionModel.created_at.asc())
    if product_type:
        query = query.filter(SessionModel.product_type == product_type)
    sessions = query.all()
    filtered: list[SessionModel] = []
    for session in sessions:
        session_date = _session_business_date(session)
        if start and session_date < start:
            continue
        if end and session_date > end:
            continue
        filtered.append(session)
    return filtered


def _get_pairing_by_trade(db: Session, session_ids: list[int]) -> dict[int, str]:
    if not session_ids:
        return {}

    trades = (
        db.query(TradeRecord.id, TradeRecord.has_unmatches)
        .filter(TradeRecord.session_id.in_(session_ids))
        .all()
    )
    trade_ids = [trade_id for trade_id, _ in trades]
    if not trade_ids:
        return {}

    unpair_trade_ids = {
        trade_id
        for trade_id, _field_name in (
            db.query(FieldComparison.trade_id, FieldComparison.field_name)
            .filter(
                FieldComparison.trade_id.in_(trade_ids),
                FieldComparison.field_name.in_(UNPAIR_FIELDS),
                FieldComparison.result == "UNMATCH",
            )
            .all()
        )
    }

    pairing_by_trade: dict[int, str] = {}
    for trade_id, has_unmatches in trades:
        if trade_id in unpair_trade_ids:
            pairing_by_trade[trade_id] = "UNPAIR"
        elif has_unmatches:
            pairing_by_trade[trade_id] = "UNMATCH"
        else:
            pairing_by_trade[trade_id] = "CLEAN"
    return pairing_by_trade


def _build_overview_from_sessions(db: Session, sessions: list[SessionModel], date_from: Optional[str], date_to: Optional[str]) -> dict:
    session_ids = [session.id for session in sessions]
    if not session_ids:
        return {
            "date_from": date_from,
            "date_to": date_to,
            "sessions": 0,
            "total_trades": 0,
            "trades_with_unmatches": 0,
            "total_unmatches": 0,
            "critical_count": 0,
            "warning_count": 0,
            "unpair_trades": 0,
            "unmatch_trades": 0,
            "clean_trades": 0,
            "pending_fields": 0,
            "resolved_fields": 0,
            "in_negotiation_fields": 0,
            "excluded_fields": 0,
            "quality_rate": 0,
            "resolution_rate": 0,
        }

    status_counts = Counter(
        dict(
            db.query(FieldComparison.status, func.count(FieldComparison.id))
            .filter(FieldComparison.session_id.in_(session_ids))
            .group_by(FieldComparison.status)
            .all()
        )
    )
    pairing_counts = Counter(_get_pairing_by_trade(db, session_ids).values())

    total_trades = sum(session.total_trades for session in sessions)
    trades_with_unmatches = sum(session.trades_with_unmatches for session in sessions)
    total_unmatches = sum(session.total_unmatches for session in sessions)
    resolved_fields = status_counts.get("RESOLVED", 0)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "sessions": len(sessions),
        "total_trades": total_trades,
        "trades_with_unmatches": trades_with_unmatches,
        "total_unmatches": total_unmatches,
        "critical_count": sum(session.critical_count for session in sessions),
        "warning_count": sum(session.warning_count for session in sessions),
        "unpair_trades": pairing_counts.get("UNPAIR", 0),
        "unmatch_trades": pairing_counts.get("UNMATCH", 0),
        "clean_trades": pairing_counts.get("CLEAN", 0),
        "pending_fields": status_counts.get("PENDING", 0),
        "resolved_fields": resolved_fields,
        "in_negotiation_fields": status_counts.get("IN_NEGOTIATION", 0),
        "excluded_fields": status_counts.get("EXCLUDED", 0),
        "quality_rate": round(((total_trades - trades_with_unmatches) / total_trades) * 100, 2) if total_trades else 0,
        "resolution_rate": round((resolved_fields / total_unmatches) * 100, 2) if total_unmatches else 0,
    }


def _top_fields_map(db: Session, session_ids: list[int]) -> dict[tuple[str, int], int]:
    if not session_ids:
        return {}
    rows = (
        db.query(
            FieldComparison.field_name,
            FieldComparison.table_number,
            func.count(FieldComparison.id).label("count"),
        )
        .filter(
            FieldComparison.result == "UNMATCH",
            FieldComparison.session_id.in_(session_ids),
        )
        .group_by(FieldComparison.field_name, FieldComparison.table_number)
        .all()
    )
    return {(field_name, table_number): count for field_name, table_number, count in rows}


@router.get("/overview")
def analytics_overview(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    return _build_overview_from_sessions(db, sessions, date_from, date_to)


@router.get("/daily")
def analytics_daily(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    if not sessions:
        return []

    session_ids = [session.id for session in sessions]
    trades = db.query(TradeRecord).filter(TradeRecord.session_id.in_(session_ids)).all()
    trade_pairing = _get_pairing_by_trade(db, session_ids)

    sessions_by_date: dict[date, list[SessionModel]] = defaultdict(list)
    for session in sessions:
        sessions_by_date[_session_business_date(session)].append(session)

    trades_by_session: dict[int, list[TradeRecord]] = defaultdict(list)
    for trade in trades:
        trades_by_session[trade.session_id].append(trade)

    items = []
    for day in sorted(sessions_by_date.keys()):
        day_sessions = sessions_by_date[day]
        day_trades = [trade for session in day_sessions for trade in trades_by_session.get(session.id, [])]
        day_trade_ids = [trade.id for trade in day_trades]

        status_counts = Counter(
            dict(
                db.query(FieldComparison.status, func.count(FieldComparison.id))
                .filter(FieldComparison.trade_id.in_(day_trade_ids))
                .group_by(FieldComparison.status)
                .all()
            )
        ) if day_trade_ids else {}
        pairing_counts = Counter(trade_pairing.get(trade.id, "CLEAN") for trade in day_trades)

        items.append(
            {
                "date": day.isoformat(),
                "sessions": len(day_sessions),
                "total_trades": sum(session.total_trades for session in day_sessions),
                "trades_with_unmatches": sum(session.trades_with_unmatches for session in day_sessions),
                "total_unmatches": sum(session.total_unmatches for session in day_sessions),
                "critical_count": sum(session.critical_count for session in day_sessions),
                "warning_count": sum(session.warning_count for session in day_sessions),
                "unpair_trades": pairing_counts.get("UNPAIR", 0),
                "unmatch_trades": pairing_counts.get("UNMATCH", 0),
                "clean_trades": pairing_counts.get("CLEAN", 0),
                "resolved_fields": status_counts.get("RESOLVED", 0),
                "pending_fields": status_counts.get("PENDING", 0),
            }
        )

    return items


@router.get("/top-fields", response_model=list[TopFieldItem])
def top_unmatch_fields(
    limit: int = Query(default=10, le=50),
    sft_type: Optional[str] = None,
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    session_ids = [session.id for session in sessions]
    if not session_ids:
        return []

    query = (
        db.query(
            FieldComparison.field_name,
            FieldComparison.table_number,
            func.count(FieldComparison.id).label("count"),
        )
        .filter(
            FieldComparison.result == "UNMATCH",
            FieldComparison.session_id.in_(session_ids),
        )
    )

    if sft_type:
        query = query.join(SessionModel, FieldComparison.session_id == SessionModel.id).filter(SessionModel.sft_type == sft_type)

    results = (
        query.group_by(FieldComparison.field_name, FieldComparison.table_number)
        .order_by(func.count(FieldComparison.id).desc())
        .limit(limit)
        .all()
    )

    return [TopFieldItem(field_name=r[0], table_number=r[1], count=r[2]) for r in results]


@router.get("/by-counterparty")
def by_counterparty(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    if not sessions:
        return []

    grouped: dict[tuple[str, str], dict] = {}
    for session in sessions:
        key = (session.emisor_name or "—", session.receptor_name or "—")
        bucket = grouped.setdefault(
            key,
            {
                "emisor_name": key[0],
                "receptor_name": key[1],
                "sessions": 0,
                "total_unmatches": 0,
                "critical_count": 0,
                "total_trades": 0,
            },
        )
        bucket["sessions"] += 1
        bucket["total_unmatches"] += session.total_unmatches
        bucket["critical_count"] += session.critical_count
        bucket["total_trades"] += session.total_trades

    return sorted(grouped.values(), key=lambda item: item["total_unmatches"], reverse=True)


@router.get("/by-sft-type")
def by_sft_type(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions = _get_filtered_sessions(db, date_from, date_to, product_type)
    if not sessions:
        return []

    grouped: dict[str, dict] = {}
    for session in sessions:
        key = session.sft_type or "—"
        bucket = grouped.setdefault(
            key,
            {
                "sft_type": key,
                "sessions": 0,
                "total_unmatches": 0,
                "critical_count": 0,
                "total_trades": 0,
            },
        )
        bucket["sessions"] += 1
        bucket["total_unmatches"] += session.total_unmatches
        bucket["critical_count"] += session.critical_count
        bucket["total_trades"] += session.total_trades

    return sorted(grouped.values(), key=lambda item: item["total_unmatches"], reverse=True)


@router.get("/compare")
def compare_periods(
    from_a: str = Query(...),
    to_a: str = Query(...),
    from_b: str = Query(...),
    to_b: str = Query(...),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    sessions_a = _get_filtered_sessions(db, from_a, to_a, product_type)
    sessions_b = _get_filtered_sessions(db, from_b, to_b, product_type)

    overview_a = _build_overview_from_sessions(db, sessions_a, from_a, to_a)
    overview_b = _build_overview_from_sessions(db, sessions_b, from_b, to_b)

    metric_names = [
        "sessions",
        "total_trades",
        "trades_with_unmatches",
        "total_unmatches",
        "critical_count",
        "warning_count",
        "unpair_trades",
        "unmatch_trades",
        "clean_trades",
        "quality_rate",
        "resolution_rate",
    ]
    deltas: dict[str, dict[str, float | None]] = {}
    for metric in metric_names:
        a_value = float(overview_a.get(metric, 0) or 0)
        b_value = float(overview_b.get(metric, 0) or 0)
        abs_delta = round(b_value - a_value, 2)
        pct_delta = round(((b_value - a_value) / a_value) * 100, 2) if a_value else None
        deltas[metric] = {
            "a": a_value,
            "b": b_value,
            "abs": abs_delta,
            "pct": pct_delta,
        }

    top_map_a = _top_fields_map(db, [session.id for session in sessions_a])
    top_map_b = _top_fields_map(db, [session.id for session in sessions_b])
    all_field_keys = set(top_map_a.keys()) | set(top_map_b.keys())
    field_comparison = [
        {
            "field_name": field_name,
            "table_number": table_number,
            "count_a": top_map_a.get((field_name, table_number), 0),
            "count_b": top_map_b.get((field_name, table_number), 0),
            "delta": top_map_b.get((field_name, table_number), 0) - top_map_a.get((field_name, table_number), 0),
        }
        for field_name, table_number in all_field_keys
    ]
    field_comparison.sort(key=lambda item: (item["delta"], item["count_b"]), reverse=True)

    return {
        "period_a": overview_a,
        "period_b": overview_b,
        "deltas": deltas,
        "top_fields_comparison": field_comparison[:15],
    }


@router.get("/sessions-by-day")
def sessions_by_day(
    day: str = Query(...),
    product_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    target_day = _parse_date(day)
    if not target_day:
        return []

    sessions = [
        session
        for session in db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
        if not product_type or session.product_type == product_type
        if _session_business_date(session) == target_day
    ]

    return [
        {
            "id": session.id,
            "created_at": session.created_at,
            "business_date": target_day.isoformat(),
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
        for session in sessions
    ]
