from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FieldResultResponse(BaseModel):
    id: int
    session_id: int
    table_number: int
    field_number: int
    field_name: str
    obligation: Optional[str] = None
    emisor_value: Optional[str] = None
    receptor_value: Optional[str] = None
    result: str
    severity: str
    status: str
    assignee: Optional[str] = None
    notes: Optional[str] = None
    validated: bool
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FieldResultUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None
    validated: Optional[bool] = None


class SessionResponse(BaseModel):
    id: int
    created_at: Optional[datetime] = None
    sft_type: Optional[str] = None
    action_type: Optional[str] = None
    level: Optional[str] = None
    emisor_name: Optional[str] = None
    emisor_lei: Optional[str] = None
    receptor_name: Optional[str] = None
    receptor_lei: Optional[str] = None
    uti: Optional[str] = None
    total_fields: int
    total_unmatches: int
    critical_count: int

    class Config:
        from_attributes = True


class SessionDetailResponse(SessionResponse):
    field_results: list[FieldResultResponse] = []


class SessionSummary(BaseModel):
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


class ActivityLogResponse(BaseModel):
    id: int
    session_id: int
    field_result_id: Optional[int] = None
    action: str
    user: Optional[str] = None
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None

    class Config:
        from_attributes = True


class TopFieldItem(BaseModel):
    field_name: str
    table_number: int
    count: int


class TrendItem(BaseModel):
    date: str
    total_unmatches: int
    critical_count: int
    sessions: int


class BulkUpdateRequest(BaseModel):
    action: str  # "resolve_all", "assign_critical"
    assignee: Optional[str] = None
