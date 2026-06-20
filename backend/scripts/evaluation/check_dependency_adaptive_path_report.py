from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tutor.path.adaptive_path_validation import load_concept_id_map, validate_selected_concept_id
from tutor.system.run_integrated_tutor_once import run_integrated_tutor_once


DB_PATH = Path("external/core_data/tutor.db")
OUTPUT_JSON = Path("evaluation_outputs/json/dependency_adaptive_path_report.json")
OUTPUT_MD = Path("evaluation_outputs/reports/dependency_adaptive_path_report.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect_readonly() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.resolve().as_posix()}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _db_status(concept_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    report = {
        "db_exists": DB_PATH.exists(),
        "concept_id_map_count": len(concept_map),
        "quiz_results_concept_count": 0,
        "quiz_results_unmapped_concept_count": 0,
        "quiz_results_unmapped_concepts": [],
        "status": "warning",
    }
    if not DB_PATH.exists():
        report["status"] = "error"
        return report

    mapped_ids = set(concept_map.keys()) | {
        str(item.get("content_concept_id"))
        for item in concept_map.values()
        if item.get("content_concept_id")
    }
    with _connect_readonly() as conn:
        rows = conn.execute(
            "SELECT CAST(concept_id AS TEXT) AS concept_id, COUNT(*) AS n FROM quiz_results GROUP BY CAST(concept_id AS TEXT)"
        ).fetchall()
    concepts = [str(row["concept_id"]) for row in rows]
    unmapped = sorted(concept for concept in concepts if concept not in mapped_ids)
    report["quiz_results_concept_count"] = len(concepts)
    report["quiz_results_unmapped_concept_count"] = len(unmapped)
    report["quiz_results_unmapped_concepts"] = unmapped[:50]
    report["status"] = "success" if len(concept_map) > 0 else "error"
    return report


def _pipeline_status(concept_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output = run_integrated_tutor_once(learner_id="14", reward_dry_run=True)
    summary = output.get("demo_summary", {}) if isinstance(output.get("demo_summary"), dict) else {}
    validation = output.get("adaptive_path_validation_output", {})
    frontend_path = output.get("frontend_path_output", {}) or summary.get("frontend_path_output", {})
    original = summary.get("adaptive_path_original_selected")
    selected = summary.get("adaptive_path_selected")
    selected_31 = validate_selected_concept_id(
        selected_concept_id="31",
        concept_id_map=concept_map,
        fallback_concept_id=summary.get("resolved_concept_id") or "1",
        current_domain=summary.get("resolved_domain"),
        dependency_output=output.get("dependency_output", {}),
    )

    dependency_safe = bool(validation.get("resolved_concept_id")) and str(selected) in concept_map
    frontend_ready = bool(frontend_path.get("path_nodes")) and bool(frontend_path.get("selected_node"))

    return {
        "status": "success" if dependency_safe and frontend_ready else "warning",
        "pipeline_status": output.get("status", "success"),
        "adaptive_path_selected_before_validation": original,
        "adaptive_path_selected_after_validation": selected,
        "adaptive_path_validation": validation,
        "selected_31_validation": selected_31,
        "is_31_valid_or_corrected": bool(selected_31.get("valid") or selected_31.get("fallback_used")),
        "dependency_safety_status": "success" if dependency_safe else "warning",
        "frontend_path_node_readiness": "success" if frontend_ready else "warning",
        "path_node_count": len(frontend_path.get("path_nodes", [])),
        "selected_node": frontend_path.get("selected_node"),
        "review_due_concepts": frontend_path.get("review_due_concepts", []),
    }


def _overall_status(parts: list[dict[str, Any]]) -> str:
    statuses = [part.get("status") for part in parts]
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "success"


def _build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Dependency Adaptive Path Report",
        "",
        f"Generated at: {report['generated_at']}",
        "",
        f"Overall status: `{report['overall_status']}`",
        "",
        "## Concept Map",
        "",
        f"- concept_id_map count: {report['db_status']['concept_id_map_count']}",
        f"- quiz_results concept count: {report['db_status']['quiz_results_concept_count']}",
        f"- unmapped quiz concept count: {report['db_status']['quiz_results_unmapped_concept_count']}",
        f"- unmapped sample: {report['db_status']['quiz_results_unmapped_concepts']}",
        "",
        "## Adaptive Path Validation",
        "",
        f"- Before validation: {report['pipeline_status']['adaptive_path_selected_before_validation']}",
        f"- After validation: {report['pipeline_status']['adaptive_path_selected_after_validation']}",
        f"- Validation: {report['pipeline_status']['adaptive_path_validation']}",
        f"- 31 valid or corrected: {report['pipeline_status']['is_31_valid_or_corrected']}",
        f"- 31 validation: {report['pipeline_status']['selected_31_validation']}",
        "",
        "## Dependency And Frontend Readiness",
        "",
        f"- Dependency safety status: `{report['pipeline_status']['dependency_safety_status']}`",
        f"- Frontend path node readiness: `{report['pipeline_status']['frontend_path_node_readiness']}`",
        f"- Path node count: {report['pipeline_status']['path_node_count']}",
        f"- Selected node: {report['pipeline_status']['selected_node']}",
        f"- Review due concepts: {report['pipeline_status']['review_due_concepts']}",
        "",
        "## Known Limitations",
        "",
    ]
    for item in report["known_limitations"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Future Upgrade Plan", ""])
    for item in report["future_upgrade_plan"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Status",
            "",
            "```text",
            f"STATUS: {report['overall_status']}",
            "MODULE: dependency_adaptive_path_report",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_report() -> dict[str, Any]:
    concept_map = load_concept_id_map(DB_PATH)
    db_status = _db_status(concept_map)
    pipeline_status = _pipeline_status(concept_map)
    return {
        "overall_status": _overall_status([db_status, pipeline_status]),
        "module": "dependency_adaptive_path_report",
        "generated_at": _now_iso(),
        "db_status": db_status,
        "pipeline_status": pipeline_status,
        "known_limitations": [
            "Adaptive path remains a transparent heuristic scorer, not a learned path ranker.",
            "Cross-domain selections are now corrected/fallback-safe but the graph still spans multiple subject DBs.",
            "Quiz data contains both system and content concept ID styles; reporting tracks unmapped IDs explicitly.",
        ],
        "future_upgrade_plan": [
            "Learned path ranker.",
            "Mastery-aware graph weighting.",
            "Path agreement model.",
            "Frontend concept graph visualization.",
        ],
    }


def main() -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    OUTPUT_MD.write_text(_build_markdown(report), encoding="utf-8")
    print(f"STATUS: {report['overall_status']}")
    print("MODULE: dependency_adaptive_path_report")
    print(f"JSON_REPORT: {OUTPUT_JSON}")
    print(f"MD_REPORT: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
