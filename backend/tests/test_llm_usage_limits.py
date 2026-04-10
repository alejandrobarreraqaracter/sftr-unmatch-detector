from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.models import LLMUsageEvent, LLMProfile
from app.services.llm_runtime import enforce_usage_limit, get_usage_limit_status


def _seed_profile(db_session):
    profile = LLMProfile(
        profile_key="anthropic_claude_sonnet_4_6",
        label="anthropic · claude-sonnet-4-6",
        provider="anthropic",
        model="claude-sonnet-4-6",
        enabled=True,
        is_active=True,
        sort_order=0,
    )
    db_session.add(profile)
    db_session.commit()
    return profile


def test_usage_limit_status_reports_near_limit(db_session):
    _seed_profile(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(
        LLMUsageEvent(
            created_at=now - timedelta(minutes=30),
            username="alejandro.barrera",
            display_name="Alejandro Barrera",
            provider="anthropic",
            model="claude-sonnet-4-6",
            feature="analytics_chat",
            input_tokens=20000,
            output_tokens=18000,
            estimated_total_cost=0.1,
        )
    )
    db_session.commit()

    status = get_usage_limit_status(db_session, "alejandro.barrera", now=now)

    assert status["total_tokens_used"] == 38000
    assert status["is_near_limit"] is True
    assert status["is_blocked"] is False
    assert status["remaining_tokens"] == 12000
    assert status["active_alerts"]


def test_usage_limit_enforcement_blocks_when_limit_reached(db_session):
    _seed_profile(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(
        LLMUsageEvent(
            created_at=now - timedelta(minutes=15),
            username="victoria.corroto",
            display_name="Victoria Corroto",
            provider="openai",
            model="gpt-4o-mini",
            feature="analytics_report",
            input_tokens=30000,
            output_tokens=20000,
            estimated_total_cost=0.2,
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        enforce_usage_limit(db_session, "victoria.corroto")

    assert exc.value.status_code == 429
    assert "Límite de consumo IA alcanzado" in exc.value.detail
