import argparse
import json

from src.cognitutor_lm_config import PACKET_OUTPUT, ROOT
from src.concept_resource_loader import find_concept, safe_name


PREVIEW_DIR = ROOT / "outputs" / "model_generated" / "previews"


def print_packet(packet):
    tc = packet["teaching_content"]
    print(f"=== PACKET: {packet['domain']} / {packet['concept_name']} / {packet['difficulty'].upper()} / {packet['teaching_view']} ===")
    print(f"SOURCE LEVEL: {packet.get('source_level')}")
    print(f"CONTENT SECTIONS USED: {', '.join(packet.get('content_sections_used') or [])}")
    print(f"TITLE: {tc['title']}")
    print(f"LEARNING GOAL: {tc.get('learning_goal', '')}")
    print("BEGINNER EXPLANATION:")
    print(f"  {tc['beginner_explanation']}")
    print(f"DEFINITION: {tc['definition']}")
    print(f"WHY IT MATTERS: {tc['why_it_matters']}")
    print("STEP BY STEP:")
    for idx, step in enumerate(tc["step_by_step"], start=1):
        print(f"  {idx}. {step}")
    print(f"EXAMPLE: {tc['example']}")
    print(f"COMMON MISTAKE: {tc['common_mistake']}")
    print(f"QUICK CHECK: {tc['quick_check']}")
    print(f"REVISION LINE: {tc['revision_line']}")
    for idx, assessment in enumerate(packet["aligned_assessments"], start=1):
        print(f"--- ALIGNED ASSESSMENT {idx} ---")
        print(f"Type: {assessment['task_type']}")
        print(f"Source level: {assessment.get('source_level')}")
        print(f"Linked teaching view: {assessment.get('linked_teaching_view')}")
        print(f"Linked content points: {assessment.get('linked_content_points')}")
        print(f"Question: {assessment['question']}")
        for option in assessment.get("options", []):
            print(option)
        print(f"Answer: {assessment['answer']}")
        print(f"Explanation: {assessment['explanation']}")
        print(f"Alignment reason: {assessment['alignment_reason']}")
    print("--- HINT ---")
    print(packet["hint"])
    print("--- FEEDBACK ---")
    print(f"Correct: {packet['feedback_template']['correct']}")
    print(f"Partial: {packet['feedback_template']['partial']}")
    print(f"Wrong: {packet['feedback_template']['wrong']}")
    print("--- REVISION SUMMARY ---")
    print(packet["revision_summary"])
    print("--- NEXT STEP ---")
    print(packet["next_step"])
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()
    concept = find_concept(args.domain, args.concept)
    packets = json.loads(PACKET_OUTPUT.read_text(encoding="utf-8")) if PACKET_OUTPUT.exists() else []
    if not concept:
        print("status: not_found")
        return
    packets = [p for p in packets if p["domain"] == concept["domain"] and p["concept_id"] == concept["concept_id"]]
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = PREVIEW_DIR / f"learning_packets_{safe_name(args.domain)}_{safe_name(args.concept)}.md"
    lines = []
    grouped = {difficulty: [p for p in packets if p.get("difficulty") == difficulty] for difficulty in ["easy", "medium", "hard", "revision"]}
    for difficulty, rows in grouped.items():
        if not rows:
            continue
        heading = f"{difficulty.upper()} PACKETS"
        print(f"\n{heading}")
        lines.extend([f"# {heading}", ""])
        for packet in rows:
            tc = packet["teaching_content"]
            lines.extend(
                [
                    f"## {packet['domain']} / {packet['concept_name']} / {packet['difficulty'].upper()} / {packet['teaching_view']}",
                    f"Source level: {packet.get('source_level')}",
                    f"Content sections used: {', '.join(packet.get('content_sections_used') or [])}",
                    "",
                    tc["beginner_explanation"],
                    "",
                ]
            )
            print_packet(packet)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"preview_saved: {path}")


if __name__ == "__main__":
    main()
