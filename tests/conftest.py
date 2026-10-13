import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Set before any project module is imported.
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("META_WA_PHONE_NUMBER_ID", "123")
os.environ.setdefault("META_WA_ACCESS_TOKEN", "test-token")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("WEBHOOK_SECRET", None)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLBACKS_DB_PATH", str(tmp_path / "test.db"))
    import scheduler

    scheduler.init_db()
    return scheduler


@pytest.fixture()
def client(db, monkeypatch):
    from fastapi.testclient import TestClient

    import app as app_module

    app_module._call_state.clear()
    return TestClient(app_module.app)
