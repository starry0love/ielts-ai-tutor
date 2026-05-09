from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.db import get_connection
from app.schemas import TaskCreate, TaskUpdate


router = APIRouter()


@router.post("")
def create_task(task: TaskCreate) -> dict:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO tasks (
                daily_plan_id,
                module,
                title,
                description,
                estimated_minutes,
                completion_criteria,
                ai_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.daily_plan_id,
                task.module,
                task.title,
                task.description,
                task.estimated_minutes,
                task.completion_criteria,
                task.ai_reason,
            ),
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


@router.patch("/{task_id}")
def update_task(task_id: int, update: TaskUpdate) -> dict:
    fields = update.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No update fields provided.")

    assignments = ", ".join([f"{field} = ?" for field in fields])
    values = list(fields.values()) + [task_id]

    with get_connection() as connection:
        connection.execute(
            f"""
            UPDATE tasks
            SET {assignments},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        row = connection.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return dict(row)

