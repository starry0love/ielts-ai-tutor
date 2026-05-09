from __future__ import annotations

import json

from fastapi import APIRouter

from app.db import DIMENSIONS, get_connection


router = APIRouter()


@router.get("/summary")
def report_summary() -> dict:
    with get_connection() as connection:
        return {
            "weekly": build_period_report(connection, 7),
            "monthly": build_period_report(connection, 30),
            "radar": build_radar(connection),
        }


def build_period_report(connection, days: int) -> dict:
    date_arg = f"-{days - 1} days"
    plans = rows_to_dicts(
        connection.execute(
            """
            SELECT *
            FROM daily_plans
            WHERE plan_date >= date('now', ?)
            ORDER BY plan_date
            """,
            (date_arg,),
        ).fetchall()
    )
    planned_tasks = rows_to_dicts(
        connection.execute(
            """
            SELECT tasks.*, daily_plans.plan_date, daily_plans.focus_summary
            FROM tasks
            JOIN daily_plans ON daily_plans.id = tasks.daily_plan_id
            WHERE daily_plans.plan_date >= date('now', ?)
            ORDER BY daily_plans.plan_date, tasks.id
            """,
            (date_arg,),
        ).fetchall()
    )
    reviews = rows_to_dicts(
        connection.execute(
            """
            SELECT *
            FROM daily_reviews
            WHERE review_date >= date('now', ?)
            ORDER BY review_date
            """,
            (date_arg,),
        ).fetchall()
    )
    task_reviews = rows_to_dicts(
        connection.execute(
            """
            SELECT task_reviews.*, tasks.module, tasks.title, daily_reviews.review_date
            FROM task_reviews
            JOIN tasks ON tasks.id = task_reviews.task_id
            JOIN daily_reviews ON daily_reviews.id = task_reviews.daily_review_id
            WHERE daily_reviews.review_date >= date('now', ?)
            ORDER BY daily_reviews.review_date
            """,
            (date_arg,),
        ).fetchall()
    )
    total_minutes = sum(int(row.get("total_minutes") or 0) for row in reviews)
    task_status = status_from_planned_tasks(planned_tasks, task_reviews)
    planned_task_count = len(planned_tasks)
    reviewed_task_count = len({row["task_id"] for row in task_reviews})
    unreviewed_task_count = max(planned_task_count - reviewed_task_count, 0)
    completed_task_count = task_status.get("completed", 0)
    writing_rows = rows_to_dicts(
        connection.execute(
            """
            SELECT estimated_band, feedback_json, created_at
            FROM writing_submissions
            WHERE date(created_at) >= date('now', ?)
            ORDER BY created_at
            """,
            (date_arg,),
        ).fetchall()
    )
    weaknesses = rows_to_dicts(
        connection.execute(
            """
            SELECT category, description, severity, evidence
            FROM weaknesses
            WHERE date(last_seen_at) >= date('now', ?)
            ORDER BY severity DESC, last_seen_at DESC
            LIMIT 6
            """,
            (date_arg,),
        ).fetchall()
    )
    dimension_averages = dimension_averages_for(reviews)
    task_module_report = task_module_report_for(planned_tasks, task_reviews)
    low_dimensions = [
        item
        for item in sorted(dimension_averages, key=lambda row: row["average"] if row["average"] is not None else 99)
        if item["average"] is not None
    ][:5]
    energy_focus = energy_focus_trends(reviews)
    next_focus = choose_next_focus(dimension_averages, weaknesses, task_module_report, reviews)

    return {
        "days": days,
        "total_minutes": total_minutes,
        "planned_days": len(plans),
        "study_days": len(reviews),
        "task_status": task_status,
        "planned_task_count": planned_task_count,
        "reviewed_task_count": reviewed_task_count,
        "unreviewed_task_count": unreviewed_task_count,
        "completion_rate": completed_task_count / planned_task_count if planned_task_count else 0,
        "review_rate": reviewed_task_count / planned_task_count if planned_task_count else 0,
        "writing_average_band": average([row["estimated_band"] for row in writing_rows if row.get("estimated_band") is not None]),
        "writing_count": len(writing_rows),
        "writing_latest_feedback": latest_writing_feedback(writing_rows),
        "dimension_averages": dimension_averages,
        "low_dimensions": low_dimensions,
        "task_module_report": task_module_report,
        "daily_plan_review": daily_plan_review_for(plans, planned_tasks, task_reviews),
        "energy_focus": energy_focus,
        "top_weaknesses": weaknesses,
        "next_focus": next_focus,
        "mentor_summary": build_mentor_summary(days, reviews, task_module_report, dimension_averages, next_focus),
    }


