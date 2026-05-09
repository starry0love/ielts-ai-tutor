from __future__ import annotations

from fastapi import APIRouter

from app.db import DIMENSIONS


router = APIRouter()


@router.get("/dimensions")
def get_dimensions() -> dict:
    return {"dimensions": DIMENSIONS}
