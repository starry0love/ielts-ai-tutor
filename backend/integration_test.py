from __future__ import annotations

import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
TMP_DIR = BACKEND_DIR / ".tmp"
SMOKE_DB = TMP_DIR / "integration_test.sqlite"
SMOKE_ENV = TMP_DIR / "integration_test.env"
MOCK_PORT = 18991

TMP_DIR.mkdir(parents=True, exist_ok=True)
for path in [SMOKE_DB, SMOKE_ENV]:
    if path.exists():
        path.unlink()

os.environ["IELTS_TUTOR_DB_PATH"] = str(SMOKE_DB)
os.environ["IELTS_TUTOR_ENV_PATH"] = str(SMOKE_ENV)


class MockAIHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        text = json.dumps(reply_for(body), ensure_ascii=False)
        payload = {
            "id": "mock-chatcmpl",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        }
        data = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def reply_for(body: dict) -> dict:
    user_content = body.get("messages", [{}])[-1].get("content", "")
    if user_content == '{"status":"ok"}':
        return {"status": "ok"}
    payload = json.loads(user_content)
    schema = payload.get("output_schema", {})
    if "questions_for_user" in schema:
        return {
            "history_summary": "你目标明确，但需要先稳定每日执行。",
            "learner_pattern": "适合短任务、强复盘、少量高质量输出。",
            "today_recommendation": "今天先做一项写作核心任务，再做复盘。",
            "questions_for_user": ["今天真实可用时间是多少？", "今天精力更适合轻量还是挑战？"],
        }
    if "tasks" in schema:
        return {
            "focus_summary": "今天围绕写作论证和复盘闭环推进。",
            "ai_reason": "根据入门画像和今天反馈，先安排可留下证据的短任务。",
            "tasks": [
                {
                    "module": "Writing",
                    "title": "写作论证小练习",
                    "description": "围绕一个观点写出理由、例子和让步。",
                    "estimated_minutes": 35,
                    "completion_criteria": "留下一段论证和一个可修改点。",
                    "ai_reason": "写作是当前最需要证据反馈的维度。",
                },
                {
                    "module": "Review",
                    "title": "任务级复盘",
                    "description": "复盘今天的任务完成质量、阻碍和明天调整。",
                    "estimated_minutes": 10,
                    "completion_criteria": "每条任务都有复盘记录。",
                    "ai_reason": "后续计划依赖任务级反馈。",
                },
            ],
        }
    if "coach_note" in schema:
        return {
            "summary": "今天完成了核心写作任务，并记录了阻碍。",
            "completion_analysis": "完成率稳定，下一步要提高例子质量。",
            "dimension_insights": [{"dimension": "Writing", "insight": "论证可以更具体。"}],
            "task_insights": [{"task_id": 1, "insight": "例子仍然偏泛。"}],
            "new_weaknesses": [],
            "memory_updates": [],
            "tomorrow_adjustment": "明天保留一项写作任务，并加入例子积累。",
            "mentor_insight": "你适合短任务加即时反馈。",
            "coach_note": "复盘已保存，明天继续压实写作例子。",
        }
    return {
        "estimated_band": 6.5,
        "criteria": {
            "task_response": {"score": 6.5, "comment": "观点明确，但例子偏泛。"},
            "coherence_and_cohesion": {"score": 6.5, "comment": "段落关系基本清楚。"},
            "lexical_resource": {"score": 6.5, "comment": "词汇够用但不够精确。"},
            "grammar_range_and_accuracy": {"score": 6.5, "comment": "复杂句使用有限。"},
        },
        "summary": "这篇作文基础清楚，主要问题是论证深度不足。",
        "top_issues": [{"category": "Writing", "title": "例子偏泛", "fix": "把例子写到具体人群、场景和结果。"}],
        "next_practice_focus": "下一次只练一个主体段，把例子写具体。",
    }


def start_mock_server() -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", MOCK_PORT), MockAIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    server = start_mock_server()
    try:
        from fastapi.testclient import TestClient

        from app.db import init_db
        from app.main import app

        init_db()
        client = TestClient(app)
        config = {
            "provider": "openai-compatible",
            "api_key": "mock-key",
            "base_url": f"http://127.0.0.1:{MOCK_PORT}/v1",
            "model": "mock-model",
            "timeout_seconds": 10,
            "max_tokens": 800,
        }
        assert client.post("/api/profile/ai-test", json=config).json()["ok"] is True
        status = client.put("/api/profile/ai-config", json=config)
        assert status.status_code == 200
        assert status.json()["configured"] is True

        profile = client.put(
            "/api/profile",
            json={
                "target_band": 7.5,
                "exam_date": None,
                "daily_available_minutes": 90,
                "mentor_style": "warm_coach",
                "onboarding_completed": True,
                "goal_notes": "三个月后总分 7.5，写作至少 7。",
                "study_methods": "短任务和复盘比较有效。",
                "study_history": "以前背过单词，写作练得少。",
                "baseline_notes": "写作例子偏泛，口语容易卡。",
                "learning_preferences": "温和但直接。",
            },
        )
        assert profile.status_code == 200
        assert profile.json()["onboarding_completed"] is True

        discussion = client.post("/api/plans/discussion")
        assert discussion.status_code == 200
        assert discussion.json()["discussion"]["needs_onboarding"] is False

        plan = client.post("/api/plans/generate")
        assert plan.status_code == 200
        tasks = plan.json()["tasks"]
        assert len(tasks) == 2
        assert tasks[0]["module"] == "Writing"

        writing = client.post(
            "/api/writing/review",
            json={
                "task_type": "task2",
                "prompt": "Some people think self-study is better than classroom study. Discuss.",
                "essay_text": "Self-study is useful because students can control their schedule.",
            },
        )
        assert writing.status_code == 200
        assert writing.json()["estimated_band"] == 6.5

        review = client.post(
            "/api/reviews/daily",
            json={
                "review_date": "2026-05-09",
                "plan_id": plan.json()["plan"]["id"],
                "total_minutes": 45,
                "energy_level": "medium",
                "focus_level": "普通",
                "task_reviews": [
                    {
                        "task_id": tasks[0]["id"],
                        "status": "completed",
                        "actual_minutes": 35,
                        "difficulty": "normal",
                        "quality": 4,
                        "outcome": "完成一段论证。",
                        "blocker": "例子偏泛。",
                        "next_action": "明天补具体例子。",
                    }
                ],
                "dimensions": [{"dimension": "Writing", "score": 3, "note": "完成了但例子还不够。"}],
            },
        )
        assert review.status_code == 200
        assert "coach_note" in review.json()["summary"]
        assert client.get("/api/progress/summary").status_code == 200
        assert client.get("/api/reports/summary").status_code == 200
        print("integration-openai-compatible-ok")
    finally:
        server.shutdown()
        server.server_close()
        for path in [SMOKE_DB, SMOKE_ENV]:
            for _ in range(5):
                if not path.exists():
                    break
                try:
                    path.unlink()
                    break
                except PermissionError:
                    time.sleep(0.2)


if __name__ == "__main__":
    sys.exit(main())