def build_radar(connection) -> dict:
    reviews = rows_to_dicts(connection.execute("SELECT * FROM daily_reviews").fetchall())
    dimension_averages = dimension_averages_for(reviews)
    labels = [item["dimension"] for item in dimension_averages]
    values = [item["average"] if item["average"] is not None else 3 for item in dimension_averages]
    return {"labels": labels, "values": values}


def status_from_planned_tasks(planned_tasks: list[dict], task_reviews: list[dict]) -> dict[str, int]:
    reviews_by_task = {row["task_id"]: row for row in task_reviews}
    counts: dict[str, int] = {}
    for task in planned_tasks:
        review = reviews_by_task.get(task["id"])
        status = (review or {}).get("status") or task.get("status") or "pending"
        counts[status] = counts.get(status, 0) + 1
    return counts


def task_module_report_for(planned_tasks: list[dict], task_reviews: list[dict]) -> list[dict]:
    reviews_by_task = {row["task_id"]: row for row in task_reviews}
    grouped: dict[str, dict[str, list[dict]]] = {}
    for task in planned_tasks:
        module = task.get("module") or "Other"
        grouped.setdefault(module, {"planned": [], "reviews": []})
        grouped[module]["planned"].append(task)
        review = reviews_by_task.get(task["id"])
        if review:
            grouped[module]["reviews"].append(review)
    report = []
    for module, rows in grouped.items():
        planned = rows["planned"]
        reviews = rows["reviews"]
        reviewed_status = {row["task_id"]: row.get("status") for row in reviews}
        completed = sum(1 for task in planned if reviewed_status.get(task["id"], task.get("status")) == "completed")
        partial = sum(1 for task in planned if reviewed_status.get(task["id"], task.get("status")) == "partial")
        skipped = sum(1 for task in planned if reviewed_status.get(task["id"], task.get("status")) == "skipped")
        planned_minutes = sum(int(row.get("estimated_minutes") or 0) for row in planned)
        actual_minutes = sum(int(row.get("actual_minutes") or 0) for row in reviews)
        quality = [int(row.get("quality") or 3) for row in reviews]
        blockers = [row.get("blocker") for row in reviews if row.get("blocker")]
        next_actions = [row.get("next_action") for row in reviews if row.get("next_action")]
        report.append(
            {
                "module": module,
                "planned_count": len(planned),
                "reviewed_count": len(reviews),
                "completed_count": completed,
                "partial_count": partial,
                "skipped_count": skipped,
                "unreviewed_count": max(len(planned) - len(reviews), 0),
                "completion_rate": completed / len(planned) if planned else 0,
                "review_rate": len(reviews) / len(planned) if planned else 0,
                "planned_minutes": planned_minutes,
                "actual_minutes": actual_minutes,
                "minutes": actual_minutes,
                "average_quality": round(sum(quality) / len(quality), 2) if quality else None,
                "latest_blocker": blockers[-1] if blockers else None,
                "next_action": next_actions[-1] if next_actions else None,
            }
        )
    return sorted(report, key=lambda item: (item["planned_count"], item["actual_minutes"]), reverse=True)


