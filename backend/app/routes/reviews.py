from __future__ import annotations

import json

from fastapi import APIRouter

from app.db import get_connection
from app.schemas import DailyReviewCreate
from app.services.review_service import summarize_daily_review


router = APIRouter()


@router.post("/daily")
def create_daily_review(review: DailyReviewCreate) -> dict:
    review_payload = review.model_dump()
    with get_connection() as connection:
        enrich_task_reviews(connection, review_payload)
        summary = summarize_daily_review(connection, review_payload)
        connection.execute(
            """
            INSERT INTO daily_reviews (
                review_date,
                plan_id,
                total_minutes,
                energy_level,
                mood,
                focus_level,
                completion_level,
                hardest_part,
                unfinished_reason,
                dimensions_json,
                task_reviews_json,
                module_reflections_json,
                blockers_json,
                wins,
                tomorrow_preference,
                message_to_mentor,
                ai_summary,
                tomorrow_adjustment,
                mentor_insight,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(review_date) DO UPDATE SET
                plan_id = excluded.plan_id,
                total_minutes = excluded.total_minutes,
                energy_level = excluded.energy_level,
                mood = excluded.mood,
                focus_level = excluded.focus_level,
                completion_level = excluded.completion_level,
                hardest_part = excluded.hardest_part,
                unfinished_reason = excluded.unfinished_reason,
                dimensions_json = excluded.dimensions_json,
                task_reviews_json = excluded.task_reviews_json,
                module_reflections_json = excluded.module_reflections_json,
                blockers_json = excluded.blockers_json,
                wins = excluded.wins,
                tomorrow_preference = excluded.tomorrow_preference,
                message_to_mentor = excluded.message_to_mentor,
                ai_summary = excluded.ai_summary,
                tomorrow_adjustment = excluded.tomorrow_adjustment,
                mentor_insight = excluded.mentor_insight,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                review.review_date,
                review.plan_id,
                review.total_minutes,
                review.energy_level,
                review.mood,
                review.focus_level,
                review.completion_level,
                review.hardest_part,
                review.unfinished_reason,
                json.dumps(review_payload.get("dimensions", []), ensure_ascii=False),
                json.dumps(review_payload.get("task_reviews", []), ensure_ascii=False),
                json.dumps(review_payload.get("module_reflections", []), ensure_ascii=False),
                json.dumps(review_payload.get("blockers", []), ensure_ascii=False),
                review.wins,
                review.tomorrow_preference,
                review.message_to_mentor,
                json.dumps(summary, ensure_ascii=False),
                summary.get("tomorrow_adjustment"),
                summary.get("mentor_insight") or summary.get("coach_note"),
            ),
        )
        row = connection.execute(
            "SELECT * FROM daily_reviews WHERE review_date = ?",
            (review.review_date,),
        ).fetchone()
        review_id = row["id"]
        replace_task_reviews(connection, review_id, review_payload.get("task_reviews", []))
        update_tasks_from_review(connection, review_payload.get("task_reviews", []))
        insert_weaknesses(connection, summary)
        upsert_memory_updates(connection, summary)
        result = hydrate_review(dict(row))
        result["summary"] = summary
        return result


@router.get("/recent")
def recent_reviews() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM daily_reviews ORDER BY review_date DESC LIMIT 14"
        ).fetchall()
        return [hydrate_review(dict(row)) for row in rows]


def enrich_task_reviews(connection, payload: dict) -> None:
    task_reviews = payload.get("task_reviews") or []
    if task_reviews or not payload.get("plan_id"):
        return
    tasks = connection.execute(
        "SELECT id FROM tasks WHERE daily_plan_id = ? ORDER BY id",
        (payload["plan_id"],),
    ).fetchall()
    payload["task_reviews"] = [
        {"task_id": row["id"], "status": "pending", "actual_minutes": 0, "difficulty": None, "quality": 3}
        for row in tasks
    ]


def replace_task_reviews(connection, review_id: int, task_reviews: list[dict]) -> None:
    connection.execute("DELETE FROM task_reviews WHERE daily_review_id = ?", (review_id,))
    for item in task_reviews:
        connection.execute(
            """
            INSERT INTO task_reviews (
                daily_review_id,
                task_id,
                status,
                actual_minutes,
                difficulty,
                quality,
                outcome,
                blocker,
                next_action
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                item.get("task_id"),
                item.get("status") or "pending",
                int(item.get("actual_minutes") or 0),
                item.get("difficulty"),
                int(item.get("quality") or 3),
                item.get("outcome"),
                item.get("blocker"),
                item.get("next_action"),
            ),
        )


def update_tasks_from_review(connection, task_reviews: list[dict]) -> None:
    for item in task_reviews:
        connection.execute(
            """
            UPDATE tasks
            SET status = ?,
                actual_minutes = ?,
                difficulty = ?,
                incomplete_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                item.get("status") or "pending",
                int(item.get("actual_minutes") or 0),
                item.get("difficulty"),
                item.get("blocker"),
                item.get("task_id"),
            ),
        )


def insert_weaknesses(connection, summary: dict) -> None:
    for weakness in summary.get("new_weaknesses", [])[:8]:
        connection.execute(
            """
            INSERT INTO weaknesses (
                category,
                description,
                evidence,
                severity,
                last_seen_at,
                updated_at
            ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (
                weakness.get("category", "Focus"),
                weakness.get("description", "Review signal"),
                weakness.get("evidence"),
                int(weakness.get("severity", 1) or 1),
            ),
        )


def upsert_memory_updates(connection, summary: dict) -> None:
    for memory in summary.get("memory_updates", [])[:10]:
        title = str(memory.get("title") or "").strip()
        content = str(memory.get("content") or "").strip()
        memory_type = str(memory.get("memory_type") or "pattern").strip()
        if not title or not content:
            continue
        existing = connection.execute(
            """
            SELECT id, weight
            FROM mentor_memories
            WHERE title = ? AND memory_type = ?
            LIMIT 1
            """,
            (title, memory_type),
        ).fetchone()
        if existing:
            connection.execute(
                """
                UPDATE mentor_memories
                SET content = ?,
                    evidence = ?,
                    weight = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    content,
                    memory.get("evidence"),
                    max(int(existing["weight"] or 1), int(memory.get("weight", 1) or 1)),
                    existing["id"],
                ),
            )
            continue
        connection.execute(
            """
            INSERT INTO mentor_memories (
                memory_type,
                title,
                content,
                evidence,
                weight
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                memory_type,
                title,
                content,
                memory.get("evidence"),
                int(memory.get("weight", 1) or 1),
            ),
        )


def hydrate_review(row: dict) -> dict:
    row["dimensions"] = parse_json(row.get("dimensions_json"), [])
    row["task_reviews"] = parse_json(row.get("task_reviews_json"), [])
    row["module_reflections"] = parse_json(row.get("module_reflections_json"), [])
    row["blockers"] = parse_json(row.get("blockers_json"), [])
    row["summary"] = parse_json(row.get("ai_summary"), {})
    return row


def parse_json(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback
