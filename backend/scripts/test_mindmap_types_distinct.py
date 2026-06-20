from __future__ import annotations

from scripts.live_truth_test_helpers import client


def main() -> None:
    data = client().get("/mindmap/S1?subject=SQL%20%2F%20Database").json()
    variants = data["mindmap_variants"]
    keys = ["concept_mindmap", "comparison_mindmap", "revision_mindmap", "misconception_mindmap"]
    assert all(key in variants for key in keys), variants
    serials = {key: str(variants[key]) for key in keys}
    assert len(set(serials.values())) == len(keys), serials
    print({key: len(variants[key]) for key in keys})


if __name__ == "__main__":
    main()
