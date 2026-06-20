from __future__ import annotations

import json
from pathlib import Path


JSON_REPORT = Path("evaluation_outputs/json/adaptive_hint_policy_report.json")
MD_REPORT = Path("evaluation_outputs/reports/adaptive_hint_policy_report.md")


def _ensure_report() -> dict:
    if not JSON_REPORT.exists() or not MD_REPORT.exists():
        from scripts.test_adaptive_hint_policy import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(JSON_REPORT.read_text(encoding="utf-8"))


def main() -> None:
    report = _ensure_report()
    distribution = report.get("hint_type_distribution") or {}

    assert report.get("status") == "success"
    assert report.get("module") == "adaptive_hint_policy_test"
    assert report.get("test_case_count") == 8
    assert distribution
    assert float(report.get("average_support_need", 0.0)) > 0
    assert report.get("frontend_component_coverage") == 1.0
    assert "score" in report.get("evidence_fields_used", [])
    assert "mastery_score" in report.get("evidence_fields_used", [])
    assert "behaviour_risk" in report.get("evidence_fields_used", [])
    assert report.get("limitations")
    assert MD_REPORT.exists()

    print("STATUS: success")
    print("MODULE: adaptive_hint_policy_report_check")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
