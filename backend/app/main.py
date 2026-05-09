from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routes import mentor, plans, profile, progress, reports, reviews, tasks, writing


app = FastAPI(title="IELTS AI Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(plans.router, prefix="/api/plans", tags=["plans"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(writing.router, prefix="/api/writing", tags=["writing"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["reviews"])
app.include_router(progress.router, prefix="/api/progress", tags=["progress"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(mentor.router, prefix="/api/mentor", tags=["mentor"])
