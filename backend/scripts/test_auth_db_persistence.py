from __future__ import annotations

import sqlite3

from scripts.live_truth_test_helpers import DB_PATH, register


def main() -> None:
    c, auth = register("auth_db")
    login = c.post("/auth/login", json={"email": auth["email"], "password": auth["password"]}).json()
    assert login["learner_id"] == auth["learner_id"], login
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        user = dict(conn.execute("SELECT * FROM users WHERE email = ?", (auth["email"],)).fetchone())
        profile = dict(conn.execute("SELECT * FROM learner_profile WHERE learner_id = ?", (auth["learner_id"],)).fetchone())
    finally:
        conn.close()
    assert user["password_hash"] != auth["password"]
    assert str(user["password_hash"]).startswith("pbkdf2_sha256$")
    assert profile.get("active_subject") in (None, "")
    print(f"DB path: {DB_PATH}")
    print(f"users count: {users_count}")
    print(f"latest user email: {user['email']}")
    print(f"learner_profile row: {profile}")
    print(f"active_subject: {profile.get('active_subject')}")
    print(f"current_concept_id: {profile.get('current_concept_id')}")
    print(f"current_difficulty: {profile.get('current_difficulty')}")


if __name__ == "__main__":
    main()
