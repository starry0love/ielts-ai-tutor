from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.db import get_connection
from app.schemas import DailyPlanCreate
from app.services.plan_service import create_ai_plan, create_plan_discussion


router = APIRouter()


@router.get("/today")
def get_today_plan() -> dict:
    today = date.today().isoformat()
    with get_connection() as connection:
        profile = connection.execute("SELECT onboarding_completed FROM users WHERE id = 1").fetchone()
        needs_onboarding = not bool(profile["onboarding_completed"]) if profile else True
        plan = connection.execute(
            "SELECT * FROM daily_plans WHERE plan_date = ?",
            (today,),
        ).fetchone()
        if plan is None:
            return {"needs_onboarding": needs_onboarding, "plan": None, "tasks": []}

        tasks = connection.execute(
            "SELECT * FROM tasks WHERE daily_plan_id = ? ORDER BY id",
            (plan["id"],),
        ).fetchall()
        return {"needs_onboarding": needs_onboarding, "plan": dict(plan), "tasks": [dict(task) for task in tasks]}


@router.post("")
def create_plan(plan: DailyPlanCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO daily_plans (plan_date, focus_summary, ai_reason)
            VALUES (?, ?, ?)
            """,
            (plan.plan_date, plan.focus_summary, plan.ai_reason),
        )
        row = connection.execute(
            "SELECT * FROM daily_plans WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


@router.post("/generate")
def generate_plan() -> dict:
    with get_connection() as connection:
        return create_ai_plan(connection)


@router.post("/discussion")
def plan_discussion() -> dict:
    with get_connection() as connection:
        return create_plan_discussion(connection)


@router.post("/regenerate")
def regenerate_plan(payload: dict | None = None) -> dict:
    user_feedback = (payload or {}).get("user_feedback")
    with get_connection() as connection:
        return create_ai_plan(
            connection,
            user_feedback=user_feedback,
            replace_existing=True,
        )
