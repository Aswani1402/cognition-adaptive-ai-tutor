from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from tutor.generation.voice_script_generator import VOICE_SCRIPT_TYPES, VoiceScriptGenerator


JSON_REPORT = Path("evaluation_outputs/json/voice_script_report.json")
MD_REPORT = Path("evaluation_outputs/reports/voice_script_report.md")


SAMPLE_EVIDENCE = {
    "concept_name": "Python Variables",
    "teaching_view": "definition_view",
    "difficulty": "easy",
    "learner_level": "beginner",
    "mistake_type": "variable_naming_error",
    "weakest_skill": "syntax accuracy",
    "evaluation_label": "partial",
    "doubt_intent": "debug_doubt",
    "next_action": "answer a naming-rule practice question",
    "key_points": [
        "A variable is a name linked to a value.",
        "Python variable names cannot start with a number.",
        "Use clear names that describe the value.",
    ],
    "example": "score = 10 stores the value 10 using the name score.",
}


def build_report() -> dict:
    generator = VoiceScriptGenerator()
    scripts = [
        generator.generate(script_type=script_type, evidence=SAMPLE_EVIDENCE)
        for script_type in sorted(VOICE_SCRIPT_TYPES)
    ]

    script_count = len(scripts)
    word_counts = [len(script.get("text", "").split()) for script in scripts]
    type_counts = Counter(script.get("script_type") for script in scripts)
    tts_ready_count = sum(1 for script in scripts if script.get("tts_ready") is True)
    empty_count = sum(1 for script in scripts if not script.get("text"))
    component_count = sum(
        1 for script in scripts if script.get("frontend_component") == "VoiceScriptCard"
    )

    report = {
        "status": "success",
        "module": "voice_script_generator_test",
        "script_count": script_count,
        "script_type_coverage": {
            "covered": sorted(type_counts.keys()),
            "expected": sorted(VOICE_SCRIPT_TYPES),
            "coverage_rate": round(len(type_counts) / len(VOICE_SCRIPT_TYPES), 6),
        },
        "average_word_count": round(sum(word_counts) / script_count, 3),
        "word_counts": dict(zip([script["script_type"] for script in scripts], word_counts)),
        "tts_ready_rate": round(tts_ready_count / script_count, 6),
        "empty_script_rate": round(empty_count / script_count, 6),
        "frontend_component_coverage": round(component_count / script_count, 6),
        "scripts": scripts,
        "final_report_wording": (
            "The voice module generates TTS-ready teaching, revision, feedback, "
            "and doubt explanation scripts. It does not synthesize audio directly; instead, "
            "it prepares learner-friendly spoken text that can be connected to browser "
            "Text-to-Speech or a speech service in the frontend."
        ),
        "limitations": [
            "No external TTS is used.",
            "No audio files are generated.",
            "Scripts are deterministic templates grounded in supplied tutor evidence.",
        ],
    }
    return report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Voice Script Report",
        "",
        f"Status: **{report['status']}**",
        "",
        report["final_report_wording"],
        "",
        f"- Script count: {report['script_count']}",
        f"- Script type coverage: {report['script_type_coverage']['coverage_rate']}",
        f"- Average word count: {report['average_word_count']}",
        f"- TTS-ready rate: {report['tts_ready_rate']}",
        f"- Empty script rate: {report['empty_script_rate']}",
        f"- Frontend component coverage: {report['frontend_component_coverage']}",
        "",
        "## Script Types",
        "",
    ]
    for script_type in report["script_type_coverage"]["covered"]:
        lines.append(f"- {script_type}")
    lines.extend(["", "## Limitations", ""])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)

    assert report["status"] == "success"
    assert report["module"] == "voice_script_generator_test"
    assert report["script_count"] == len(VOICE_SCRIPT_TYPES)
    assert report["script_type_coverage"]["coverage_rate"] == 1.0
    assert report["tts_ready_rate"] == 1.0
    assert report["empty_script_rate"] == 0.0
    assert report["frontend_component_coverage"] == 1.0
    for script in report["scripts"]:
        assert script["status"] == "success"
        assert script["module"] == "VoiceScriptGenerator"
        assert script["text"]
        assert script["tts_ready"] is True
        assert script["estimated_duration_sec"] > 0
        assert script["tone"] == "supportive"
        assert script["frontend_component"] == "VoiceScriptCard"

    print("STATUS: success")
    print("MODULE: voice_script_generator_test")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
