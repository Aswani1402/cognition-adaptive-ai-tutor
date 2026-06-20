from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


REPORT_PATH = Path("evaluation_outputs/json/voice_script_report.json")
CHART_DIR = Path("evaluation_outputs/charts")
JSON_REPORT = Path("evaluation_outputs/json/voice_script_visualization_report.json")
MD_REPORT = Path("evaluation_outputs/reports/voice_script_visualization_report.md")


def _ensure_report() -> dict:
    if not REPORT_PATH.exists():
        from scripts.test_voice_script_generator import build_report, write_reports

        report = build_report()
        write_reports(report)
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def _save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def generate_charts() -> dict:
    report = _ensure_report()
    CHART_DIR.mkdir(parents=True, exist_ok=True)

    scripts = report.get("scripts", [])
    script_types = [script.get("script_type") for script in scripts]
    word_counts = [len(script.get("text", "").split()) for script in scripts]
    tts_ready_count = sum(1 for script in scripts if script.get("tts_ready") is True)
    not_ready_count = len(scripts) - tts_ready_count

    type_path = CHART_DIR / "voice_script_type_distribution.png"
    type_distribution = {script_type: script_types.count(script_type) for script_type in script_types}
    plt.figure(figsize=(10, 4.5))
    plt.bar(list(type_distribution.keys()), list(type_distribution.values()))
    plt.xticks(rotation=30, ha="right")
    plt.title("Voice Script Type Distribution")
    plt.ylabel("Script count")
    _save(type_path)

    word_path = CHART_DIR / "voice_script_word_count.png"
    plt.figure(figsize=(10, 4.5))
    plt.bar(script_types, word_counts)
    plt.xticks(rotation=30, ha="right")
    plt.title("Voice Script Word Count")
    plt.ylabel("Words")
    _save(word_path)

    tts_path = CHART_DIR / "voice_script_tts_ready_rate.png"
    plt.figure(figsize=(5.5, 4.5))
    plt.bar(["tts_ready", "not_ready"], [tts_ready_count, not_ready_count])
    plt.title("Voice Script TTS Ready Rate")
    plt.ylabel("Script count")
    _save(tts_path)

    chart_report = {
        "status": "success",
        "module": "voice_script_visualization_report",
        "chart_dir": str(CHART_DIR),
        "charts": {
            "voice_script_type_distribution": str(type_path),
            "voice_script_word_count": str(word_path),
            "voice_script_tts_ready_rate": str(tts_path),
        },
        "source_report": str(REPORT_PATH),
    }
    return chart_report


def write_reports(report: dict) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# Voice Script Chart Report",
        "",
        f"Status: **{report['status']}**",
        "",
        f"Chart directory: `{report['chart_dir']}`",
        "",
        "## Charts",
        "",
    ]
    for name, path in report["charts"].items():
        lines.append(f"- {name}: `{path}`")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = generate_charts()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: voice_script_visualization_report")
    print(f"CHART_DIR: {CHART_DIR}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
