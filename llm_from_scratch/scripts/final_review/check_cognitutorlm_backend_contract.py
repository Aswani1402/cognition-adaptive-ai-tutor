import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.guarded_generation_service import generate_guarded_tutor_output

try:
    import torch

    torch.manual_seed(11)
except Exception:
    pass


OUT_JSON = ROOT / "evaluation_outputs" / "json" / "final_cognitutorlm_backend_contract_check.json"
OUT_REPORT = ROOT / "evaluation_outputs" / "reports" / "final_cognitutorlm_backend_contract_check_report.md"


CASES = [
    {"task_type": "explanation", "concept_id": "P1", "concept_name": "Variables", "subject": "Python", "difficulty": "easy"},
    {"task_type": "mcq", "concept_id": "S2", "concept_name": "SQL SELECT Queries", "subject": "SQL", "difficulty": "easy"},
    {"task_type": "flashcard", "concept_id": "H2", "concept_name": "HTML Tags and Elements", "subject": "HTML", "difficulty": "easy"},
    {"task_type": "hint", "concept_id": "G3", "concept_name": "Commits and History", "subject": "Git", "difficulty": "easy"},
    {"task_type": "output_prediction", "concept_id": "D1", "concept_name": "Arrays", "subject": "Data Structures", "difficulty": "easy"},
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def compact_packet(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task_type": result.get("task_type"),
        "concept_id": result.get("concept_id"),
        "concept_name": result.get("concept_name"),
        "subject": result.get("subject"),
        "difficulty": result.get("difficulty"),
        "content": result.get("final_output"),
        "source": result.get("fallback_source") if result.get("fallback_used") else "raw_cognitutor_lm_validated",
        "model_attempted": result.get("model_attempted"),
        "fallback_used": result.get("fallback_used"),
        "validation_summary": {
            "final_valid": result.get("final_valid"),
            "grounding_pass": result.get("grounding_pass"),
            "repetition_pass": result.get("repetition_pass"),
            "format_pass": result.get("format_pass"),
            "raw_valid": result.get("raw_valid"),
            "raw_validation_errors": result.get("validation_errors") or [],
        },
        "learner_facing_safe": result.get("learner_facing_safe"),
    }


def render_report(payload: Dict[str, Any]) -> str:
    lines = [
        "# Final CogniTutorLM Backend Contract Check",
        "",
        f"- Generated at: `{payload['generated_at']}`",
        f"- Packets checked: `{len(payload['packets'])}`",
        f"- Learner-facing safe packets: `{sum(1 for p in payload['packets'] if p['learner_facing_safe'])}`",
        "",
        "## Required Backend Packet Fields",
        "",
        "`task_type`, `concept_id`, `concept_name`, `subject`, `difficulty`, `content`, `source`, `model_attempted`, `fallback_used`, `validation_summary`, `learner_facing_safe`",
        "",
        "## Packets",
        "",
    ]
    for packet in payload["packets"]:
        lines.append(
            f"- `{packet['subject']} / {packet['concept_name']} / {packet['task_type']}`: "
            f"source={packet['source']}, model_attempted={packet['model_attempted']}, "
            f"fallback_used={packet['fallback_used']}, safe={packet['learner_facing_safe']}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)

    packets: List[Dict[str, Any]] = []
    full_results: List[Dict[str, Any]] = []
    for case in CASES:
        result = generate_guarded_tutor_output(**case, learner_state={"hint_level": "guided"}, prefer_model=True)
        full_results.append(result)
        packets.append(compact_packet(result))
        print(
            f"{case['subject']} | {case['concept_name']} | {case['task_type']} | "
            f"safe={result['learner_facing_safe']} source={packets[-1]['source']}"
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "packets": packets,
        "full_guarded_results": full_results,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_REPORT.write_text(render_report(payload), encoding="utf-8")

    print("")
    print("Backend contract check complete.")
    print(f"JSON: {rel(OUT_JSON)}")
    print(f"Report: {rel(OUT_REPORT)}")


if __name__ == "__main__":
    main()
