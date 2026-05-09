from __future__ import annotations

import os
import sqlite3
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
DB_PATH = Path(os.getenv("IELTS_TUTOR_DB_PATH", str(DATA_DIR / "ielts_tutor.sqlite")))

DIMENSIONS = [
    "Listening",
    "Reading",
    "Writing",
    "Speaking",
    "Vocabulary",
    "Grammar",
    "Pronunciation",
    "Fluency",
    "Logic",
    "Test Strategy",
    "Focus",
    "Energy",
]


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                target_band REAL NOT NULL DEFAULT 7.5,
                exam_date TEXT,
                daily_available_minutes INTEGER NOT NULL DEFAULT 120,
                current_level_notes TEXT,
                mentor_style TEXT NOT NULL DEFAULT 'warm_coach',
                onboarding_completed INTEGER NOT NULL DEFAULT 0,
                goal_notes TEXT,
                study_methods TEXT,
                study_history TEXT,
                baseline_notes TEXT,
                learning_preferences TEXT,
                onboarding_summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_date TEXT NOT NULL UNIQUE,
                focus_summary TEXT NOT NULL,
                ai_reason TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_plan_id INTEGER NOT NULL,
                module TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                estimated_minutes INTEGER NOT NULL,
                completion_criteria TEXT NOT NULL,
                ai_reason TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                actual_minutes INTEGER,
                difficulty TEXT,
                incomplete_reason TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (daily_plan_id) REFERENCES daily_plans(id)
            );

            CREATE TABLE IF NOT EXISTS writing_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                prompt TEXT NOT NULL,
                essay_text TEXT NOT NULL,
                estimated_band REAL,
                task_response_score REAL,
                coherence_score REAL,
                lexical_score REAL,
                grammar_score REAL,
                feedback_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS writing_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                title TEXT NOT NULL,
                prompt TEXT NOT NULL,
                topic TEXT NOT NULL,
                source TEXT NOT NULL,
                source_kind TEXT NOT NULL DEFAULT 'ai_simulated',
                difficulty TEXT NOT NULL DEFAULT 'medium',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS daily_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_date TEXT NOT NULL UNIQUE,
                plan_id INTEGER,
                total_minutes INTEGER NOT NULL,
                energy_level TEXT NOT NULL,
                mood TEXT,
                focus_level TEXT,
                completion_level TEXT,
                hardest_part TEXT,
                unfinished_reason TEXT,
                dimensions_json TEXT,
                task_reviews_json TEXT,
                module_reflections_json TEXT,
                blockers_json TEXT,
                wins TEXT,
                tomorrow_preference TEXT,
                message_to_mentor TEXT,
                ai_summary TEXT,
                tomorrow_adjustment TEXT,
                mentor_insight TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES daily_plans(id)
            );

            CREATE TABLE IF NOT EXISTS task_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                daily_review_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                actual_minutes INTEGER NOT NULL DEFAULT 0,
                difficulty TEXT,
                quality INTEGER NOT NULL DEFAULT 3,
                outcome TEXT,
                blocker TEXT,
                next_action TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (daily_review_id) REFERENCES daily_reviews(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            );

            CREATE TABLE IF NOT EXISTS weaknesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT,
                severity INTEGER NOT NULL DEFAULT 1,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mentor_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                evidence TEXT,
                weight INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        ensure_user_columns(connection)
        seed_default_user(connection)
        migrate_existing_onboarding_notes(connection)
        ensure_review_columns(connection)
        remove_legacy_writing_prompts(connection)


def ensure_user_columns(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "users", "mentor_style", "TEXT NOT NULL DEFAULT 'warm_coach'")
    ensure_column(connection, "users", "onboarding_completed", "INTEGER NOT NULL DEFAULT 0")
    ensure_column(connection, "users", "goal_notes", "TEXT")
    ensure_column(connection, "users", "study_methods", "TEXT")
    ensure_column(connection, "users", "study_history", "TEXT")
    ensure_column(connection, "users", "baseline_notes", "TEXT")
    ensure_column(connection, "users", "learning_preferences", "TEXT")
    ensure_column(connection, "users", "onboarding_summary", "TEXT")
    ensure_column(connection, "users", "created_at", "TEXT")
    ensure_column(connection, "users", "updated_at", "TEXT")


def ensure_review_columns(connection: sqlite3.Connection) -> None:
    ensure_column(connection, "daily_reviews", "plan_id", "INTEGER")
    ensure_column(connection, "daily_reviews", "mood", "TEXT")
    ensure_column(connection, "daily_reviews", "focus_level", "TEXT")
    ensure_column(connection, "daily_reviews", "completion_level", "TEXT")
    ensure_column(connection, "daily_reviews", "dimensions_json", "TEXT")
    ensure_column(connection, "daily_reviews", "task_reviews_json", "TEXT")
    ensure_column(connection, "daily_reviews", "module_reflections_json", "TEXT")
    ensure_column(connection, "daily_reviews", "blockers_json", "TEXT")
    ensure_column(connection, "daily_reviews", "wins", "TEXT")
    ensure_column(connection, "daily_reviews", "tomorrow_preference", "TEXT")
    ensure_column(connection, "daily_reviews", "message_to_mentor", "TEXT")
    ensure_column(connection, "daily_reviews", "mentor_insight", "TEXT")
    ensure_column(connection, "daily_reviews", "updated_at", "TEXT")


def seed_default_user(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO users (
            id,
            target_band,
            daily_available_minutes,
            current_level_notes,
            mentor_style,
            onboarding_completed
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            7.5,
            120,
            "先完成入门对话，导师会基于目标、基础、学习方式和时间生成计划。",
            "warm_coach",
            0,
        ),
    )


def migrate_existing_onboarding_notes(connection: sqlite3.Connection) -> None:
    row = connection.execute("SELECT * FROM users WHERE id = 1").fetchone()
    if row is None or bool(row["onboarding_completed"]):
        return

    notes = (row["current_level_notes"] or "").strip()
    if not notes or "目标：" not in notes or "基础：" not in notes:
        return

    fields = parse_onboarding_notes(notes)
    connection.execute(
        """
        UPDATE users
        SET onboarding_completed = 1,
            onboarding_summary = ?,
            goal_notes = COALESCE(goal_notes, ?),
            baseline_notes = COALESCE(baseline_notes, ?),
            study_history = COALESCE(study_history, ?),
            study_methods = COALESCE(study_methods, ?),
            learning_preferences = COALESCE(learning_preferences, ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
        """,
        (
            notes,
            fields.get("目标"),
            fields.get("基础"),
            fields.get("学习经历"),
            fields.get("方法偏好"),
            fields.get("导师偏好"),
        ),
    )
    upsert_system_memory(connection, "profile", "入门画像", notes, "migrated onboarding notes", 5)


def parse_onboarding_notes(notes: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in notes.splitlines():
        if "：" not in line:
            continue
        key, value = line.split("：", 1)
        value = value.strip()
        if value and value != "未填写":
            fields[key.strip()] = value
    return fields


def upsert_system_memory(
    connection: sqlite3.Connection,
    memory_type: str,
    title: str,
    content: str,
    evidence: str,
    weight: int,
) -> None:
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


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if column not in {row["name"] for row in columns}:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def remove_legacy_writing_prompts(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM writing_prompts WHERE source LIKE 'built-in-%'")
