from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.models import Session as SessionModel, FieldComparison
from app.schemas import TopFieldItem, TrendItem

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/top-fields", response_model=list[TopFieldItem])
def top_unmatch_fields(
    limit: int = Query(default=10, le=50),
    sft_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            FieldComparison.field_name,
            FieldComparison.table_number,
            func.count(FieldComparison.id).label("count"),
        )
        .filter(FieldComparison.result == "UNMATCH")
    )

    if sft_type:
        query = query.join(SessionModel, FieldComparison.session_id == SessionModel.id).filter(SessionModel.sft_type == sft_type)

    results = (
        query.group_by(FieldComparison.field_name, FieldComparison.table_number)
        .order_by(func.count(FieldComparison.id).desc())
        .limit(limit)
        .all()
    )

    return [
        TopFieldItem(field_name=r[0], table_number=r[1], count=r[2])
        for r in results
    ]


@router.get("/trend", response_model=list[TrendItem])
def unmatch_trend(
    days: int = Query(default=30, le=365),
    db: Session = Depends(get_db),
):
    results = (
        db.query(
            func.date(SessionModel.created_at).label("date"),
            func.sum(SessionModel.total_unmatches).label("total_unmatches"),
            func.sum(SessionModel.critical_count).label("critical_count"),
            func.count(SessionModel.id).label("sessions"),
        )
        .group_by(func.date(SessionModel.created_at))
        .order_by(func.date(SessionModel.created_at).desc())
        .limit(days)
        .all()
    )

    return [
        TrendItem(
            date=str(r[0]),
            total_unmatches=r[1] or 0,
            critical_count=r[2] or 0,
            sessions=r[3] or 0,
        )
        for r in results
    ]


@router.get("/by-counterparty")
def by_counterparty(db: Session = Depends(get_db)):
    results = (
        db.query(
            SessionModel.emisor_name,
            SessionModel.receptor_name,
            func.count(SessionModel.id).label("sessions"),
            func.sum(SessionModel.total_unmatches).label("total_unmatches"),
            func.sum(SessionModel.critical_count).label("critical_count"),
        )
        .group_by(SessionModel.emisor_name, SessionModel.receptor_name)
        .order_by(func.sum(SessionModel.total_unmatches).desc())
        .all()
    )

    return [
        {
            "emisor_name": r[0],
            "receptor_name": r[1],
            "sessions": r[2],
            "total_unmatches": r[3] or 0,
            "critical_count": r[4] or 0,
        }
        for r in results
    ]


@router.get("/by-sft-type")
def by_sft_type(db: Session = Depends(get_db)):
    results = (
        db.query(
            SessionModel.sft_type,
            func.count(SessionModel.id).label("sessions"),
            func.sum(SessionModel.total_unmatches).label("total_unmatches"),
            func.sum(SessionModel.critical_count).label("critical_count"),
        )
        .group_by(SessionModel.sft_type)
        .order_by(func.sum(SessionModel.total_unmatches).desc())
        .all()
    )

    return [
        {
            "sft_type": r[0],
            "sessions": r[1],
            "total_unmatches": r[2] or 0,
            "critical_count": r[3] or 0,
        }
        for r in results
    ]
