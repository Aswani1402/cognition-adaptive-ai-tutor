from __future__ import annotations

import json
from pathlib import Path


JSON_REPORT = Path("evaluation_outputs/json/voice_script_report.json")
MD_REPORT = Path("evaluation_outputs/reports/voice_script_report.md")

EXPECTED_SCRIPT_TYPES = {
    "teaching_explanation",
    "revision_summary",
    "mistake_feedback",
    "doubt_explanation",
    "encouragement",
    "next_step_guidance",
}


def _ensure_report() -> dict:
    if not JSON_REPORT.exists() or not MD_REPORT.exists():
        from scripts.test_voice_script_generator import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(JSON_REPORT.read_text(encoding="utf-8"))


def main() -> None:
    report = _ensure_report()
    covered = set((report.get("script_type_coverage") or {}).get("covered") or [])

    assert report.get("status") == "success"
    assert report.get("module") == "voice_script_generator_test"
    assert report.get("script_count") == len(EXPECTED_SCRIPT_TYPES)
    assert covered == EXPECTED_SCRIPT_TYPES
    assert float(report.get("average_word_count", 0)) > 0
    assert report.get("tts_ready_rate") == 1.0
    assert report.get("empty_script_rate") == 0.0
    assert report.get("frontend_component_coverage") == 1.0
    assert MD_REPORT.exists()

    print("STATUS: success")
    print("MODULE: voice_script_report_check")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
