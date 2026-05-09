from __future__ import annotations

from app.services.ai_client import load_prompt, request_json


def review_writing_with_ai(task_type: str, prompt: str, essay_text: str) -> dict:
    system_prompt = load_prompt("writing_review.md")
    payload = {
        "target_band": 7.5,
        "task_type": task_type,
        "prompt": prompt,
        "essay_text": essay_text,
    }

    return request_json(system_prompt, payload)
