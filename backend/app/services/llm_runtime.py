from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.config import (
    ANTHROPIC_API_KEY,
    DEFAULT_LLM_PROFILES,
    LLM_USAGE_TOKEN_LIMIT_PER_WINDOW,
    LLM_USAGE_WARNING_RATIO,
    LLM_USAGE_WINDOW_HOURS,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)
from app.models import LLMProfile, LLMUsageEvent
from app.services.demo_users import get_demo_user
from app.services.llm_provider import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)
from fastapi import HTTPException


def ensure_llm_profiles_seeded(db: DBSession) -> list[LLMProfile]:
    existing = {profile.profile_key: profile for profile in db.query(LLMProfile).all()}
    seeded: list[LLMProfile] = []

    for index, raw in enumerate(DEFAULT_LLM_PROFILES):
        profile = existing.get(raw["key"])
        if profile is None:
            profile = LLMProfile(
                profile_key=raw["key"],
                label=raw["label"],
                provider=raw["provider"],
                model=raw["model"],
                base_url=raw.get("base_url"),
                input_cost_per_million=raw.get("input_cost_per_million"),
                output_cost_per_million=raw.get("output_cost_per_million"),
                enabled=True,
                is_active=bool(raw.get("is_active")),
                sort_order=index,
            )
            db.add(profile)
            seeded.append(profile)
            continue

        profile.label = raw["label"]
        profile.provider = raw["provider"]
        profile.model = raw["model"]
        profile.base_url = raw.get("base_url")
        profile.input_cost_per_million = raw.get("input_cost_per_million")
        profile.output_cost_per_million = raw.get("output_cost_per_million")
        profile.sort_order = index
        seeded.append(profile)

    if not any(profile.is_active for profile in seeded):
        for profile in seeded:
            profile.is_active = profile.profile_key == DEFAULT_LLM_PROFILES[0]["key"]

    if sum(1 for profile in seeded if profile.is_active) > 1:
        first_active = next(profile for profile in seeded if profile.is_active)
        for profile in seeded:
            profile.is_active = profile.id == first_active.id

    db.commit()
    for profile in seeded:
        db.refresh(profile)
    return seeded


def list_llm_profiles(db: DBSession) -> list[LLMProfile]:
    ensure_llm_profiles_seeded(db)
    return db.query(LLMProfile).filter(LLMProfile.enabled == True).order_by(LLMProfile.sort_order.asc(), LLMProfile.id.asc()).all()


def get_active_profile(db: DBSession) -> LLMProfile:
    ensure_llm_profiles_seeded(db)
    profile = (
        db.query(LLMProfile)
        .filter(LLMProfile.enabled == True, LLMProfile.is_active == True)
        .order_by(LLMProfile.sort_order.asc(), LLMProfile.id.asc())
        .first()
    )
    if profile:
        return profile
    profile = db.query(LLMProfile).filter(LLMProfile.enabled == True).order_by(LLMProfile.sort_order.asc(), LLMProfile.id.asc()).first()
    if not profile:
        raise RuntimeError("No LLM profiles configured")
    profile.is_active = True
    db.commit()
    db.refresh(profile)
    return profile


def activate_profile(db: DBSession, profile_key: str) -> LLMProfile:
    ensure_llm_profiles_seeded(db)
    profiles = db.query(LLMProfile).filter(LLMProfile.enabled == True).all()
    target: Optional[LLMProfile] = None
    for profile in profiles:
        is_target = profile.profile_key == profile_key
        profile.is_active = is_target
        if is_target:
            target = profile
    if target is None:
        raise ValueError("LLM profile not found")
    db.commit()
    db.refresh(target)
    return target


def _build_provider(profile: LLMProfile) -> LLMProvider:
    if profile.provider == "anthropic":
        return AnthropicProvider(
            api_key=ANTHROPIC_API_KEY,
            model=profile.model,
        )
    if profile.provider == "openai":
        return OpenAIProvider(
            api_key=OPENAI_API_KEY,
            model=profile.model,
            base_url=profile.base_url or OPENAI_BASE_URL,
        )
    return OllamaProvider(
        base_url=profile.base_url or OLLAMA_BASE_URL,
        model=profile.model,
    )


def get_provider_for_request(db: DBSession) -> tuple[LLMProfile, LLMProvider]:
    profile = get_active_profile(db)
    provider = _build_provider(profile)
    return profile, provider


