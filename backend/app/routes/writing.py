from __future__ import annotations

import json

from fastapi import APIRouter

from app.db import get_connection
from app.schemas import WritingReviewRequest
from app.services.writing_service import review_writing_with_ai


router = APIRouter()


@router.post("/review")
def review_writing(payload: WritingReviewRequest) -> dict:
    feedback = review_writing_with_ai(
        task_type=payload.task_type,
        prompt=payload.prompt,
        essay_text=payload.essay_text,
    )
    criteria = feedback.get("criteria", {})
    task_response = criteria.get("task_response", {})
    coherence = criteria.get("coherence_and_cohesion", {})
    lexical = criteria.get("lexical_resource", {})
    grammar = criteria.get("grammar_range_and_accuracy", {})

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO writing_submissions (
                task_type,
                prompt,
                essay_text,
                estimated_band,
                task_response_score,
                coherence_score,
                lexical_score,
                grammar_score,
                feedback_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.task_type,
                payload.prompt,
                payload.essay_text,
                feedback.get("estimated_band"),
                task_response.get("score"),
                coherence.get("score"),
                lexical.get("score"),
                grammar.get("score"),
                json.dumps(feedback, ensure_ascii=False),
            ),
        )
        submission_id = cursor.lastrowid
        save_writing_signals(connection, submission_id, feedback)
        row = connection.execute(
            "SELECT * FROM writing_submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
        return dict(row)


@router.get("/history")
def writing_history() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM writing_submissions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def save_writing_signals(connection, submission_id: int, feedback: dict) -> None:
    score = feedback.get("estimated_band")
    summary = feedback.get("summary") or feedback.get("overall_feedback") or "写作批改已保存。"
    if summary:
        upsert_memory(
            connection,
            "writing",
            "最近写作画像",
            f"最近一次写作 Band: {score or '未评分'}。{summary}",
            f"writing_submission_id={submission_id}",
            4,
        )
    for issue in feedback.get("top_issues", [])[:5]:
        title = issue.get("title") or issue.get("category") or "写作问题"
        content = issue.get("fix") or issue.get("evidence") or issue.get("comment") or title
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
                issue.get("category", "Writing"),
                title,
                issue.get("evidence") or f"writing_submission_id={submission_id}",
                int(issue.get("severity", 2) or 2),
            ),
        )
        upsert_memory(
            connection,
            "writing_weakness",
            f"写作反复问题：{title}",
            content,
            f"writing_submission_id={submission_id}",
            3,
        )
    next_focus = feedback.get("next_practice_focus")
    if next_focus:
        upsert_memory(
            connection,
            "strategy",
            "写作下一步训练重点",
            next_focus,
            f"writing_submission_id={submission_id}",
            3,
        )


def upsert_memory(connection, memory_type: str, title: str, content: str, evidence: str, weight: int) -> None:
    existing = connection.execute(
        "SELECT id, weight FROM mentor_memories WHERE memory_type = ? AND title = ? LIMIT 1",
        (memory_type, title),
    ).fetchone()
    if existing:
        connection.execute(
            """
            UPDATE mentor_memories
            SET content = ?, evidence = ?, weight = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (content, evidence, max(int(existing["weight"] or 1), weight), existing["id"]),
        )
    else:
        connection.execute(
            """
            INSERT INTO mentor_memories (memory_type, title, content, evidence, weight)
            VALUES (?, ?, ?, ?, ?)
            """,
            (memory_type, title, content, evidence, weight),
        )
