from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional

from app.database import get_db
from app.models import Session as SessionModel, FieldResult, ActivityLog
from app.schemas import (
    SessionResponse, SessionDetailResponse, SessionSummary,
    FieldResultResponse, FieldResultUpdate, ActivityLogResponse,
    BulkUpdateRequest,
)
from app.services.file_parser import parse_file
from app.services.comparison import compare_fields
from app.services.export import generate_xlsx

router = APIRouter(prefix="/api", tags=["sessions"])


@router.post("/sessions/upload", response_model=SessionResponse)
async def upload_and_compare(
    emisor_file: UploadFile = File(...),
    receptor_file: UploadFile = File(...),
    sft_type: str = Form(default="Repo"),
    action_type: str = Form(default="NEWT"),
    emisor_name: str = Form(default=""),
    receptor_name: str = Form(default=""),
    db: Session = Depends(get_db),
):
    emisor_content = await emisor_file.read()
    receptor_content = await receptor_file.read()

    emisor_data = parse_file(emisor_file.filename or "file.csv", emisor_content)
    receptor_data = parse_file(receptor_file.filename or "file.csv", receptor_content)

    results = compare_fields(emisor_data, receptor_data, sft_type, action_type)

    total_fields = len(results)
    total_unmatches = sum(1 for r in results if r["result"] == "UNMATCH")
    critical_count = sum(1 for r in results if r["severity"] == "CRITICAL")

    uti = emisor_data.get("UTI", "") or receptor_data.get("UTI", "")
    emisor_lei = emisor_data.get("Reporting counterparty", "")
    receptor_lei = receptor_data.get("Reporting counterparty", "")
    level_val = emisor_data.get("Level", "") or receptor_data.get("Level", "")

    if not emisor_name:
        emisor_name = emisor_data.get("Report submitting entity", "Emisor")
    if not receptor_name:
        receptor_name = receptor_data.get("Report submitting entity", "Receptor")

    session = SessionModel(
        sft_type=sft_type,
        action_type=action_type,
        level=level_val,
        emisor_name=emisor_name,
        emisor_lei=emisor_lei,
        receptor_name=receptor_name,
        receptor_lei=receptor_lei,
        uti=uti,
        total_fields=total_fields,
        total_unmatches=total_unmatches,
        critical_count=critical_count,
    )
    db.add(session)
    db.flush()

    for r in results:
        fr = FieldResult(
            session_id=session.id,
            table_number=r["table_number"],
            field_number=r["field_number"],
            field_name=r["field_name"],
            obligation=r["obligation"],
            emisor_value=r["emisor_value"],
            receptor_value=r["receptor_value"],
            result=r["result"],
            severity=r["severity"],
            status=r["status"],
            validated=r["validated"],
        )
        db.add(fr)

    log = ActivityLog(
        session_id=session.id,
        action="SESSION_CREATED",
        detail=f"Comparison session created with {total_unmatches} unmatches ({critical_count} critical)",
    )
    db.add(log)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(SessionModel)
        .order_by(SessionModel.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/summary", response_model=SessionSummary)
def get_session_summary(session_id: int, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    field_results = session.field_results
    return SessionSummary(
        total_fields=len(field_results),
        total_unmatches=sum(1 for fr in field_results if fr.result == "UNMATCH"),
        critical_count=sum(1 for fr in field_results if fr.severity == "CRITICAL"),
        warning_count=sum(1 for fr in field_results if fr.severity == "WARNING"),
        info_count=sum(1 for fr in field_results if fr.severity == "INFO"),
        resolved_count=sum(1 for fr in field_results if fr.status == "RESOLVED"),
        pending_count=sum(1 for fr in field_results if fr.status == "PENDING"),
        match_count=sum(1 for fr in field_results if fr.result == "MATCH"),
        mirror_count=sum(1 for fr in field_results if fr.result == "MIRROR"),
        na_count=sum(1 for fr in field_results if fr.result == "NA"),
    )


@router.get("/sessions/{session_id}/activity", response_model=list[ActivityLogResponse])
def get_activity_log(session_id: int, db: Session = Depends(get_db)):
    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.session_id == session_id)
        .order_by(ActivityLog.timestamp.desc())
        .all()
    )
    return logs


