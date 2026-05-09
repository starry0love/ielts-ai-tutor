from __future__ import annotations

from pydantic import BaseModel, Field


class Profile(BaseModel):
    target_band: float = 7.5
    exam_date: str | None = None
    daily_available_minutes: int = 120
    current_level_notes: str | None = None
    mentor_style: str = "warm_coach"
    onboarding_completed: bool = False
    goal_notes: str | None = None
    study_methods: str | None = None
    study_history: str | None = None
    baseline_notes: str | None = None
    learning_preferences: str | None = None
    onboarding_summary: str | None = None


class AIConfigUpdate(BaseModel):
    provider: str = "openai-compatible"
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 25
    max_tokens: int = 1600


class DailyPlanCreate(BaseModel):
    plan_date: str
    focus_summary: str
    ai_reason: str | None = None


class TaskCreate(BaseModel):
    daily_plan_id: int
    module: str
    title: str
    description: str
    estimated_minutes: int
    completion_criteria: str
    ai_reason: str | None = None


class TaskUpdate(BaseModel):
    status: str | None = None
    actual_minutes: int | None = None
    difficulty: str | None = None
    incomplete_reason: str | None = None


class WritingReviewRequest(BaseModel):
    task_type: str = Field(pattern="^(task1|task2)$")
    prompt: str
    essay_text: str


class DimensionRating(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    note: str | None = None


class ModuleReflection(BaseModel):
    module: str
    minutes: int = 0
    quality: int = Field(default=3, ge=1, le=5)
    note: str | None = None


class TaskReflection(BaseModel):
    task_id: int
    status: str = "completed"
    actual_minutes: int = 0
    difficulty: str | None = None
    quality: int = Field(default=3, ge=1, le=5)
    outcome: str | None = None
    blocker: str | None = None
    next_action: str | None = None


class DailyReviewCreate(BaseModel):
    review_date: str
    total_minutes: int
    energy_level: str
    plan_id: int | None = None
    mood: str | None = None
    focus_level: str | None = None
    completion_level: str | None = None
    hardest_part: str | None = None
    unfinished_reason: str | None = None
    dimensions: list[DimensionRating] = Field(default_factory=list)
    task_reviews: list[TaskReflection] = Field(default_factory=list)
    module_reflections: list[ModuleReflection] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    wins: str | None = None
    tomorrow_preference: str | None = None
    message_to_mentor: str | None = None
