from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, AuthenticationError, BadRequestError, RateLimitError


ROOT_DIR = Path(__file__).resolve().parents[3]
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


class AIUnavailableError(RuntimeError):
    pass


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def get_model_name() -> str:
    load_env()
    return os.getenv("AI_MODEL", "gpt-4o-mini")


def is_ai_configured() -> bool:
    load_env()
    return bool(os.getenv("AI_API_KEY") and os.getenv("AI_BASE_URL") and os.getenv("AI_MODEL"))


def get_client_config() -> dict[str, str | None]:
    load_env()
    return {
        "provider": os.getenv("AI_PROVIDER", "openai-compatible"),
        "api_key": os.getenv("AI_API_KEY"),
        "base_url": os.getenv("AI_BASE_URL"),
        "model": os.getenv("AI_MODEL", "gpt-4o-mini"),
    }


def test_client_config(config: dict[str, str | int | None]) -> dict[str, str | bool]:
    from openai import OpenAI

    api_key = str(config.get("api_key") or "")
    base_url = str(config.get("base_url") or "")
    model = str(config.get("model") or "")
    timeout = float(config.get("timeout_seconds") or 25)
    if not api_key or not base_url or not model:
        raise AIUnavailableError("API key, base URL, and model are required.")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            max_tokens=80,
            messages=[
                {"role": "system", "content": "Return JSON only."},
                {"role": "user", "content": '{"status":"ok"}'},
            ],
        )
    except (APIConnectionError, AuthenticationError, BadRequestError, RateLimitError, APIError) as exc:
        raise AIUnavailableError(f"AI connection test failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise AIUnavailableError("AI connection test returned an empty response.")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIUnavailableError("AI connection test did not return valid JSON.") from exc
    if parsed.get("status") != "ok":
        raise AIUnavailableError("AI connection test returned an unexpected response.")
    return {"ok": True, "model": model, "base_url": base_url}


def request_json(system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    config = get_client_config()
    api_key = config["api_key"]
    if not api_key:
        raise AIUnavailableError(f"{config['provider']} API key is not configured.")

    from openai import OpenAI

    client_kwargs = {"api_key": api_key}
    if config["base_url"]:
        client_kwargs["base_url"] = config["base_url"]

    timeout = float(os.getenv("AI_TIMEOUT_SECONDS", "25"))
    max_tokens = int(os.getenv("AI_MAX_TOKENS", "1600"))
    client = OpenAI(timeout=timeout, **client_kwargs)
    try:
        response = client.chat.completions.create(
            model=config["model"],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
    except (APIConnectionError, AuthenticationError, BadRequestError, RateLimitError, APIError) as exc:
        raise AIUnavailableError(f"AI request failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise AIUnavailableError("OpenAI returned an empty response.")

    return json.loads(content)


def load_env() -> None:
    env_path = os.getenv("IELTS_TUTOR_ENV_PATH")
    if env_path:
        load_dotenv(env_path, override=True)
    load_dotenv(ROOT_DIR / ".env", override=True)
