from __future__ import annotations

import json
from sqlite3 import Connection

from app.services.ai_client import load_prompt, request_json


def summarize_daily_review(connection: Connection, review_payload: dict) -> dict:
    tasks = rows_to_dicts(
        connection.execute(
            """
            SELECT tasks.*
            FROM tasks
            JOIN daily_plans ON daily_plans.id = tasks.daily_plan_id
            WHERE daily_plans.id = COALESCE(?, daily_plans.id)
              AND daily_plans.plan_date = ?
            ORDER BY tasks.id
            """,
            (review_payload.get("plan_id"), review_payload["review_date"]),
        ).fetchall()
    )
    memories = rows_to_dicts(
        connection.execute(
            "SELECT * FROM mentor_memories ORDER BY weight DESC, updated_at DESC LIMIT 16"
        ).fetchall()
    )
    recent_reviews = rows_to_dicts(
        connection.execute("SELECT * FROM daily_reviews ORDER BY review_date DESC LIMIT 7").fetchall()
    )
    recent_writing = rows_to_dicts(
        connection.execute(
            """
            SELECT created_at, task_type, estimated_band, feedback_json
            FROM writing_submissions
            ORDER BY created_at DESC
            LIMIT 5
            """
        ).fetchall()
    )
    profile = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()

    payload = {
        "profile": dict(profile) if profile else {},
        "review": review_payload,
        "today_tasks": tasks,
        "task_reviews": review_payload.get("task_reviews", []),
        "recent_reviews": recent_reviews,
        "recent_writing": recent_writing,
        "mentor_memories": memories,
        "output_schema": {
            "summary": "中文字符串",
            "completion_analysis": "中文字符串",
            "dimension_insights": [{"dimension": "维度名", "insight": "中文字符串"}],
            "task_insights": [{"task_id": "整数", "insight": "中文字符串"}],
            "new_weaknesses": [{"category": "分类名", "description": "中文字符串", "evidence": "证据", "severity": "整数"}],
            "memory_updates": [{"memory_type": "类型名", "title": "中文标题", "content": "中文内容", "evidence": "证据", "weight": "整数"}],
            "tomorrow_adjustment": "中文字符串",
            "mentor_insight": "中文字符串",
            "coach_note": "中文字符串",
        },
        "language": "所有解释性内容必须使用简体中文。",
    }

    return request_json(load_prompt("mentor_daily_review.md"), payload)


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]

