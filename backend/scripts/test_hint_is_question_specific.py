from __future__ import annotations

from scripts.live_truth_test_helpers import client


def main() -> None:
    c = client()
    debug = c.post("/hint/predict", json={"subject": "Python", "concept_id": "P1", "question_type": "debug_task", "hint_count": 1}).json()
    output = c.post("/hint/predict", json={"subject": "Python", "concept_id": "P1", "question_type": "output_prediction", "hint_count": 1}).json()
    assert debug["hint_type"] == "debug_hint", debug
    assert output["hint_type"] == "output_prediction_hint", output
    assert debug["hint_text"] != output["hint_text"], (debug, output)
    print({"debug": debug["hint_text"], "output": output["hint_text"]})


if __name__ == "__main__":
    main()
