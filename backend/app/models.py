from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sft_type = Column(String(10), nullable=True)
    action_type = Column(String(10), nullable=True)
    level = Column(String(20), nullable=True)
    emisor_name = Column(String(255), nullable=True)
    emisor_lei = Column(String(20), nullable=True)
    receptor_name = Column(String(255), nullable=True)
    receptor_lei = Column(String(20), nullable=True)
    uti = Column(String(52), nullable=True)
    total_fields = Column(Integer, default=0)
    total_unmatches = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)

    field_results = relationship("FieldResult", back_populates="session", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="session", cascade="all, delete-orphan")


class FieldResult(Base):
    __tablename__ = "field_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    table_number = Column(Integer, nullable=False)
    field_number = Column(Integer, nullable=False)
    field_name = Column(String(255), nullable=False)
    obligation = Column(String(5), nullable=True)
    emisor_value = Column(Text, nullable=True)
    receptor_value = Column(Text, nullable=True)
    result = Column(String(10), nullable=False)  # MATCH, UNMATCH, MIRROR, NA
    severity = Column(String(10), nullable=False)  # CRITICAL, WARNING, INFO, NONE
    status = Column(String(20), default="PENDING")  # PENDING, IN_NEGOTIATION, RESOLVED, EXCLUDED
    assignee = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    validated = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="field_results")
    activity_logs = relationship("ActivityLog", back_populates="field_result", cascade="all, delete-orphan")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    field_result_id = Column(Integer, ForeignKey("field_results.id"), nullable=True)
    action = Column(String(50), nullable=False)
    user = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    detail = Column(Text, nullable=True)

    session = relationship("Session", back_populates="activity_logs")
    field_result = relationship("FieldResult", back_populates="activity_logs")
