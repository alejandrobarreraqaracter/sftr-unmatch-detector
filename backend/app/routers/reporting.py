from datetime import datetime
from io import BytesIO
from typing import Optional
import httpx

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import ReportingSnapshot
from app.schemas import (
    RegulatoryReportPreview,
    RegulatorySnapshotGenerateRequest,
    RegulatorySnapshotResponse,
)
from app.services.ai_agents import generate_regulatory_narrative
from app.services.llm_provider import get_provider
from app.services.regulatory_reporting import (
    build_regulatory_narrative_fallback,
    build_regulatory_report_preview,
    deserialize_snapshot_payload,
    generate_regulatory_xlsx,
    serialize_report_for_snapshot,
    snapshot_payload_to_preview,
)
from app.services.report_export import generate_pdf_report, generate_word_report_html
from app.services.report_cache import artifact_metadata, read_artifact, write_artifact
from app.config import LLM_PROVIDER, LLM_MODEL

router = APIRouter(prefix="/api/reporting", tags=["reporting"])


@router.get("/regulatory/preview", response_model=RegulatoryReportPreview)
def regulatory_preview(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_db),
):
    return build_regulatory_report_preview(db, date_from, date_to)


@router.get("/regulatory/export.xlsx")
def regulatory_export_xlsx(
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    db: DBSession = Depends(get_db),
):
    report = build_regulatory_report_preview(db, date_from, date_to)
    xlsx_bytes = generate_regulatory_xlsx(report)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"sftr_regulatory_report_{date_str}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/regulatory/generate", response_model=RegulatorySnapshotResponse)
