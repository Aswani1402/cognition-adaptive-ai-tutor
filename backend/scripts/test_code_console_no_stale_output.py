from __future__ import annotations

from scripts.live_truth_test_helpers import register


def main() -> None:
    c, auth = register("code_stale")
    first = c.post("/code/run", json={"learner_id": auth["learner_id"], "code": "name = 'Alice'\nprint(name)"}).json()
    second = c.post("/code/run", json={"learner_id": auth["learner_id"], "code": "score = 10\nprint(score)"}).json()
    assert first["stdout"].strip() == "Alice", first
    assert second["stdout"].strip() == "10", second
    assert "Alice" not in second["stdout"], second
    print({"first": first["stdout"], "second": second["stdout"]})


if __name__ == "__main__":
    main()
