from __future__ import annotations

from scripts.live_truth_test_helpers import client


def main() -> None:
    data = client().get("/flashcards/test_learner/S1?subject=SQL%20%2F%20Database").json()
    cards = data["flashcards"]
    blob = str(cards)
    assert len(cards) >= 6, data
    assert "core concept in selected subject" not in blob.lower(), blob
    assert "SQL / Database" in blob or "database" in blob.lower() or "sql" in blob.lower(), blob
    print({"count": len(cards), "first": cards[0]})


if __name__ == "__main__":
    main()
