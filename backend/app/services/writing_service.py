from __future__ import annotations

from pydantic import ValidationError

from app.schemas import WritingReviewAIOutput
from app.services.ai_client import AIUnavailableError, load_prompt, request_json


def review_writing_with_ai(task_type: str, prompt: str, essay_text: str) -> dict:
    system_prompt = load_prompt("writing_review.md")
    payload = {
        "target_band": 7.5,
        "task_type": task_type,
        "prompt": prompt,
        "essay_text": essay_text,
    }

    raw = request_json(system_prompt, payload)
    try:
        return WritingReviewAIOutput.model_validate(raw).model_dump()
    except ValidationError as exc:
        raise AIUnavailableError(f"AI writing feedback did not match the expected structure: {exc}") from exc
