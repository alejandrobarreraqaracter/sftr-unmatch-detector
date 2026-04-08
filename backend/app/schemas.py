from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ─── Field Comparison ────────────────────────────────────────────────────────

class FieldComparisonResponse(BaseModel):
    id: int
    trade_id: int
    session_id: int
    table_number: int
    field_number: int
    field_name: str
    obligation: Optional[str] = None
    emisor_value: Optional[str] = None
    receptor_value: Optional[str] = None
    result: str
    severity: str
    root_cause: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    notes: Optional[str] = None
    validated: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FieldComparisonUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    validated: Optional[bool] = None


# ─── Trade Record ─────────────────────────────────────────────────────────────

class TradeRecordResponse(BaseModel):
    id: int
    session_id: int
    row_number: int
    uti: Optional[str] = None
    sft_type: Optional[str] = None
    action_type: Optional[str] = None
    emisor_lei: Optional[str] = None
    receptor_lei: Optional[str] = None
    total_fields: int
    total_unmatches: int
    critical_count: int
    warning_count: int
    has_unmatches: bool

    class Config:
        from_attributes = True


class TradeDetailResponse(TradeRecordResponse):
    field_comparisons: list[FieldComparisonResponse] = []


# ─── Session ─────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    sft_type: Optional[str] = None
    action_type: Optional[str] = None
    emisor_name: Optional[str] = None
    receptor_name: Optional[str] = None
    filename: Optional[str] = None
    total_trades: int
    total_fields: int
    total_unmatches: int
    critical_count: int
    warning_count: int
    trades_with_unmatches: int

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    trades: list[TradeRecordResponse] = []


class SessionSummary(BaseModel):
    total_trades: int
    trades_with_unmatches: int
    total_fields: int
    total_unmatches: int
    critical_count: int
    warning_count: int
    info_count: int
    resolved_count: int
    pending_count: int
    match_count: int
    mirror_count: int
    na_count: int


# ─── Activity Log ─────────────────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    id: int
    session_id: int
    trade_id: Optional[int] = None
    field_comparison_id: Optional[int] = None
    action: str
    user: Optional[str] = None
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Analytics ────────────────────────────────────────────────────────────────

class TopFieldItem(BaseModel):
    field_name: str
    table_number: int
    count: int


class TrendItem(BaseModel):
    date: str
    total_unmatches: int
    critical_count: int
    sessions: int


# ─── Bulk Update ─────────────────────────────────────────────────────────────

class BulkUpdateRequest(BaseModel):
    action: str          # "resolve_all", "assign_critical"
    assignee: Optional[str] = None
    trade_id: Optional[int] = None   # if set, scope to one trade; else whole session
