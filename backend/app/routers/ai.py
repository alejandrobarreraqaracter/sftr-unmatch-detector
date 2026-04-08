from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func

from app.database import get_db
from app.models import Session as SessionModel, TradeRecord, FieldComparison
from app.services.llm_provider import get_provider
from app.services.ai_agents import analyze_field, analyze_trade, generate_session_narrative
from app.config import LLM_PROVIDER, LLM_MODEL

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
async def ai_status():
    """Check which AI provider is active and whether it's reachable."""
    provider = get_provider()
    available = await provider.is_available()
    return {
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "available": available,
    }


@router.post("/field-comparisons/{fc_id}/analyze")
async def analyze_field_comparison(fc_id: int, db: DBSession = Depends(get_db)):
    """Agent 1: Analyze a single field discrepancy."""
    fc = db.query(FieldComparison).filter(FieldComparison.id == fc_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Field comparison not found")
    if fc.result != "UNMATCH":
        raise HTTPException(status_code=400, detail="Field is not an unmatch")

    trade = db.query(TradeRecord).filter(TradeRecord.id == fc.trade_id).first()

    provider = get_provider()
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
    return {"field_id": fc_id, "field_name": fc.field_name, **result}


@router.post("/trades/{trade_id}/analyze")
async def analyze_trade_endpoint(trade_id: int, db: DBSession = Depends(get_db)):
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

    provider = get_provider()
    result = await analyze_trade(
        provider=provider,
        uti=trade.uti or f"Trade #{trade.row_number}",
        sft_type=trade.sft_type or "Repo",
        action_type=trade.action_type or "NEWT",
        unmatches=unmatches,
    )
    return {"trade_id": trade_id, "uti": trade.uti, **result}


@router.post("/sessions/{session_id}/narrative")
async def session_narrative(session_id: int, db: DBSession = Depends(get_db)):
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

    provider = get_provider()
    narrative = await generate_session_narrative(provider, session_data, top_fields, sample_trades)
    return {
        "session_id": session_id,
        "provider": LLM_PROVIDER,
        "model": LLM_MODEL,
        "narrative": narrative,
    }
