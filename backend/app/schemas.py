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
    difference_value: Optional[float] = None
    difference_unit: Optional[str] = None
    difference_display: Optional[str] = None
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
    pairing_status: Optional[str] = None   # UNPAIR | UNMATCH | None
    pairing_reason: Optional[str] = None   # UTI | Other counterparty | UTI, Other counterparty

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
    product_type: str = "sftr"
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


class ReprocessSessionResponse(BaseModel):
    session_id: int
    trades_reprocessed: int
    fields_reprocessed: int
    total_unmatches: int
    critical_count: int
    warning_count: int


class DemoUserResponse(BaseModel):
    username: str
    display_name: str


class LLMProfileResponse(BaseModel):
    id: int
    profile_key: str
    label: str
    provider: str
    model: str
    base_url: Optional[str] = None
    input_cost_per_million: Optional[float] = None
    output_cost_per_million: Optional[float] = None
    enabled: bool
    is_active: bool
    sort_order: int

    class Config:
        from_attributes = True


class ActivateLLMProfileRequest(BaseModel):
    profile_key: str


class LLMUsageOverview(BaseModel):
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_input_tokens: int
    total_cost: float
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class LLMUsageDailyItem(BaseModel):
    date: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_cost: float


class LLMUsageByUserItem(BaseModel):
    username: str
    display_name: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_cost: float


class LLMUsageByModelItem(BaseModel):
    provider: str
    model: str
    requests: int
    input_tokens: int
    output_tokens: int
    total_cost: float


# ─── Regulatory Reporting ────────────────────────────────────────────────────

class RegulatoryTopFieldItem(BaseModel):
    field_name: str
    table_number: int
    count: int
    critical_count: int
    warning_count: int


class RegulatoryOpenItem(BaseModel):
    business_date: str
    session_id: int
    trade_id: int
    row_number: int
    uti: Optional[str] = None
    field_name: str
    table_number: int
    field_number: int
    severity: str
    status: str
    assignee: Optional[str] = None
    root_cause: Optional[str] = None
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None


class RegulatoryDaySummary(BaseModel):
    date: str
    sessions: int
    total_trades: int
    trades_with_unmatches: int
    unpair_trades: int
    total_unmatches: int
    critical_count: int
    warning_count: int
    resolved_fields: int
    pending_fields: int


class RegulatoryCounterpartyItem(BaseModel):
    emisor_name: str
    receptor_name: str
    sessions: int
    total_trades: int
    total_unmatches: int
    critical_count: int


class RegulatoryTradeSummary(BaseModel):
    business_date: str
    session_id: int
    trade_id: int
    row_number: int
    uti: Optional[str] = None
    sft_type: Optional[str] = None
    action_type: Optional[str] = None
    emisor_name: Optional[str] = None
    receptor_name: Optional[str] = None
    pairing_status: str
    pairing_reason: Optional[str] = None
    total_fields: int
    total_unmatches: int
    critical_count: int
    warning_count: int
    has_unmatches: bool


class RegulatoryFieldDetail(BaseModel):
    business_date: str
    session_id: int
    trade_id: int
    row_number: int
    uti: Optional[str] = None
    sft_type: Optional[str] = None
    action_type: Optional[str] = None
    pairing_status: str
    pairing_reason: Optional[str] = None
    field_name: str
    table_number: int
    field_number: int
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


class RegulatoryReportPreview(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    product_type: str = "sftr"
    generated_at: datetime
    sessions: int
    filenames: list[str]
    overview: dict
    daily_summary: list[RegulatoryDaySummary]
    top_fields: list[RegulatoryTopFieldItem]
    top_counterparties: list[RegulatoryCounterpartyItem]
    open_items_count: int
    critical_open_items_count: int
    open_items: list[RegulatoryOpenItem]
    comparison_to_previous_period: Optional[dict] = None
    risk_residual: Optional[dict] = None


class RegulatorySnapshotGenerateRequest(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    product_type: str = "sftr"
    include_ai_narrative: bool = False
    created_by: Optional[str] = None


class RegulatorySnapshotResponse(BaseModel):
    id: int
    report_type: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None
    source_sessions_count: int
    source_trades_count: int
    source_field_comparisons_count: int
    report_version: str
    narrative_markdown: Optional[str] = None
    narrative_provider: Optional[str] = None
    narrative_model: Optional[str] = None
    payload: RegulatoryReportPreview
