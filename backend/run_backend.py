from __future__ import annotations

import sys
import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
DEPS_DIR = BACKEND_DIR / ".deps"

if DEPS_DIR.exists():
    sys.path.insert(0, str(DEPS_DIR))

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=int(os.getenv("IELTS_TUTOR_PORT", "8000")),
        reload=False,
    )
