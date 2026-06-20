from __future__ import annotations

from tutor.doubt.doubt_intent_classifier import DoubtIntentClassifier


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    clf = DoubtIntentClassifier().load()
    cases = [
        ("I don't understand variables", "concept_doubt"),
        ("Why is 2score = 10 invalid?", "syntax_doubt"),
        ("My code gives an error, can you debug it?", "debug_doubt"),
        ("What will this code print?", "output_prediction_doubt"),
        ("Give me another example of JOIN", "example_request"),
        ("Can you revise variables quickly?", "revision_doubt"),
        ("What should I study after variables?", "next_step_doubt"),
        ("I am confused", "low_confidence_doubt"),
    ]
    for text, expected in cases:
        output = clf.predict(text, concept_name="Variables", domain="Python")
        _assert(output["status"] == "success", f"bad status: {output}")
        _assert(output["intent"] == expected, f"{text}: expected {expected}, got {output}")
        _assert(0.0 <= output["confidence"] <= 1.0, f"confidence out of range: {output}")
        print(f"{text} -> {output['intent']} confidence={output['confidence']} fallback={output['fallback_used']}")

    empty = clf.predict("")
    _assert(empty["fallback_used"] is True, f"empty should fallback: {empty}")
    _assert(empty["intent"] == "low_confidence_doubt", f"empty intent wrong: {empty}")

    odd = clf.predict("banana spaceship unrelated", concept_name="Variables")
    _assert(odd["status"] == "success", f"odd failed: {odd}")
    print(f"irrelevant -> {odd['intent']} confidence={odd['confidence']} fallback={odd['fallback_used']}")
    print("STATUS: success")
    print("MODULE: doubt_intent_classifier_test")


if __name__ == "__main__":
    main()
