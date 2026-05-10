from __future__ import annotations

import json
from datetime import date, timedelta
from sqlite3 import Connection

from pydantic import ValidationError

from app.db import DIMENSIONS
from app.schemas import DailyPlanAIOutput, PlanDiscussionAIOutput
from app.services.ai_client import AIUnavailableError, load_prompt, request_json


MODULE_LABELS = {
    "Listening": "听力",
    "Reading": "阅读",
    "Writing": "写作",
    "Speaking": "口语",
    "Vocabulary": "词汇",
    "Grammar": "语法",
    "Pronunciation": "发音",
    "Fluency": "流利度",
    "Logic": "逻辑",
    "Test Strategy": "考试策略",
    "Focus": "专注",
    "Energy": "精力",
    "Review": "复盘",
}


def create_ai_plan(connection: Connection, user_feedback: str | None = None, replace_existing: bool = False) -> dict:
    today = date.today().isoformat()
    profile = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()
    if profile is not None and not bool(profile["onboarding_completed"]):
        return {
            "needs_onboarding": True,
            "plan": None,
            "tasks": [],
            "message": "请先完成入门对话，让导师理解目标、基础、时间和学习方式后再生成今日计划。",
        }

    if replace_existing:
        delete_plan_for_date(connection, today)

    existing = connection.execute("SELECT * FROM daily_plans WHERE plan_date = ?", (today,)).fetchone()
    if existing is not None:
        result = fetch_plan(connection, existing["id"])
        result["needs_onboarding"] = False
        return result

    context = collect_plan_context(connection)
    payload = {
        **context,
        "user_feedback": user_feedback,
        "output_schema": {
            "focus_summary": "中文字符串",
            "ai_reason": "中文字符串",
            "tasks": [
                {
                    "module": "一个 IELTS 维度英文名或 Review",
                    "title": "中文字符串",
                    "description": "中文字符串",
                    "estimated_minutes": "整数",
                    "completion_criteria": "中文字符串",
                    "ai_reason": "中文字符串",
                }
            ],
        },
    }

    raw_plan = request_json(load_prompt("mentor_daily_plan.md"), payload)
    try:
        ai_plan = DailyPlanAIOutput.model_validate(raw_plan).model_dump()
    except ValidationError as exc:
        raise AIUnavailableError(f"AI daily plan did not match the expected structure: {exc}") from exc

    focus_summary = str(ai_plan.get("focus_summary") or "今天围绕一个核心目标、一个支撑能力和一次具体复盘来学习。")
    ai_reason = str(ai_plan.get("ai_reason") or "根据入门画像、近期复盘、写作反馈和后台画像生成。")
    tasks = normalise_tasks(ai_plan.get("tasks") or [], context)

    cursor = connection.execute(
        """
        INSERT INTO daily_plans (plan_date, focus_summary, ai_reason)
        VALUES (?, ?, ?)
        """,
        (today, focus_summary, ai_reason),
    )
    plan_id = cursor.lastrowid
    insert_tasks(connection, plan_id, tasks)
    result = fetch_plan(connection, plan_id)
    result["needs_onboarding"] = False
    return result


def create_plan_discussion(connection: Connection) -> dict:
    context = collect_plan_context(connection)
    profile = context.get("profile", {})
    if not profile.get("onboarding_completed"):
        return {
            "context": context,
            "discussion": {
                "history_summary": "我还不了解你的目标、基础和学习方式，所以暂时不生成今日计划。",
                "learner_pattern": "先完成入门对话，后续计划和复盘才不会变成泛泛的任务清单。",
                "today_recommendation": "先告诉导师：目标分数、每天可用时间、当前基础、以前怎么学、哪些方法有效或无效。",
                "questions_for_user": [
                    "你想在什么时间前达到什么分数？",
                    "每天真实可用的学习时间是多少？",
                    "你现在四项大概是什么基础，最不稳的是哪一项？",
                    "你以前怎么学英语或雅思，哪些方法有效，哪些让你痛苦？",
                    "你希望导师更温柔、严格、理性，还是朋友式陪伴？",
                ],
                "needs_onboarding": True,
            },
        }
    raw_discussion = request_json(
        load_prompt("mentor_plan_discussion.md"),
        {
            **context,
            "output_schema": {
                "history_summary": "中文字符串",
                "learner_pattern": "中文字符串",
                "today_recommendation": "中文字符串",
                "questions_for_user": ["中文问题"],
            },
            "language": "所有解释性内容必须使用简体中文。",
        },
    )
    try:
        discussion = PlanDiscussionAIOutput.model_validate(raw_discussion).model_dump()
    except ValidationError as exc:
        raise AIUnavailableError(f"AI plan discussion did not match the expected structure: {exc}") from exc
    discussion["needs_onboarding"] = False
    return {"context": context, "discussion": discussion}


