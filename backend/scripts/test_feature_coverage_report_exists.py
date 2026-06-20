from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "evaluation_outputs" / "reports" / "frontend_full_generation_feature_coverage_report.md"
JSON_PATH = ROOT / "evaluation_outputs" / "json" / "frontend_full_generation_feature_coverage_report.json"


def main() -> None:
    assert MD.exists(), f"Missing report: {MD}"
    assert JSON_PATH.exists(), f"Missing JSON report: {JSON_PATH}"
    text = MD.read_text(encoding="utf-8")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    required_sections = [
        "Page/button/component coverage",
        "Voice script coverage",
        "Teaching view coverage",
        "Assessment type coverage",
        "CogniTutorLM generation coverage",
        "RAG-to-generation connection status",
        "Remaining warnings",
    ]
    missing = [section for section in required_sections if section not in text]
    assert not missing, f"Missing report sections: {missing}"
    assert data.get("status") in {"success", "warning"}
    print("feature coverage report exists test success")


if __name__ == "__main__":
    main()
