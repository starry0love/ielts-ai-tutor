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


class WritingCriterionAIOutput(BaseModel):
    score: float | None = None
    comment: str | None = None
    evidence: str | None = None
    fix: str | None = None


class WritingCriteriaAIOutput(BaseModel):
    task_response: WritingCriterionAIOutput = Field(default_factory=WritingCriterionAIOutput)
    coherence_and_cohesion: WritingCriterionAIOutput = Field(default_factory=WritingCriterionAIOutput)
    lexical_resource: WritingCriterionAIOutput = Field(default_factory=WritingCriterionAIOutput)
    grammar_range_and_accuracy: WritingCriterionAIOutput = Field(default_factory=WritingCriterionAIOutput)


class WritingIssueAIOutput(BaseModel):
    category: str = "Writing"
    title: str = "写作问题"
    evidence: str | None = None
    fix: str | None = None
    comment: str | None = None
    severity: int = Field(default=2, ge=1, le=5)


class WritingReviewAIOutput(BaseModel):
    estimated_band: float | None = None
    criteria: WritingCriteriaAIOutput = Field(default_factory=WritingCriteriaAIOutput)
    summary: str = "写作反馈已生成。"
    top_issues: list[WritingIssueAIOutput] = Field(default_factory=list)
    band_75_rewrite: str | None = None
    next_practice_focus: str | None = None


class DailyPlanTaskAIOutput(BaseModel):
    module: str
    title: str
    description: str
    estimated_minutes: int = Field(default=20, ge=1, le=360)
    completion_criteria: str
    ai_reason: str | None = None


class DailyPlanAIOutput(BaseModel):
    focus_summary: str
    ai_reason: str | None = None
    tasks: list[DailyPlanTaskAIOutput] = Field(default_factory=list, min_length=1, max_length=5)


class PlanDiscussionAIOutput(BaseModel):
    history_summary: str
    learner_pattern: str
    today_recommendation: str
    questions_for_user: list[str] = Field(default_factory=list, max_length=8)


class DimensionInsightAIOutput(BaseModel):
    dimension: str
    insight: str


class TaskInsightAIOutput(BaseModel):
    task_id: int | None = None
    insight: str


class WeaknessAIOutput(BaseModel):
    category: str = "Focus"
    description: str = "Review signal"
    evidence: str | None = None
    severity: int = Field(default=1, ge=1, le=5)


class MemoryUpdateAIOutput(BaseModel):
    memory_type: str = "pattern"
    title: str
    content: str
    evidence: str | None = None
    weight: int = Field(default=1, ge=1, le=5)


class DailyReviewAIOutput(BaseModel):
    summary: str
    completion_analysis: str | None = None
    dimension_insights: list[DimensionInsightAIOutput] = Field(default_factory=list)
    task_insights: list[TaskInsightAIOutput] = Field(default_factory=list)
    new_weaknesses: list[WeaknessAIOutput] = Field(default_factory=list)
    memory_updates: list[MemoryUpdateAIOutput] = Field(default_factory=list)
    tomorrow_adjustment: str | None = None
    mentor_insight: str | None = None
    coach_note: str | None = None
