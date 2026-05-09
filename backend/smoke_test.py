from __future__ import annotations

import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
DEPS_DIR = BACKEND_DIR / ".deps"
TMP_DIR = BACKEND_DIR / ".tmp"
SMOKE_DB = TMP_DIR / "smoke_test.sqlite"

if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))

TMP_DIR.mkdir(parents=True, exist_ok=True)
if SMOKE_DB.exists():
    SMOKE_DB.unlink()
os.environ["IELTS_TUTOR_DB_PATH"] = str(SMOKE_DB)

from fastapi.testclient import TestClient

from app.db import get_connection, init_db
from app.main import app
from app.services import plan_service, review_service, writing_service


def fake_json(system_prompt: str, user_payload: dict) -> dict:
    schema = user_payload.get("output_schema", {})
    if "tasks" in schema:
        return {
            "focus_summary": "Smoke focus summary.",
            "ai_reason": "Smoke AI reason.",
            "tasks": [
                {
                    "module": "Writing",
                    "title": "Smoke writing task",
                    "description": "Smoke task description.",
                    "estimated_minutes": 30,
                    "completion_criteria": "Smoke completion evidence.",
                    "ai_reason": "Smoke task reason.",
                },
                {
                    "module": "Review",
                    "title": "Smoke review task",
                    "description": "Smoke review description.",
                    "estimated_minutes": 10,
                    "completion_criteria": "Smoke review evidence.",
                    "ai_reason": "Smoke review reason.",
                },
            ],
        }
    if "questions_for_user" in schema:
        return {
            "history_summary": "Smoke history.",
            "learner_pattern": "Smoke learner pattern.",
            "today_recommendation": "Smoke recommendation.",
            "questions_for_user": ["Smoke question?"],
        }
    if "coach_note" in schema:
        return {
            "summary": "Smoke review summary.",
            "completion_analysis": "Smoke completion analysis.",
            "dimension_insights": [],
            "task_insights": [],
            "new_weaknesses": [],
            "memory_updates": [],
            "tomorrow_adjustment": "Smoke tomorrow adjustment.",
            "mentor_insight": "Smoke mentor insight.",
            "coach_note": "Smoke coach note.",
        }
    return {
        "estimated_band": 6.5,
        "criteria": {
            "task_response": {"score": 6.5},
            "coherence_and_cohesion": {"score": 6.5},
            "lexical_resource": {"score": 6.5},
            "grammar_range_and_accuracy": {"score": 6.5},
        },
        "summary": "Smoke writing feedback.",
        "top_issues": [],
        "next_practice_focus": "Smoke next focus.",
    }


def main() -> None:
    plan_service.request_json = fake_json
    review_service.request_json = fake_json
    writing_service.request_json = fake_json

    init_db()
    client = TestClient(app)

    assert client.get("/api/health").json()["status"] == "ok"
    profile = client.get("/api/profile")
    assert profile.status_code == 200
    assert profile.json()["onboarding_completed"] is False

    blocked_plan = client.post("/api/plans/generate")
    assert blocked_plan.status_code == 200
    assert blocked_plan.json()["needs_onboarding"] is True
    assert blocked_plan.json()["tasks"] == []

    update_profile = client.put(
        "/api/profile",
        json={
            "target_band": 7.5,
            "exam_date": None,
            "daily_available_minutes": 90,
            "current_level_notes": "Smoke learner profile.",
            "mentor_style": "analytical",
            "onboarding_completed": True,
            "goal_notes": "Reach IELTS 7.5 with stable writing and speaking.",
            "study_methods": "Short focused blocks and review work best.",
            "study_history": "Has studied vocabulary and writing before.",
            "baseline_notes": "Writing examples are weak; focus is good in the morning.",
            "learning_preferences": "Direct, analytical feedback with clear next actions.",
            "onboarding_summary": "Smoke onboarding summary.",
        },
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["onboarding_completed"] is True

    dimensions = client.get("/api/mentor/dimensions")
    assert dimensions.status_code == 200
    assert "Writing" in dimensions.json()["dimensions"]

    discussion = client.post("/api/plans/discussion")
    assert discussion.status_code == 200
    assert discussion.json()["discussion"]["needs_onboarding"] is False

    plan = client.post("/api/plans/generate")
    assert plan.status_code == 200
    tasks = plan.json()["tasks"]
    assert 1 <= len(tasks) <= 5
    assert any(task["module"] in {"Writing", "Focus", "Energy", "Review"} for task in tasks)

    writing = client.post(
        "/api/writing/review",
        json={
            "task_type": "task2",
            "prompt": "Some people think technology improves education. Discuss.",
            "essay_text": "This is a short essay for smoke testing.",
        },
    )
    assert writing.status_code == 200
    assert writing.json()["task_type"] == "task2"

    task_reviews = [
        {
            "task_id": task["id"],
            "status": "completed" if index == 0 else "partial",
            "actual_minutes": task["estimated_minutes"],
            "difficulty": "normal",
            "quality": 3,
            "outcome": "Smoke task outcome.",
            "blocker": "Examples were thin." if index == 1 else "",
            "next_action": "Use a smaller evidence template.",
        }
        for index, task in enumerate(tasks)
    ]
    review = client.post(
        "/api/reviews/daily",
        json={
            "review_date": "2026-05-08",
            "plan_id": plan.json()["plan"]["id"],
            "total_minutes": 90,
            "energy_level": "medium",
            "focus_level": "medium",
            "completion_level": "high",
            "hardest_part": "Keeping logic tight in writing.",
            "dimensions": [
                {"dimension": "Writing", "score": 2, "note": "Ideas were clear but examples were thin."},
                {"dimension": "Focus", "score": 4, "note": "Good morning focus."},
            ],
            "task_reviews": task_reviews,
            "wins": "Finished the planned writing block.",
            "tomorrow_preference": "Keep one writing task and one light vocabulary task.",
            "message_to_mentor": "Please remember that examples are the hard part.",
        },
    )
    assert review.status_code == 200
    assert review.json()["total_minutes"] == 90
    assert len(review.json()["task_reviews"]) == len(tasks)

    progress = client.get("/api/progress/summary")
    assert progress.status_code == 200
    assert progress.json()["total_minutes"] >= 90
    assert "dimension_summary" in progress.json()
    assert "task_quality" in progress.json()

    reports = client.get("/api/reports/summary")
    assert reports.status_code == 200
    assert "weekly" in reports.json()
    assert "task_module_report" in reports.json()["weekly"]
    assert reports.json()["weekly"]["planned_task_count"] >= len(tasks)
    assert reports.json()["weekly"]["reviewed_task_count"] == len(tasks)
    assert "daily_plan_review" in reports.json()["weekly"]
    assert "low_dimensions" in reports.json()["weekly"]

    with get_connection() as connection:
        memories = connection.execute("SELECT * FROM mentor_memories").fetchall()
        task_review_rows = connection.execute("SELECT * FROM task_reviews").fetchall()
        assert len(memories) >= 1
        assert len(task_review_rows) == len(tasks)

    print("backend-mentor-smoke-ok")


if __name__ == "__main__":
    main()