@router.patch("/fields/{field_id}", response_model=FieldResultResponse)
def update_field(field_id: int, update: FieldResultUpdate, db: Session = Depends(get_db)):
    fr = db.query(FieldResult).filter(FieldResult.id == field_id).first()
    if not fr:
        raise HTTPException(status_code=404, detail="Field result not found")

    changes = []
    if update.status is not None and update.status != fr.status:
        changes.append(f"Status: {fr.status} -> {update.status}")
        fr.status = update.status
    if update.assignee is not None and update.assignee != fr.assignee:
        changes.append(f"Assignee: {fr.assignee or 'None'} -> {update.assignee}")
        fr.assignee = update.assignee
    if update.notes is not None and update.notes != fr.notes:
        changes.append(f"Notes updated")
        fr.notes = update.notes
    if update.validated is not None and update.validated != fr.validated:
        changes.append(f"Validated: {fr.validated} -> {update.validated}")
        fr.validated = update.validated

    fr.updated_at = datetime.now(timezone.utc)

    if changes:
        log = ActivityLog(
            session_id=fr.session_id,
            field_result_id=fr.id,
            action="FIELD_UPDATED",
            detail=f"[{fr.field_name}] " + "; ".join(changes),
        )
        db.add(log)

    db.commit()
    db.refresh(fr)
    return fr


@router.post("/sessions/{session_id}/bulk-update")
def bulk_update(session_id: int, req: BulkUpdateRequest, db: Session = Depends(get_db)):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    count = 0
    if req.action == "resolve_all":
        frs = db.query(FieldResult).filter(
            FieldResult.session_id == session_id,
            FieldResult.result == "UNMATCH",
            FieldResult.status != "RESOLVED",
        ).all()
        for fr in frs:
            fr.status = "RESOLVED"
            fr.updated_at = datetime.now(timezone.utc)
            count += 1

    elif req.action == "assign_critical":
        if not req.assignee:
            raise HTTPException(status_code=400, detail="Assignee required for assign_critical")
        frs = db.query(FieldResult).filter(
            FieldResult.session_id == session_id,
            FieldResult.severity == "CRITICAL",
            FieldResult.result == "UNMATCH",
        ).all()
        for fr in frs:
            fr.assignee = req.assignee
            fr.updated_at = datetime.now(timezone.utc)
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


@router.post("/sessions/{session_id}/export")
def export_session(
    session_id: int,
    only_unmatches: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = {
        "uti": session.uti,
        "created_at": str(session.created_at),
        "sft_type": session.sft_type,
        "action_type": session.action_type,
        "emisor_name": session.emisor_name,
        "emisor_lei": session.emisor_lei,
        "receptor_name": session.receptor_name,
        "receptor_lei": session.receptor_lei,
        "total_fields": session.total_fields,
        "total_unmatches": session.total_unmatches,
        "critical_count": session.critical_count,
    }

    field_results = [
        {
            "table_number": fr.table_number,
            "field_number": fr.field_number,
            "field_name": fr.field_name,
            "obligation": fr.obligation,
            "emisor_value": fr.emisor_value,
            "receptor_value": fr.receptor_value,
            "result": fr.result,
            "severity": fr.severity,
            "status": fr.status,
            "assignee": fr.assignee,
            "notes": fr.notes,
            "validated": fr.validated,
        }
        for fr in session.field_results
    ]

    xlsx_bytes = generate_xlsx(session_data, field_results, only_unmatches)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"sftr_unmatch_{session.uti or 'report'}_{date_str}.xlsx"

    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
