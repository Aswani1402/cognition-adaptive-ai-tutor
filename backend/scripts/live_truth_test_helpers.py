from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from tutor.api.app import app


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "external" / "core_data" / "tutor.db"


def client() -> TestClient:
    return TestClient(app)


def unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}@example.test"


def register(prefix: str = "live_truth") -> tuple[TestClient, dict]:
    c = client()
    email = unique_email(prefix)
    password = "StrongPass123!"
    response = c.post("/auth/register", json={"name": "Live Truth Learner", "email": email, "password": password})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get("learner_id"), data
    data["email"] = email
    data["password"] = password
    return c, data


def db_row(query: str, params: tuple = ()) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()
