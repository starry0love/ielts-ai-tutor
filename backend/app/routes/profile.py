from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.db import get_connection
from app.schemas import AIConfigUpdate, Profile
from app.services.ai_client import AIUnavailableError, get_client_config, is_ai_configured, test_client_config


router = APIRouter()


@router.get("/ai-status")
def get_ai_status() -> dict:
    config = get_client_config()
    return {
        "provider": config["provider"],
        "base_url": config["base_url"],
        "model": config["model"],
        "configured": is_ai_configured(),
    }


@router.put("/ai-config")
def update_ai_config(config: AIConfigUpdate) -> dict:
    test_ai_config(config)
    env_path = get_env_path()
    values = read_env_values(env_path)
    values.update(
        {
            "AI_PROVIDER": config.provider or "openai-compatible",
            "AI_API_KEY": config.api_key,
            "AI_BASE_URL": config.base_url,
            "AI_MODEL": config.model,
            "AI_TIMEOUT_SECONDS": str(config.timeout_seconds),
            "AI_MAX_TOKENS": str(config.max_tokens),
        }
    )
    write_env_values(env_path, values)
    os.environ.update(values)
    return get_ai_status()


@router.post("/ai-test")
def test_ai_config(config: AIConfigUpdate) -> dict:
    try:
        return test_client_config(
            {
                "api_key": config.api_key,
                "base_url": config.base_url,
                "model": config.model,
                "timeout_seconds": config.timeout_seconds,
            }
        )
    except AIUnavailableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def get_profile() -> dict:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()
        return normalise_profile(dict(row))


@router.put("")
def update_profile(profile: Profile) -> dict:
    onboarding_summary = profile.onboarding_summary or build_onboarding_summary(profile)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET target_band = ?,
                exam_date = ?,
                daily_available_minutes = ?,
                current_level_notes = ?,
                mentor_style = ?,
                onboarding_completed = ?,
                goal_notes = ?,
                study_methods = ?,
                study_history = ?,
                baseline_notes = ?,
                learning_preferences = ?,
                onboarding_summary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (
                profile.target_band,
                profile.exam_date,
                profile.daily_available_minutes,
                profile.current_level_notes,
                profile.mentor_style,
                1 if profile.onboarding_completed else 0,
                profile.goal_notes,
                profile.study_methods,
                profile.study_history,
                profile.baseline_notes,
                profile.learning_preferences,
                onboarding_summary,
            ),
        )
        upsert_onboarding_memories(connection, profile, onboarding_summary)
        row = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()
        return normalise_profile(dict(row))


def normalise_profile(row: dict) -> dict:
    row["onboarding_completed"] = bool(row.get("onboarding_completed"))
    return row


def build_onboarding_summary(profile: Profile) -> str:
    parts = [
        f"目标分数：{profile.target_band}",
        f"考试日期：{profile.exam_date or '未确定'}",
        f"每日可用时间：{profile.daily_available_minutes} 分钟",
        f"目标与动机：{profile.goal_notes or '未填写'}",
        f"当前基础：{profile.baseline_notes or '未填写'}",
        f"学习经历：{profile.study_history or '未填写'}",
        f"学习方法：{profile.study_methods or '未填写'}",
        f"学习偏好：{profile.learning_preferences or '未填写'}",
    ]
    return "\n".join(parts)


def upsert_onboarding_memories(connection, profile: Profile, summary: str) -> None:
    if not profile.onboarding_completed:
        return
    memories = [
        ("profile", "入门画像", summary, "onboarding", 5),
        ("goal", "目标与动机", profile.goal_notes or "", "onboarding", 4),
        ("baseline", "当前基础", profile.baseline_notes or "", "onboarding", 4),
        ("method", "学习方法", profile.study_methods or "", "onboarding", 3),
        ("preference", "学习偏好", profile.learning_preferences or "", "onboarding", 3),
    ]
    for memory_type, title, content, evidence, weight in memories:
        content = content.strip()
        if not content:
            continue
        existing = connection.execute(
            "SELECT id FROM mentor_memories WHERE memory_type = ? AND title = ? LIMIT 1",
            (memory_type, title),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE mentor_memories
                SET content = ?, evidence = ?, weight = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (content, evidence, weight, existing["id"]),
            )
        else:
            connection.execute(
                """
                INSERT INTO mentor_memories (memory_type, title, content, evidence, weight)
                VALUES (?, ?, ?, ?, ?)
                """,
                (memory_type, title, content, evidence, weight),
            )


def get_env_path() -> Path:
    configured_path = os.getenv("IELTS_TUTOR_ENV_PATH")
    if configured_path:
        return Path(configured_path)
    return Path(__file__).resolve().parents[3] / ".env"


def read_env_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def write_env_values(path: Path, values: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered_keys = [
        "AI_PROVIDER",
        "AI_API_KEY",
        "AI_BASE_URL",
        "AI_MODEL",
        "AI_TIMEOUT_SECONDS",
        "AI_MAX_TOKENS",
        "DATABASE_URL",
    ]
    lines: list[str] = []
    for key in ordered_keys:
        if key in values and values[key] is not None:
            lines.append(f"{key}={values[key]}")
    for key in sorted(set(values) - set(ordered_keys)):
        lines.append(f"{key}={values[key]}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
