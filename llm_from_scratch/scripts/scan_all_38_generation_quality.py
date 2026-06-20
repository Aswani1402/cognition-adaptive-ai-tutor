import json
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path("outputs/model_generated/structured_model_generated_core.json")
OUT_JSON = Path("outputs/final_reports/all_38_concept_generation_quality_scan.json")
OUT_MD = Path("outputs/final_reports/all_38_concept_generation_quality_scan.md")

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))

concepts = defaultdict(list)
for item in data:
    concepts[(item["domain"], item["concept_id"], item["concept_name"])].append(item)

bad_patterns = [
    "remove_wrong",
    "wrong_item",
    "Progr.",
    " becom.",
    " th.",
    " st.",
    " elemen.",
    " and l.",
    " Comp.",
]

report = []
bad_rows = []

for (domain, concept_id, concept_name), items in sorted(concepts.items()):
    issues = []

    if len(items) != 12:
        issues.append({
            "type": "task_count_not_12",
            "task_count": len(items),
        })

    for item in sorted(items, key=lambda x: x["task_type"]):
        output = str(item.get("output", ""))
        found_patterns = [p for p in bad_patterns if p in output]
        valid = bool(item.get("valid"))
        quality = float(item.get("quality_score", 0.0))

        # Detect Python-list-as-text only when it appears in prose, not valid code like graph['A'].
        list_string_artifact = False
        if item["task_type"] not in {"debug_task", "output_prediction"}:
            if "['" in output or "']" in output:
                list_string_artifact = True

        if found_patterns or list_string_artifact or not valid or quality < 0.85:
            issue = {
                "task_type": item["task_type"],
                "valid": valid,
                "quality_score": quality,
                "patterns": found_patterns + (["list_string_artifact"] if list_string_artifact else []),
                "preview": output[:700],
            }
            issues.append(issue)
            bad_rows.append({
                "domain": domain,
                "concept_id": concept_id,
                "concept_name": concept_name,
                **issue,
            })

    report.append({
        "domain": domain,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "task_count": len(items),
        "issue_count": len(issues),
        "status": "PASS" if len(items) == 12 and len(issues) == 0 else "CHECK",
        "issues": issues,
    })

OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

lines = ["# All 38 Concept Generation Quality Scan", ""]
lines.append(f"- total_items: {len(data)}")
lines.append(f"- concept_count: {len(concepts)}")
lines.append(f"- concepts_with_issues: {sum(1 for r in report if r['status'] != 'PASS')}")
lines.append(f"- total_bad_rows: {len(bad_rows)}")
lines.append("")

for row in report:
    lines.append(f"## {row['domain']} - {row['concept_id']} - {row['concept_name']} [{row['status']}]")
    lines.append(f"- task_count: {row['task_count']}")
    lines.append(f"- issue_count: {row['issue_count']}")
    for issue in row["issues"][:12]:
        lines.append(f"  - {issue}")
    lines.append("")

OUT_MD.write_text("\n".join(lines), encoding="utf-8")

print("saved_json:", OUT_JSON)
print("saved_md:", OUT_MD)
print("total_items:", len(data))
print("concept_count:", len(concepts))
print("concepts_with_issues:", sum(1 for r in report if r["status"] != "PASS"))
print("total_bad_rows:", len(bad_rows))

for bad in bad_rows[:80]:
    print("\nBAD:", bad["domain"], bad["concept_id"], bad["concept_name"], bad["task_type"])
    print("patterns:", bad["patterns"])
    print("valid:", bad["valid"], "quality:", bad["quality_score"])
    print("preview:", bad["preview"][:500])