def collect_plan_context(connection: Connection) -> dict:
    profile = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()
    recent_reviews = rows_to_dicts(
        connection.execute("SELECT * FROM daily_reviews ORDER BY review_date DESC LIMIT 10").fetchall()
    )
    recent_tasks = rows_to_dicts(
        connection.execute(
            """
            SELECT tasks.*, daily_plans.plan_date
            FROM tasks
            JOIN daily_plans ON daily_plans.id = tasks.daily_plan_id
            ORDER BY daily_plans.plan_date DESC, tasks.id DESC
            LIMIT 24
            """
        ).fetchall()
    )
    task_reviews = rows_to_dicts(
        connection.execute(
            """
            SELECT task_reviews.*, tasks.module, tasks.title, daily_reviews.review_date
            FROM task_reviews
            JOIN tasks ON tasks.id = task_reviews.task_id
            JOIN daily_reviews ON daily_reviews.id = task_reviews.daily_review_id
            ORDER BY daily_reviews.review_date DESC, task_reviews.id DESC
            LIMIT 24
            """
        ).fetchall()
    )
    writing = rows_to_dicts(
        connection.execute(
            """
            SELECT created_at, task_type, estimated_band, task_response_score, coherence_score, lexical_score, grammar_score, feedback_json
            FROM writing_submissions
            ORDER BY created_at DESC
            LIMIT 8
            """
        ).fetchall()
    )
    memories = rows_to_dicts(
        connection.execute(
            "SELECT * FROM mentor_memories ORDER BY weight DESC, updated_at DESC LIMIT 16"
        ).fetchall()
    )
    weaknesses = rows_to_dicts(
        connection.execute(
            "SELECT * FROM weaknesses ORDER BY severity DESC, last_seen_at DESC LIMIT 10"
        ).fetchall()
    )
    profile_dict = dict(profile) if profile else {}
    profile_dict["onboarding_completed"] = bool(profile_dict.get("onboarding_completed"))
    return {
        "today": date.today().isoformat(),
        "yesterday": (date.today() - timedelta(days=1)).isoformat(),
        "dimensions": DIMENSIONS,
        "profile": profile_dict,
        "recent_reviews": recent_reviews,
        "recent_tasks": recent_tasks,
        "recent_task_reviews": task_reviews,
        "recent_writing": writing,
        "mentor_memories": memories,
        "weaknesses": weaknesses,
    }


def infer_main_focus(profile: dict) -> str:
    text = " ".join(str(profile.get(key) or "") for key in ["goal_notes", "baseline_notes", "study_methods", "current_level_notes"])
    for dimension in ["Writing", "Speaking", "Reading", "Listening", "Vocabulary", "Grammar"]:
        if dimension.lower() in text.lower() or MODULE_LABELS.get(dimension, "") in text:
            return dimension
    return "Writing"


def weakest_dimensions(context: dict) -> list[str]:
    scores: dict[str, list[int]] = {}
    for review in context.get("recent_reviews", []):
        try:
            dims = json.loads(review.get("dimensions_json") or "[]")
        except json.JSONDecodeError:
            dims = []
        for item in dims:
            dimension = item.get("dimension")
            score = item.get("score")
            if dimension and isinstance(score, int):
                scores.setdefault(dimension, []).append(score)
    ranked = sorted(scores, key=lambda key: sum(scores[key]) / len(scores[key]))
    return ranked or []


def normalise_tasks(tasks: list[dict], context: dict) -> list[dict]:
    source = tasks if isinstance(tasks, list) and tasks else []
    cleaned = []
    allowed_modules = set(DIMENSIONS) | {"Review"}
    for task in source[:5]:
        module = str(task.get("module") or "Review")
        if module not in allowed_modules:
            module = "Review"
        cleaned.append(
            {
                "module": module,
                "title": str(task.get("title") or f"{MODULE_LABELS.get(module, module)}任务"),
                "description": str(task.get("description") or "完成一个具体学习任务，并留下可复盘记录。"),
                "estimated_minutes": int(task.get("estimated_minutes") or 20),
                "completion_criteria": str(task.get("completion_criteria") or "留下产出和复盘记录。"),
                "ai_reason": str(task.get("ai_reason") or "根据当前学习画像安排。"),
            }
        )
    return cleaned


def insert_tasks(connection: Connection, plan_id: int, tasks: list[dict]) -> None:
    for task in tasks:
        connection.execute(
            """
            INSERT INTO tasks (
                daily_plan_id, module, title, description, estimated_minutes, completion_criteria, ai_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plan_id,
                task["module"],
                task["title"],
                task["description"],
                task["estimated_minutes"],
                task["completion_criteria"],
                task["ai_reason"],
            ),
        )


def fetch_plan(connection: Connection, plan_id: int) -> dict:
    plan = connection.execute("SELECT * FROM daily_plans WHERE id = ?", (plan_id,)).fetchone()
    tasks = connection.execute("SELECT * FROM tasks WHERE daily_plan_id = ? ORDER BY id", (plan_id,)).fetchall()
    return {"plan": dict(plan), "tasks": rows_to_dicts(tasks), "needs_onboarding": False}


def delete_plan_for_date(connection: Connection, plan_date: str) -> None:
    existing = connection.execute("SELECT * FROM daily_plans WHERE plan_date = ?", (plan_date,)).fetchone()
    if existing is None:
        return
    connection.execute("DELETE FROM tasks WHERE daily_plan_id = ?", (existing["id"],))
    connection.execute("DELETE FROM daily_plans WHERE id = ?", (existing["id"],))


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]

