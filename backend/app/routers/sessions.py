from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from app.database import get_db
from app.models import Session as SessionModel, TradeRecord, FieldComparison, ActivityLog
from app.schemas import (
    SessionResponse, SessionDetailResponse, SessionSummary,
    TradeRecordResponse, TradeDetailResponse,
    FieldComparisonResponse, FieldComparisonUpdate,
    ActivityLogResponse, BulkUpdateRequest,
)
from app.services.file_parser import parse_tabular_csv
from app.services.comparison import compare_trade
from app.services.export import generate_xlsx

router = APIRouter(prefix="/api", tags=["sessions"])


# ─── Upload ───────────────────────────────────────────────────────────────────

@router.post("/sessions/upload", response_model=SessionResponse)
async def upload_and_compare(
    file: UploadFile = File(...),
    emisor_name: str = Form(default=""),
    receptor_name: str = Form(default=""),
    db: DBSession = Depends(get_db),
):
    content = await file.read()
    rows = parse_tabular_csv(content)

    if not rows:
        raise HTTPException(status_code=400, detail="No data rows found in file")

    # Infer session-level sft_type / action_type from most common value in rows
    sft_types = [r["sft_type"] for r in rows if r["sft_type"]]
    action_types = [r["action_type"] for r in rows if r["action_type"]]
    session_sft = _most_common(sft_types) or "Repo"
    session_action = _most_common(action_types) or "NEWT"

    session = SessionModel(
        sft_type=session_sft,
        action_type=session_action,
        emisor_name=emisor_name or "CP1",
        receptor_name=receptor_name or "CP2",
        filename=file.filename,
    )
    db.add(session)
    db.flush()

    session_total_fields = 0
    session_total_unmatches = 0
    session_critical = 0
    session_warning = 0
    session_trades_with_unmatches = 0

    for idx, row in enumerate(rows):
        sft = row["sft_type"] or session_sft
        action = row["action_type"] or session_action

        trade = TradeRecord(
            session_id=session.id,
            row_number=idx + 1,
            uti=row["uti"] or None,
            sft_type=sft,
            action_type=action,
            emisor_lei=row.get("emisor_lei") or None,
            receptor_lei=row.get("receptor_lei") or None,
        )
        db.add(trade)
        db.flush()

        comparisons = compare_trade(row["emisor"], row["receptor"], sft, action)

        trade_unmatches = 0
        trade_critical = 0
        trade_warning = 0

        for c in comparisons:
            fc = FieldComparison(
                trade_id=trade.id,
                session_id=session.id,
                table_number=c["table_number"],
                field_number=c["field_number"],
                field_name=c["field_name"],
                obligation=c["obligation"],
                emisor_value=c["emisor_value"],
                receptor_value=c["receptor_value"],
                result=c["result"],
                severity=c["severity"],
                root_cause=c["root_cause"],
                status=c["status"],
                validated=c["validated"],
            )
            db.add(fc)

            if c["result"] == "UNMATCH":
                trade_unmatches += 1
                if c["severity"] == "CRITICAL":
                    trade_critical += 1
                elif c["severity"] == "WARNING":
                    trade_warning += 1

        trade.total_fields = len(comparisons)
        trade.total_unmatches = trade_unmatches
        trade.critical_count = trade_critical
        trade.warning_count = trade_warning
        trade.has_unmatches = trade_unmatches > 0

        session_total_fields += len(comparisons)
        session_total_unmatches += trade_unmatches
        session_critical += trade_critical
        session_warning += trade_warning
        if trade_unmatches > 0:
            session_trades_with_unmatches += 1

    session.total_trades = len(rows)
    session.total_fields = session_total_fields
    session.total_unmatches = session_total_unmatches
    session.critical_count = session_critical
    session.warning_count = session_warning
    session.trades_with_unmatches = session_trades_with_unmatches

    log = ActivityLog(
        session_id=session.id,
        action="SESSION_CREATED",
        detail=(
            f"Loaded {len(rows)} trades — "
            f"{session_total_unmatches} unmatches ({session_critical} critical) "
            f"across {session_trades_with_unmatches} trades"
        ),
    )
    db.add(log)
    db.commit()
    db.refresh(session)
    return session


# ─── Sessions ─────────────────────────────────────────────────────────────────

