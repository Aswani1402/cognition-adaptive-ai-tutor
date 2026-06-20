from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


CSV_INPUT = Path("evaluation_outputs/csv/kt_training_sequences.csv")
ID_MAP_OUTPUT = Path("models/dkt/id_map.json")
JSON_REPORT = Path("evaluation_outputs/json/kt_skill_item_map_summary.json")
MD_REPORT = Path("evaluation_outputs/reports/kt_skill_item_map_summary.md")


def _ensure_training_data() -> None:
    if not CSV_INPUT.exists():
        from scripts.training.kt.prepare_kt_training_data import prepare_sequences

        prepare_sequences()


def _load_rows() -> list[dict[str, Any]]:
    _ensure_training_data()
    with CSV_INPUT.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_skill_item_map() -> dict[str, Any]:
    rows = _load_rows()
    concept_values = [str(row.get("concept_id", "")).strip() for row in rows]
    concepts = sorted({value for value in concept_values if value}, key=lambda item: (len(item), item))
    concept_to_idx = {concept_id: index + 1 for index, concept_id in enumerate(concepts)}
    idx_to_concept = {str(value): key for key, value in concept_to_idx.items()}

    item_values = [str(row.get("question_id", "")).strip() for row in rows if str(row.get("question_id", "")).strip()]
    items = sorted(set(item_values), key=lambda item: (len(item), item))
    item_to_idx = {item_id: index + 1 for index, item_id in enumerate(items)}

    concept_metadata = {
        concept_id: {
            "domain": "",
            "concept_name": "",
        }
        for concept_id in concepts
    }

    id_map = {
        "schema_version": "current_tutor_kt_v1",
        "source": "tutor_db_quiz_results",
        "training_csv": str(CSV_INPUT),
        "concept_to_idx": concept_to_idx,
        "idx_to_concept": idx_to_concept,
        "item_to_idx": item_to_idx,
        "idx_to_item": {str(value): key for key, value in item_to_idx.items()},
        "num_concepts": len(concept_to_idx) + 1,
        "num_items": len(item_to_idx) + 1 if item_to_idx else 0,
        "concept_metadata": concept_metadata,
        "skill2idx": concept_to_idx,
        "idx2skill": idx_to_concept,
        "num_skills": len(concept_to_idx) + 1,
    }

    ID_MAP_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    ID_MAP_OUTPUT.write_text(json.dumps(id_map, indent=2), encoding="utf-8")

    null_concepts = sum(1 for value in concept_values if not value)
    concept_counts = Counter(concept_values)
    summary = {
        "status": "success",
        "module": "kt_skill_item_map_builder",
        "source_csv": str(CSV_INPUT),
        "id_map_output": str(ID_MAP_OUTPUT),
        "row_count": len(rows),
        "concept_count": len(concepts),
        "item_question_count": len(items),
        "unmapped_null_concept_count": null_concepts,
        "matches_current_tutor_concepts": bool(concepts) and len(concepts) <= 60,
        "sample_concept_mappings": dict(list(concept_to_idx.items())[:10]),
        "sample_item_mappings": dict(list(item_to_idx.items())[:10]),
        "most_common_concepts": concept_counts.most_common(10),
        "compatibility_aliases": ["skill2idx", "idx2skill", "num_skills"],
        "old_phase1_artifact_note": (
            "Old AI_TUTOR EdNet/ASSISTments artifacts are not used for this map because their skill IDs "
            "do not represent the current tutor concepts."
        ),
    }

    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# KT Skill/Item Map Summary",
        "",
        f"Status: **{summary['status']}**",
        "",
        f"- Source CSV: `{CSV_INPUT}`",
        f"- ID map: `{ID_MAP_OUTPUT}`",
        f"- Rows: {summary['row_count']}",
        f"- Concepts: {summary['concept_count']}",
        f"- Items/questions: {summary['item_question_count']}",
        f"- Null concepts: {summary['unmapped_null_concept_count']}",
        "",
        "## Sample Concept Mappings",
        "",
    ]
    for concept_id, idx in summary["sample_concept_mappings"].items():
        lines.append(f"- `{concept_id}` -> `{idx}`")
    lines.extend(["", "## Note", "", summary["old_phase1_artifact_note"]])
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    summary = build_skill_item_map()
    print("STATUS: success")
    print("MODULE: kt_skill_item_map_builder")
    print(f"ID_MAP: {ID_MAP_OUTPUT}")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
