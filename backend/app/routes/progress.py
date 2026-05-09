from __future__ import annotations

from datetime import date, timedelta
import json

from fastapi import APIRouter

from app.db import DIMENSIONS, get_connection


router = APIRouter()


@router.get("/summary")
def progress_summary() -> dict:
    with get_connection() as connection:
        reviews = rows_to_dicts(connection.execute("SELECT * FROM daily_reviews ORDER BY review_date").fetchall())
        task_reviews = rows_to_dicts(
            connection.execute(
                """
                SELECT task_reviews.*, tasks.module, tasks.title, daily_reviews.review_date
                FROM task_reviews
                JOIN tasks ON tasks.id = task_reviews.task_id
                JOIN daily_reviews ON daily_reviews.id = task_reviews.daily_review_id
                ORDER BY daily_reviews.review_date
                """
            ).fetchall()
        )
        total_minutes = sum(int(row.get("total_minutes") or 0) for row in reviews)
        review_dates = [row["review_date"] for row in reviews]
        task_status = task_status_counts(connection)
        recent_task_status = task_status_counts(connection, days=7)
        total_tasks = sum(task_status.values())
        completed_tasks = task_status.get("completed", 0)
        recent_total = sum(recent_task_status.values())
        recent_completed = recent_task_status.get("completed", 0)
        writing_rows = rows_to_dicts(
            connection.execute(
                """
                SELECT created_at, task_type, estimated_band, task_response_score, coherence_score, lexical_score, grammar_score, feedback_json
                FROM writing_submissions
                ORDER BY created_at
                """
            ).fetchall()
        )
        weaknesses = rows_to_dicts(
            connection.execute("SELECT * FROM weaknesses ORDER BY severity DESC, last_seen_at DESC LIMIT 8").fetchall()
        )
        latest_review = reviews[-1] if reviews else None
        latest_summary = parse_json(latest_review.get("ai_summary") if latest_review else None, {})
        dimension_summary = build_dimension_summary(reviews)
        task_quality = build_task_quality(task_reviews)
        priority_focus = pick_priority_focus(dimension_summary, weaknesses, latest_summary, task_quality)

        return {
            "total_minutes": total_minutes,
            "study_days": len(set(review_dates)),
            "current_streak": calculate_current_streak(review_dates),
            "recent_minutes": [
                {"review_date": row["review_date"], "total_minutes": row.get("total_minutes", 0)}
                for row in reviews[-7:]
            ],
            "task_status": task_status,
            "completion_rate": completed_tasks / total_tasks if total_tasks else 0,
            "completion_rate_7d": recent_completed / recent_total if recent_total else 0,
            "module_minutes": module_minutes_from_task_reviews(task_reviews),
            "task_quality": task_quality,
            "writing_trend": writing_rows,
            "weaknesses": weaknesses,
            "dimension_summary": dimension_summary,
            "latest_review_summary": latest_summary.get("summary") or (latest_review or {}).get("mentor_insight"),
            "tomorrow_adjustment": latest_summary.get("tomorrow_adjustment") or (latest_review or {}).get("tomorrow_adjustment"),
            "priority_focus": priority_focus,
            "level_analysis": {
                "estimated_band": latest_writing_band(writing_rows),
                "summary": "导师版通过入门画像、今日计划、任务级复盘和写作反馈判断趋势。",
                "weakest_module": priority_focus,
                "recommendation": latest_summary.get("tomorrow_adjustment") or "先保持计划-执行-复盘的闭环。",
                "scores": {item["dimension"]: item["average"] for item in dimension_summary},
            },
        }


def task_status_counts(connection, days: int | None = None) -> dict[str, int]:
    if days is None:
        rows = connection.execute("SELECT status, COUNT(*) AS count FROM tasks GROUP BY status").fetchall()
    else:
        rows = connection.execute(
            """
            SELECT tasks.status, COUNT(*) AS count
            FROM tasks
            JOIN daily_plans ON daily_plans.id = tasks.daily_plan_id
            WHERE daily_plans.plan_date >= date('now', ?)
            GROUP BY tasks.status
            """,
            (f"-{days - 1} days",),
        ).fetchall()
    return {row["status"]: row["count"] for row in rows}


def build_dimension_summary(reviews: list[dict]) -> list[dict]:
    scores: dict[str, list[int]] = {dimension: [] for dimension in DIMENSIONS}
    notes: dict[str, list[str]] = {dimension: [] for dimension in DIMENSIONS}
    for review in reviews:
        for item in parse_json(review.get("dimensions_json"), []):
            dimension = item.get("dimension")
            score = item.get("score")
            if dimension in scores and isinstance(score, int):
                scores[dimension].append(score)
                if item.get("note"):
                    notes[dimension].append(item["note"])
    return [
        {
            "dimension": dimension,
            "average": round(sum(values) / len(values), 2) if values else None,
            "count": len(values),
            "latest_note": notes[dimension][-1] if notes[dimension] else None,
        }
        for dimension, values in scores.items()
    ]


def build_task_quality(task_reviews: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in task_reviews:
        grouped.setdefault(row["module"], []).append(row)
    result = []
    for module, rows in grouped.items():
        completed = sum(1 for row in rows if row["status"] == "completed")
        minutes = sum(int(row.get("actual_minutes") or 0) for row in rows)
        quality_values = [int(row.get("quality") or 3) for row in rows]
        blockers = [row["blocker"] for row in rows if row.get("blocker")]
        result.append(
            {
                "module": module,
                "reviews": len(rows),
                "completed": completed,
                "completion_rate": completed / len(rows) if rows else 0,
                "minutes": minutes,
                "average_quality": round(sum(quality_values) / len(quality_values), 2) if quality_values else None,
                "latest_blocker": blockers[-1] if blockers else None,
            }
        )
    return sorted(result, key=lambda item: item["minutes"], reverse=True)


def module_minutes_from_task_reviews(task_reviews: list[dict]) -> list[dict]:
    quality = build_task_quality(task_reviews)
    return [{"module": item["module"], "minutes": item["minutes"]} for item in quality]


def pick_priority_focus(dimension_summary: list[dict], weaknesses: list[dict], latest_summary: dict, task_quality: list[dict]) -> str | None:
    low_quality = [item for item in task_quality if item.get("average_quality") is not None and item["average_quality"] <= 2.5]
    if low_quality:
        return low_quality[0]["module"]
    scored = [item for item in dimension_summary if item["average"] is not None]
    if scored:
        return sorted(scored, key=lambda item: item["average"])[0]["dimension"]
    if weaknesses:
        return weaknesses[0]["category"]
    if latest_summary.get("dimension_insights"):
        return latest_summary["dimension_insights"][0].get("dimension")
    return None


def calculate_current_streak(review_dates: list[str]) -> int:
    parsed_dates = set()
    for value in review_dates:
        try:
            parsed_dates.add(date.fromisoformat(value))
        except ValueError:
            continue
    if not parsed_dates:
        return 0
    cursor = date.today()
    if cursor not in parsed_dates:
        yesterday = cursor - timedelta(days=1)
        if yesterday not in parsed_dates:
            return 0
        cursor = yesterday
    streak = 0
    while cursor in parsed_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def latest_writing_band(rows: list[dict]) -> float | None:
    scored = [row for row in rows if row.get("estimated_band") is not None]
    return scored[-1].get("estimated_band") if scored else None


def parse_json(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]