def record_usage_event(
    db: DBSession,
    profile: LLMProfile,
    provider: LLMProvider,
    feature: str,
    username: Optional[str],
) -> Optional[LLMUsageEvent]:
    usage = getattr(provider, "last_usage", None)
    if not usage:
        return None

    user = get_demo_user(username)
    normalized_username = user["username"] if user else (username or "anonymous")
    display_name = user["display_name"] if user else normalized_username

    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cached_input_tokens = int(usage.get("cached_input_tokens") or 0)

    input_cost_rate = profile.input_cost_per_million or 0.0
    output_cost_rate = profile.output_cost_per_million or 0.0

    estimated_input_cost = round((input_tokens / 1_000_000) * input_cost_rate, 6)
    estimated_output_cost = round((output_tokens / 1_000_000) * output_cost_rate, 6)
    estimated_total_cost = round(estimated_input_cost + estimated_output_cost, 6)

    event = LLMUsageEvent(
        created_at=datetime.now(timezone.utc),
        username=normalized_username,
        display_name=display_name,
        provider=profile.provider,
        model=profile.model,
        feature=feature,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        estimated_input_cost=estimated_input_cost,
        estimated_output_cost=estimated_output_cost,
        estimated_total_cost=estimated_total_cost,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_usage_limit_status(
    db: DBSession,
    username: Optional[str],
    *,
    now: Optional[datetime] = None,
) -> dict[str, object]:
    user = get_demo_user(username)
    normalized_username = user["username"] if user else (username or "anonymous")
    display_name = user["display_name"] if user else normalized_username

    current_time = now or datetime.now(timezone.utc)
    window_started_at = current_time - timedelta(hours=LLM_USAGE_WINDOW_HOURS)
    rows = (
        db.query(LLMUsageEvent)
        .filter(
            LLMUsageEvent.username == normalized_username,
            LLMUsageEvent.created_at >= window_started_at,
        )
        .all()
    )

    input_tokens_used = sum(row.input_tokens for row in rows)
    output_tokens_used = sum(row.output_tokens for row in rows)
    total_tokens_used = input_tokens_used + output_tokens_used
    remaining_tokens = max(LLM_USAGE_TOKEN_LIMIT_PER_WINDOW - total_tokens_used, 0)
    threshold_tokens = int(LLM_USAGE_TOKEN_LIMIT_PER_WINDOW * LLM_USAGE_WARNING_RATIO)
    is_blocked = total_tokens_used >= LLM_USAGE_TOKEN_LIMIT_PER_WINDOW
    is_near_limit = not is_blocked and total_tokens_used >= threshold_tokens

    alerts: list[str] = []
    if is_blocked:
        alerts.append(
            f"Límite de {LLM_USAGE_TOKEN_LIMIT_PER_WINDOW:,} tokens alcanzado en la ventana de {LLM_USAGE_WINDOW_HOURS} horas."
        )
    elif is_near_limit:
        alerts.append(
            f"Consumo alto: {total_tokens_used:,} de {LLM_USAGE_TOKEN_LIMIT_PER_WINDOW:,} tokens usados en la ventana actual."
        )

    oldest_event = min((row.created_at for row in rows), default=current_time)
    return {
        "username": normalized_username,
        "display_name": display_name,
        "window_hours": LLM_USAGE_WINDOW_HOURS,
        "token_limit": LLM_USAGE_TOKEN_LIMIT_PER_WINDOW,
        "warning_ratio": LLM_USAGE_WARNING_RATIO,
        "requests_used": len(rows),
        "input_tokens_used": input_tokens_used,
        "output_tokens_used": output_tokens_used,
        "total_tokens_used": total_tokens_used,
        "remaining_tokens": remaining_tokens,
        "total_cost": round(sum(row.estimated_total_cost for row in rows), 6),
        "window_started_at": window_started_at,
        "resets_at": oldest_event + timedelta(hours=LLM_USAGE_WINDOW_HOURS),
        "is_near_limit": is_near_limit,
        "is_blocked": is_blocked,
        "active_alerts": alerts,
    }


def enforce_usage_limit(db: DBSession, username: Optional[str]) -> dict[str, object]:
    status = get_usage_limit_status(db, username)
    if status["is_blocked"]:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Límite de consumo IA alcanzado para {status['display_name']}. "
                f"Se reactivará automáticamente tras la ventana de {status['window_hours']} horas."
            ),
        )
    return status
