from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sft_type = Column(String(10), nullable=True)        # predominant SFT type or mixed
    action_type = Column(String(10), nullable=True)     # predominant action type or mixed
    emisor_name = Column(String(255), nullable=True)
    receptor_name = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=True)
    product_type = Column(String(30), nullable=False, default="sftr")

    total_trades = Column(Integer, default=0)
    total_fields = Column(Integer, default=0)           # sum of compared fields across all trades
    total_unmatches = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    trades_with_unmatches = Column(Integer, default=0)

    trades = relationship("TradeRecord", back_populates="session", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="session", cascade="all, delete-orphan")


class TradeRecord(Base):
    __tablename__ = "trade_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)        # original row in the CSV
    uti = Column(String(52), nullable=True, index=True)
    sft_type = Column(String(10), nullable=True)
    action_type = Column(String(10), nullable=True)
    emisor_lei = Column(String(20), nullable=True)
    receptor_lei = Column(String(20), nullable=True)

    total_fields = Column(Integer, default=0)
    total_unmatches = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    has_unmatches = Column(Boolean, default=False)

    session = relationship("Session", back_populates="trades")
    field_comparisons = relationship("FieldComparison", back_populates="trade", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="trade")


class FieldComparison(Base):
    __tablename__ = "field_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    trade_id = Column(Integer, ForeignKey("trade_records.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    table_number = Column(Integer, nullable=False)
    field_number = Column(Integer, nullable=False)
    field_name = Column(String(255), nullable=False)
    obligation = Column(String(5), nullable=True)
    emisor_value = Column(Text, nullable=True)
    receptor_value = Column(Text, nullable=True)
    difference_value = Column(Float, nullable=True)
    difference_unit = Column(String(20), nullable=True)
    difference_display = Column(String(255), nullable=True)
    result = Column(String(10), nullable=False)         # MATCH, UNMATCH, MIRROR, NA
    severity = Column(String(10), nullable=False)       # CRITICAL, WARNING, INFO, NONE
    root_cause = Column(String(30), nullable=True)      # MISSING_EMISOR, MISSING_RECEPTOR, NUMERIC_DELTA, VALUE_MISMATCH, etc.
    status = Column(String(20), default="PENDING")      # PENDING, IN_NEGOTIATION, RESOLVED, EXCLUDED
    assignee = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    validated = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    trade = relationship("TradeRecord", back_populates="field_comparisons")
    activity_logs = relationship("ActivityLog", back_populates="field_comparison", cascade="all, delete-orphan")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    trade_id = Column(Integer, ForeignKey("trade_records.id"), nullable=True)
    field_comparison_id = Column(Integer, ForeignKey("field_comparisons.id"), nullable=True)
    action = Column(String(50), nullable=False)
    user = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    detail = Column(Text, nullable=True)

    session = relationship("Session", back_populates="activity_logs")
    trade = relationship("TradeRecord", back_populates="activity_logs")
    field_comparison = relationship("FieldComparison", back_populates="activity_logs")


class ReportingSnapshot(Base):
    __tablename__ = "reporting_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), nullable=False, default="REGULATORY")
    date_from = Column(String(10), nullable=True)
    date_to = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String(255), nullable=True)
    source_sessions_count = Column(Integer, default=0)
    source_trades_count = Column(Integer, default=0)
    source_field_comparisons_count = Column(Integer, default=0)
    payload_json = Column(Text, nullable=False)
    narrative_markdown = Column(Text, nullable=True)
    narrative_provider = Column(String(50), nullable=True)
    narrative_model = Column(String(100), nullable=True)
    report_version = Column(String(20), nullable=False, default="v1")


class LLMProfile(Base):
    __tablename__ = "llm_profiles"

    id = Column(Integer, primary_key=True, index=True)
    profile_key = Column(String(100), nullable=False, unique=True, index=True)
    label = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    model = Column(String(100), nullable=False)
    base_url = Column(String(255), nullable=True)
    input_cost_per_million = Column(Float, nullable=True)
    output_cost_per_million = Column(Float, nullable=True)
    enabled = Column(Boolean, default=True)
    is_active = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)


class LLMUsageEvent(Base):
    __tablename__ = "llm_usage_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    username = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    feature = Column(String(100), nullable=False, index=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cached_input_tokens = Column(Integer, default=0)
    estimated_input_cost = Column(Float, default=0.0)
    estimated_output_cost = Column(Float, default=0.0)
    estimated_total_cost = Column(Float, default=0.0)