async def regulatory_generate_snapshot(
    request: RegulatorySnapshotGenerateRequest,
    db: DBSession = Depends(get_db),
):
    report = build_regulatory_report_preview(db, request.date_from, request.date_to)
    narrative = build_regulatory_narrative_fallback(report)
    provider_name = None
    model_name = None

    if request.include_ai_narrative:
        provider = get_provider()
        try:
            narrative = await generate_regulatory_narrative(provider, report)
            provider_name = LLM_PROVIDER
            model_name = LLM_MODEL
        except httpx.HTTPError as exc:
            message = (
                f"No se pudo conectar con el proveedor IA configurado ({LLM_PROVIDER}/{LLM_MODEL}). "
                "Revisa la configuración del provider y su conectividad de red."
            )
            if LLM_PROVIDER == "ollama":
                message += (
                    " Si estás usando Docker y Ollama corre en tu máquina host, configura "
                    "`LLM_BASE_URL=http://host.docker.internal:11434` y reinicia el backend."
                )
            raise HTTPException(status_code=503, detail=message) from exc

    snapshot = ReportingSnapshot(
        report_type="REGULATORY",
        date_from=request.date_from,
        date_to=request.date_to,
        created_by=request.created_by,
        source_sessions_count=report["sessions"],
        source_trades_count=report["overview"]["total_trades"],
        source_field_comparisons_count=len(report.get("field_details", [])),
        payload_json=serialize_report_for_snapshot(report),
        narrative_markdown=narrative,
        narrative_provider=provider_name,
        narrative_model=model_name,
        report_version="v1",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return _snapshot_response(snapshot)


@router.get("/regulatory/snapshots", response_model=list[RegulatorySnapshotResponse])
def regulatory_list_snapshots(db: DBSession = Depends(get_db)):
    snapshots = (
        db.query(ReportingSnapshot)
        .filter(ReportingSnapshot.report_type == "REGULATORY")
        .order_by(ReportingSnapshot.created_at.desc())
        .limit(20)
        .all()
    )
    return [_snapshot_response(snapshot) for snapshot in snapshots]


@router.get("/regulatory/snapshots/{snapshot_id}", response_model=RegulatorySnapshotResponse)
def regulatory_get_snapshot(snapshot_id: int, db: DBSession = Depends(get_db)):
    snapshot = _get_snapshot_or_404(snapshot_id, db)
    return _snapshot_response(snapshot)


@router.get("/regulatory/snapshots/{snapshot_id}/export.xlsx")
def regulatory_snapshot_export_xlsx(snapshot_id: int, db: DBSession = Depends(get_db)):
    snapshot = _get_snapshot_or_404(snapshot_id, db)
    xlsx_bytes = read_artifact(snapshot_id, "xlsx")
    if xlsx_bytes is None:
        report = deserialize_snapshot_payload(snapshot)
        xlsx_bytes = generate_regulatory_xlsx(report)
        write_artifact(snapshot_id, "xlsx", xlsx_bytes)
    filename = f"sftr_regulatory_snapshot_{snapshot_id}.xlsx"
    return StreamingResponse(
        BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/regulatory/snapshots/{snapshot_id}/export.pdf")
def regulatory_snapshot_export_pdf(snapshot_id: int, db: DBSession = Depends(get_db)):
    snapshot = _get_snapshot_or_404(snapshot_id, db)
    pdf_bytes = read_artifact(snapshot_id, "pdf")
    if pdf_bytes is None:
        payload = deserialize_snapshot_payload(snapshot)
        narrative = snapshot.narrative_markdown or build_regulatory_narrative_fallback(payload)
        subtitle = (
            f"Rango: {snapshot.date_from or 'inicio disponible'} - {snapshot.date_to or 'fin disponible'} "
            f"| Snapshot #{snapshot.id}"
        )
        pdf_bytes = generate_pdf_report("Informe Regulatorio SFTR", subtitle, narrative)
        write_artifact(snapshot_id, "pdf", pdf_bytes)
    filename = f"sftr_regulatory_snapshot_{snapshot.id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/regulatory/snapshots/{snapshot_id}/export.doc")
def regulatory_snapshot_export_doc(snapshot_id: int, db: DBSession = Depends(get_db)):
    snapshot = _get_snapshot_or_404(snapshot_id, db)
    doc_bytes = read_artifact(snapshot_id, "doc")
    if doc_bytes is None:
        payload = deserialize_snapshot_payload(snapshot)
        narrative = snapshot.narrative_markdown or build_regulatory_narrative_fallback(payload)
        subtitle = (
            f"Rango: {snapshot.date_from or 'inicio disponible'} - {snapshot.date_to or 'fin disponible'} "
            f"| Snapshot #{snapshot.id}"
        )
        doc_bytes = generate_word_report_html("Informe Regulatorio SFTR", subtitle, narrative)
        write_artifact(snapshot_id, "doc", doc_bytes)
    filename = f"sftr_regulatory_snapshot_{snapshot.id}.doc"
    return StreamingResponse(
        BytesIO(doc_bytes),
        media_type="application/msword",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/regulatory/snapshots/{snapshot_id}/artifacts")
def regulatory_snapshot_artifacts(snapshot_id: int, db: DBSession = Depends(get_db)):
    _get_snapshot_or_404(snapshot_id, db)
    return {
        "snapshot_id": snapshot_id,
        "artifacts": [
            artifact_metadata(snapshot_id, "xlsx"),
            artifact_metadata(snapshot_id, "pdf"),
            artifact_metadata(snapshot_id, "doc"),
        ],
    }


@router.post("/regulatory/snapshots/{snapshot_id}/warm-cache")
def regulatory_snapshot_warm_cache(
    snapshot_id: int,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    snapshot = _get_snapshot_or_404(snapshot_id, db)
    background_tasks.add_task(_warm_snapshot_artifacts, snapshot.id, snapshot.date_from, snapshot.date_to, snapshot.narrative_markdown)
    return {"snapshot_id": snapshot.id, "status": "warming"}


def _get_snapshot_or_404(snapshot_id: int, db: DBSession) -> ReportingSnapshot:
    snapshot = (
        db.query(ReportingSnapshot)
        .filter(ReportingSnapshot.id == snapshot_id, ReportingSnapshot.report_type == "REGULATORY")
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Reporting snapshot not found")
    return snapshot


def _snapshot_response(snapshot: ReportingSnapshot) -> dict:
    payload = snapshot_payload_to_preview(deserialize_snapshot_payload(snapshot))
    return {
        "id": snapshot.id,
        "report_type": snapshot.report_type,
        "date_from": snapshot.date_from,
        "date_to": snapshot.date_to,
        "created_at": snapshot.created_at,
        "created_by": snapshot.created_by,
        "source_sessions_count": snapshot.source_sessions_count,
        "source_trades_count": snapshot.source_trades_count,
        "source_field_comparisons_count": snapshot.source_field_comparisons_count,
        "report_version": snapshot.report_version,
        "narrative_markdown": snapshot.narrative_markdown,
        "narrative_provider": snapshot.narrative_provider,
        "narrative_model": snapshot.narrative_model,
        "payload": payload,
    }


def _warm_snapshot_artifacts(snapshot_id: int, date_from: str | None, date_to: str | None, narrative_markdown: str | None) -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        snapshot = _get_snapshot_or_404(snapshot_id, db)
        payload = deserialize_snapshot_payload(snapshot)
        narrative = narrative_markdown or build_regulatory_narrative_fallback(payload)
        subtitle = (
            f"Rango: {date_from or 'inicio disponible'} - {date_to or 'fin disponible'} "
            f"| Snapshot #{snapshot_id}"
        )
        write_artifact(snapshot_id, "xlsx", generate_regulatory_xlsx(payload))
        write_artifact(snapshot_id, "pdf", generate_pdf_report("Informe Regulatorio SFTR", subtitle, narrative))
        write_artifact(snapshot_id, "doc", generate_word_report_html("Informe Regulatorio SFTR", subtitle, narrative))
    finally:
        db.close()
