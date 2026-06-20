import csv
import json
from collections import defaultdict

from scripts.structured_generation_common import ROOT_DIR


CORE = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
OUT_JSON = ROOT_DIR / "outputs" / "evaluation" / "human_review_sample_structured_core.json"
OUT_MD = ROOT_DIR / "outputs" / "evaluation" / "human_review_sample_structured_core.md"
OUT_CSV = ROOT_DIR / "outputs" / "evaluation" / "human_review_sample_structured_core.csv"


def main() -> None:
    items = json.loads(CORE.read_text(encoding="utf-8")) if CORE.exists() else []
    by_domain = defaultdict(list)
    for item in items:
        by_domain[item.get("domain")].append(item)
    selected = []
    seen = set()
    for domain in sorted(by_domain):
        concepts = []
        for item in by_domain[domain]:
            cid = item.get("concept_id")
            if cid not in concepts:
                concepts.append(cid)
        for cid in concepts[:3]:
            for item in by_domain[domain]:
                if item.get("concept_id") == cid and item.get("item_id") not in seen:
                    selected.append(item)
                    seen.add(item.get("item_id"))
                    if len([x for x in selected if x.get("domain") == domain and x.get("concept_id") == cid]) >= 4:
                        break
    covered_tasks = {item.get("task_type") for item in selected}
    for item in items:
        if item.get("task_type") not in covered_tasks and item.get("item_id") not in seen:
            selected.append(item)
            seen.add(item.get("item_id"))
            covered_tasks.add(item.get("task_type"))
    selected = selected[:60]

    review_rows = [
        {
            "item_id": item.get("item_id"),
            "domain": item.get("domain"),
            "concept_name": item.get("concept_name"),
            "task_type": item.get("task_type"),
            "output": item.get("output"),
            "auto_valid": item.get("valid"),
            "auto_quality_score": item.get("quality_score"),
            "human_correctness_score": "",
            "human_teaching_usefulness_score": "",
            "human_format_score": "",
            "human_notes": "",
        }
        for item in selected
    ]
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(review_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(review_rows[0].keys()) if review_rows else [])
        writer.writeheader()
        writer.writerows(review_rows)
    OUT_MD.write_text(
        "# Human Review Sample - Structured Core\n\n"
        "Scoring scale: 1 = poor, 2 = weak, 3 = acceptable, 4 = good, 5 = excellent.\n\n"
        + "\n".join(f"- {row['item_id']} | {row['domain']} | {row['concept_name']} | {row['task_type']}" for row in review_rows)
        + "\n",
        encoding="utf-8",
    )
    print(f"sample_count: {len(review_rows)}")
    print(f"json_path: {OUT_JSON}")
    print(f"csv_path: {OUT_CSV}")


if __name__ == "__main__":
    main()