@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    db: DBSession = Depends(get_db),
):
    return (
        db.query(SessionModel)
        .order_by(SessionModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(
    session_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, le=500),
    db: DBSession = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Load trades paginated (without field_comparisons — those are per-trade)
    trades = (
        db.query(TradeRecord)
        .filter(TradeRecord.session_id == session_id)
        .order_by(TradeRecord.row_number)
        .offset(skip)
        .limit(limit)
        .all()
    )
    session.trades = trades
    return session


@router.get("/sessions/{session_id}/summary", response_model=SessionSummary)
def get_session_summary(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    fcs = db.query(FieldComparison).filter(FieldComparison.session_id == session_id).all()
    return SessionSummary(
        total_trades=session.total_trades,
        trades_with_unmatches=session.trades_with_unmatches,
        total_fields=session.total_fields,
        total_unmatches=session.total_unmatches,
        critical_count=session.critical_count,
        warning_count=session.warning_count,
        info_count=sum(1 for fc in fcs if fc.severity == "INFO" and fc.result == "UNMATCH"),
        resolved_count=sum(1 for fc in fcs if fc.status == "RESOLVED"),
        pending_count=sum(1 for fc in fcs if fc.status == "PENDING"),
        match_count=sum(1 for fc in fcs if fc.result == "MATCH"),
        mirror_count=sum(1 for fc in fcs if fc.result == "MIRROR"),
        na_count=sum(1 for fc in fcs if fc.result == "NA"),
    )


@router.get("/sessions/{session_id}/activity", response_model=list[ActivityLogResponse])
def get_activity_log(session_id: int, db: DBSession = Depends(get_db)):
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.session_id == session_id)
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )


@router.post("/sessions/{session_id}/export")
def export_session(
    session_id: int,
    only_unmatches: bool = Query(default=False),
    db: DBSession = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = {
        "id": session.id,
        "filename": session.filename,
        "created_at": str(session.created_at),
        "sft_type": session.sft_type,
        "action_type": session.action_type,
        "emisor_name": session.emisor_name,
        "receptor_name": session.receptor_name,
        "total_trades": session.total_trades,
        "total_unmatches": session.total_unmatches,
        "critical_count": session.critical_count,
    }

    fcs_query = db.query(FieldComparison).filter(FieldComparison.session_id == session_id)
    if only_unmatches:
        fcs_query = fcs_query.filter(FieldComparison.result == "UNMATCH")

    field_results = [
        {
            "trade_id": fc.trade_id,
            "table_number": fc.table_number,
            "field_number": fc.field_number,
            "field_name": fc.field_name,
            "obligation": fc.obligation,
            "emisor_value": fc.emisor_value,
            "receptor_value": fc.receptor_value,
            "result": fc.result,
            "severity": fc.severity,
            "root_cause": fc.root_cause,
            "status": fc.status,
            "assignee": fc.assignee,
            "notes": fc.notes,
            "validated": fc.validated,
        }
        for fc in fcs_query.all()
    ]

    xlsx_bytes = generate_xlsx(session_data, field_results, only_unmatches)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"sftr_unmatch_{session.id}_{date_str}.xlsx"

    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Trades ───────────────────────────────────────────────────────────────────

@router.get("/trades/{trade_id}", response_model=TradeDetailResponse)
def get_trade(trade_id: int, db: DBSession = Depends(get_db)):
    trade = db.query(TradeRecord).filter(TradeRecord.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


# ─── Field Comparisons ────────────────────────────────────────────────────────

@router.patch("/field-comparisons/{fc_id}", response_model=FieldComparisonResponse)
def update_field_comparison(fc_id: int, update: FieldComparisonUpdate, db: DBSession = Depends(get_db)):
    fc = db.query(FieldComparison).filter(FieldComparison.id == fc_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Field comparison not found")

    changes = []
    if update.status is not None and update.status != fc.status:
        changes.append(f"Status: {fc.status} → {update.status}")
        fc.status = update.status
    if update.assignee is not None and update.assignee != fc.assignee:
        changes.append(f"Assignee: {fc.assignee or 'None'} → {update.assignee}")
        fc.assignee = update.assignee
    if update.notes is not None and update.notes != fc.notes:
        changes.append("Notes updated")
        fc.notes = update.notes
    if update.validated is not None and update.validated != fc.validated:
        changes.append(f"Validated: {fc.validated} → {update.validated}")
        fc.validated = update.validated

    fc.updated_at = datetime.now(timezone.utc)

    if changes:
        log = ActivityLog(
            session_id=fc.session_id,
            trade_id=fc.trade_id,
            field_comparison_id=fc.id,
            action="FIELD_UPDATED",
            detail=f"[{fc.field_name}] " + "; ".join(changes),
        )
        db.add(log)

    db.commit()
    db.refresh(fc)
    return fc


# ─── Bulk Update ──────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/bulk-update")
def bulk_update(session_id: int, req: BulkUpdateRequest, db: DBSession = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    query = db.query(FieldComparison).filter(FieldComparison.session_id == session_id)
    if req.trade_id:
        query = query.filter(FieldComparison.trade_id == req.trade_id)

    count = 0
    if req.action == "resolve_all":
        fcs = query.filter(FieldComparison.result == "UNMATCH", FieldComparison.status != "RESOLVED").all()
        for fc in fcs:
            fc.status = "RESOLVED"
            fc.updated_at = datetime.now(timezone.utc)
            count += 1

    elif req.action == "assign_critical":
        if not req.assignee:
            raise HTTPException(status_code=400, detail="Assignee required")
        fcs = query.filter(FieldComparison.severity == "CRITICAL", FieldComparison.result == "UNMATCH").all()
        for fc in fcs:
            fc.assignee = req.assignee
            fc.updated_at = datetime.now(timezone.utc)
            count += 1

    if count > 0:
        log = ActivityLog(
            session_id=session_id,
            action="BULK_UPDATE",
            detail=f"{req.action}: {count} fields updated" + (f" (assignee: {req.assignee})" if req.assignee else ""),
        )
        db.add(log)

    db.commit()
    return {"updated": count, "action": req.action}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _most_common(lst: list[str]) -> Optional[str]:
    if not lst:
        return None
    return max(set(lst), key=lst.count)
