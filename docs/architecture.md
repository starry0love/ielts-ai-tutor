# Architecture

IELTS AI Tutor is a local desktop app with a local backend.

```text
Electron desktop window
  -> Vue frontend
  -> HTTP API
FastAPI local backend
  -> SQLite local database
  -> User-provided OpenAI-compatible model API
```

The project is intentionally not a content-bank app. Reading, listening, writing, speaking, vocabulary, grammar, focus, and energy are treated as learning dimensions for planning and review.

The open-source version does not include proprietary test materials, audio, OCR output, or imported practice content.
