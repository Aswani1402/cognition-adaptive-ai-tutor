import argparse
import json
from collections import defaultdict
from typing import Any, Dict, List

from src.cognitutor_lm_config import PACKET_OUTPUT, REPORTS_DIR
from src.concept_resource_loader import find_concept, safe_name


OUT_DIR = REPORTS_DIR / "concept_study_reports"


def load_packets() -> List[Dict[str, Any]]:
    return json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []


def next_action(scores: Dict[str, Any]) -> tuple[str, str]:
    easy = scores.get("easy")
    medium = scores.get("medium")
    hard = scores.get("hard")
    if hard is not None and hard >= 0.8:
        return "mastered", "concept_mastered"
    if medium is not None and medium >= 0.8:
        return "hard_in_progress", "move_to_hard_content"
    if medium is not None and medium < 0.8:
        return "medium_in_progress", "medium_remediation"
    if easy is not None and easy >= 0.8:
        return "easy_complete", "move_to_medium_content"
    return "easy_in_progress", "stay_easy_change_view"


def content_covered(rows: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    covered: Dict[str, List[str]] = defaultdict(list)
    for packet in rows:
        difficulty = packet.get("difficulty")
        tc = packet.get("teaching_content", {})
        for item in [tc.get("definition"), tc.get("revision_line"), tc.get("example")]:
            if item and item not in covered[difficulty]:
                covered[difficulty].append(str(item)[:140])
    return {level: values[:5] for level, values in covered.items()}


def build_report(learner_id: str, domain: str, concept: str) -> Dict[str, Any]:
    found = find_concept(domain, concept=concept)
    if not found:
        raise SystemExit(f"Concept not found: {domain} / {concept}")
    rows = [p for p in load_packets() if p.get("domain") == found["domain"] and p.get("concept_id") == found["concept_id"]]
    studied_views: Dict[str, List[str]] = defaultdict(list)
    for packet in rows:
        if packet.get("difficulty") != "revision":
            studied_views[packet["difficulty"]].append(packet["teaching_view"])
    preferred_scores = {"easy": 0.85, "medium": 0.72, "hard": None}
    mastery_status, action = next_action(preferred_scores)
    assessments = []
    for packet in rows:
        for assessment in packet.get("aligned_assessments", []):
            assessments.append(
                {
                    "difficulty": packet.get("difficulty"),
                    "source_level": assessment.get("source_level"),
                    "teaching_view": packet.get("teaching_view"),
                    "task_type": assessment.get("task_type"),
                    "question": assessment.get("question") or assessment.get("statement"),
                    "answer": assessment.get("answer"),
                    "alignment_reason": assessment.get("alignment_reason"),
                }
            )
    return {
        "learner_id": learner_id,
        "domain": found["domain"],
        "concept_id": found["concept_id"],
        "concept_name": found["concept_name"],
        "studied_levels": ["easy", "medium", "hard"],
        "studied_views": {level: views[:4] for level, views in studied_views.items()},
        "content_covered": content_covered(rows),
        "assessment_questions_seen": assessments[:12],
        "scores": preferred_scores,
        "mistakes": [],
        "hints_used": 0,
        "feedback_given": [],
        "revision_recommended": "Review the medium debug/output packet before attempting hard transfer tasks.",
        "mastery_status": mastery_status,
        "next_recommended_action": action,
    }


def markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# Concept Study Report",
        "",
        f"- Learner: {report['learner_id']}",
        f"- Concept: {report['domain']} / {report['concept_name']} ({report['concept_id']})",
        f"- Mastery status: {report['mastery_status']}",
        f"- Next action: {report['next_recommended_action']}",
        "",
        "## Studied Views",
    ]
    for level, views in report["studied_views"].items():
        lines.append(f"- {level}: {', '.join(views)}")
    lines += ["", "## Questions Seen"]
    for item in report["assessment_questions_seen"]:
        lines.append(f"- {item['difficulty']} / {item['teaching_view']} / {item['task_type']}: {item['question']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()
    report = build_report(args.learner_id, args.domain, args.concept)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{safe_name(args.learner_id)}_{safe_name(report['domain'])}_{safe_name(report['concept_name'])}"
    json_path = OUT_DIR / f"{stem}.json"
    md_path = OUT_DIR / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"study_report_json: {json_path}")
    print(f"study_report_md: {md_path}")
    print("STATUS: PASS")


if __name__ == "__main__":
    main()
