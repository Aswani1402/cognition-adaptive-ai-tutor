import argparse
import json
from collections import defaultdict

from src.cognitutor_lm_config import BY_CONCEPT_DIR, ROOT
from src.concept_resource_loader import find_concept, safe_name


def preview_output(value) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text[:420] + ("..." if len(text) > 420 else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True)
    parser.add_argument("--concept", required=True)
    args = parser.parse_args()
    concept = find_concept(args.domain, args.concept)
    if not concept:
        print("status: not_found")
        return
    stem = f"{safe_name(concept['domain'])}_{safe_name(concept['concept_id'])}_{safe_name(concept['concept_name'])}"
    path = BY_CONCEPT_DIR / f"{stem}.json"
    rows = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.get("task_family", "other")].append(row)

    lines = [f"# All Tasks Preview: {concept['domain']} / {concept['concept_id']} / {concept['concept_name']}", "", f"total_tasks: {len(rows)}", ""]
    print(f"domain: {concept['domain']}")
    print(f"concept_id: {concept['concept_id']}")
    print(f"concept_name: {concept['concept_name']}")
    print(f"total_tasks: {len(rows)}")
    for fam in sorted(grouped):
        print(f"\n## {fam.upper()}")
        lines.extend([f"## {fam.upper()}", ""])
        for row in sorted(grouped[fam], key=lambda r: r["task_type"]):
            answer = row.get("answer")
            print(f"- {row['task_type']} | difficulty={row['difficulty']} | source_level={row.get('source_level')} | view={row.get('teaching_view')} | valid={row.get('valid')} | quality={row.get('quality_score')}")
            print(f"  output: {preview_output(row.get('output'))}")
            if answer not in (None, ""):
                print(f"  answer: {answer}")
            print(f"  alignment_reason: {row.get('alignment_reason')}")
            lines.extend(
                [
                    f"### {row['task_type']}",
                    f"- difficulty: {row['difficulty']}",
                    f"- source_level: {row.get('source_level')}",
                    f"- teaching_view: {row.get('teaching_view')}",
                    f"- valid: {row.get('valid')}",
                    f"- quality: {row.get('quality_score')}",
                    f"- answer: {answer}",
                    f"- alignment_reason: {row.get('alignment_reason')}",
                    "",
                    "```json",
                    json.dumps(row.get("output"), indent=2, ensure_ascii=False),
                    "```",
                    "",
                ]
            )
    preview_dir = ROOT / "outputs" / "model_generated" / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview = preview_dir / f"all_tasks_{stem}.md"
    preview.write_text("\n".join(lines), encoding="utf-8")
    print(f"preview_saved: {preview}")


if __name__ == "__main__":
    main()