def dimension_averages_for(reviews: list[dict]) -> list[dict]:
    scores: dict[str, dict[str, object]] = {
        dimension: {"values": [], "latest_note": ""}
        for dimension in DIMENSIONS
    }
    for review in reviews:
        for item in parse_json(review.get("dimensions_json"), []):
            dimension = item.get("dimension")
            score = item.get("score")
            if dimension in scores and isinstance(score, (int, float)):
                scores[dimension]["values"].append(score)
                if item.get("note"):
                    scores[dimension]["latest_note"] = item["note"]
    return [
        {
            "dimension": dimension,
            "average": round(sum(values["values"]) / len(values["values"]), 2) if values["values"] else None,
            "count": len(values["values"]),
            "latest_note": values["latest_note"],
        }
        for dimension, values in scores.items()
    ]


def daily_plan_review_for(plans: list[dict], planned_tasks: list[dict], task_reviews: list[dict]) -> list[dict]:
    reviews_by_task = {row["task_id"]: row for row in task_reviews}
    rows = []
    for plan in plans:
        tasks = [task for task in planned_tasks if task["daily_plan_id"] == plan["id"]]
        reviews = [reviews_by_task[task["id"]] for task in tasks if task["id"] in reviews_by_task]
        completed = sum(1 for review in reviews if review.get("status") == "completed")
        rows.append(
            {
                "plan_date": plan["plan_date"],
                "focus_summary": plan.get("focus_summary"),
                "planned_count": len(tasks),
                "reviewed_count": len(reviews),
                "completed_count": completed,
                "planned_minutes": sum(int(task.get("estimated_minutes") or 0) for task in tasks),
                "actual_minutes": sum(int(review.get("actual_minutes") or 0) for review in reviews),
            }
        )
    return rows


def latest_writing_feedback(writing_rows: list[dict]) -> dict | None:
    if not writing_rows:
        return None
    latest = writing_rows[-1]
    feedback = parse_json(latest.get("feedback_json"), {})
    return {
        "created_at": latest.get("created_at"),
        "estimated_band": latest.get("estimated_band"),
        "summary": feedback.get("summary"),
        "next_practice_focus": feedback.get("next_practice_focus"),
        "top_issues": feedback.get("top_issues", [])[:3],
    }


def energy_focus_trends(reviews: list[dict]) -> list[dict]:
    return [
        {
            "review_date": row["review_date"],
            "energy_level": row.get("energy_level"),
            "focus_level": row.get("focus_level"),
            "completion_level": row.get("completion_level"),
        }
        for row in reviews[-14:]
    ]


def choose_next_focus(dimension_averages: list[dict], weaknesses: list[dict], task_module_report: list[dict], reviews: list[dict]) -> str:
    weak_tasks = [item for item in task_module_report if item.get("average_quality") is not None and item["average_quality"] <= 2.5]
    if weak_tasks:
        return f"下阶段优先把 {weak_tasks[0]['module']} 的任务拆小，并明确完成证据。"
    scored = [item for item in dimension_averages if item["average"] is not None]
    if scored:
        weakest = sorted(scored, key=lambda item: item["average"])[0]
        return f"继续关注 {weakest['dimension']}，同时保护 Focus 和 Energy。"
    if weaknesses:
        return weaknesses[0]["description"]
    if reviews:
        latest_summary = parse_json(reviews[-1].get("ai_summary"), {})
        if latest_summary.get("tomorrow_adjustment"):
            return latest_summary["tomorrow_adjustment"]
    return "先完成几天计划和任务级复盘，再从真实模式里调整学习策略。"


def build_mentor_summary(days: int, reviews: list[dict], task_module_report: list[dict], dimension_averages: list[dict], next_focus: str) -> str:
    if not reviews:
        return f"最近 {days} 天还没有复盘。先完成入门对话，再做一份今日计划。"
    completed = sum(item.get("completed_count", 0) for item in task_module_report)
    planned = sum(item.get("planned_count", 0) for item in task_module_report)
    low = [item["dimension"] for item in dimension_averages if item["average"] is not None and item["average"] <= 2.5]
    low_text = "、".join(low[:3]) if low else "暂未出现稳定低分维度"
    return f"最近 {days} 天记录了 {len(reviews)} 次复盘，任务完成 {completed}/{planned}。低信号维度：{low_text}。下一步：{next_focus}"


def average(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 2) if values else None


def parse_json(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]
