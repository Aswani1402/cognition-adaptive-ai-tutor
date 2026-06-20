import json
from collections import Counter, defaultdict
from typing import Any, Dict, List

from scripts.structured_generation_common import ROOT_DIR


IN_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core.json"
QUALITY_JSON = ROOT_DIR / "outputs" / "model_generated" / "structured_model_generated_core_quality_report.json"
OUT_JSON = ROOT_DIR / "outputs" / "final_reports" / "all_generated_quality_summary.json"
OUT_MD = ROOT_DIR / "outputs" / "final_reports" / "all_generated_quality_summary.md"


def score(item: Dict[str, Any], key: str) -> float:
    try:
        return float(item.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def rate(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def compact(item: Dict[str, Any], raw: bool = False) -> Dict[str, Any]:
    return {
        "item_id": item.get("item_id"),
        "domain": item.get("domain"),
        "concept_id": item.get("concept_id"),
        "concept_name": item.get("concept_name"),
        "task_type": item.get("task_type"),
        "raw_valid": item.get("raw_valid"),
        "final_valid": item.get("final_valid", item.get("valid")),
        "quality_score": item.get("raw_quality_score" if raw else "final_quality_score", item.get("quality_score")),
        "issues": item.get("raw_issues" if raw else "final_issues", item.get("issues", [])),
        "output": item.get("raw_model_output" if raw else "output", ""),
        "fallback_applied": item.get("fallback_applied"),
    }


def grouped_quality(items: List[Dict[str, Any]], group_key: str) -> Dict[str, Dict[str, Any]]:
    grouped = defaultdict(list)
    for item in items:
        grouped[str(item.get(group_key, "unknown"))].append(item)
    return {
        key: {
            "items": len(rows),
            "raw_valid_rate": rate(sum(1 for item in rows if item.get("raw_valid")), len(rows)),
            "final_valid_rate": rate(sum(1 for item in rows if item.get("final_valid", item.get("valid"))), len(rows)),
            "raw_avg_quality_score": round(sum(score(item, "raw_quality_score") for item in rows) / len(rows), 4),
            "final_avg_quality_score": round(sum(score(item, "final_quality_score") for item in rows) / len(rows), 4),
            "fallback_rate": rate(sum(1 for item in rows if item.get("fallback_applied")), len(rows)),
        }
        for key, rows in sorted(grouped.items())
    }


def build_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    raw_valid = sum(1 for item in items if item.get("raw_valid"))
    final_valid = sum(1 for item in items if item.get("final_valid", item.get("valid")))
    fallback_count = sum(1 for item in items if item.get("fallback_applied"))
    invalid_raw = [item for item in items if not item.get("raw_valid")]
    invalid_final = [item for item in items if not item.get("final_valid", item.get("valid"))]
    quality = json.loads(QUALITY_JSON.read_text(encoding="utf-8")) if QUALITY_JSON.exists() else {}
    q_summary = quality.get("summary", {})
    return {
        "source": str(IN_JSON),
        "total_items": total,
        "raw_valid_count": raw_valid,
        "raw_valid_rate": rate(raw_valid, total),
        "final_valid_count": final_valid,
        "final_valid_rate": rate(final_valid, total),
        "valid_items": final_valid,
        "valid_rate": rate(final_valid, total),
        "invalid_items": len(invalid_final),
        "raw_avg_quality_score": round(sum(score(item, "raw_quality_score") for item in items) / total, 4) if total else 0.0,
        "final_avg_quality_score": round(sum(score(item, "final_quality_score") for item in items) / total, 4) if total else 0.0,
        "fallback_applied_count": fallback_count,
        "fallback_rate": rate(fallback_count, total),
        "invalid_raw_by_task_type": dict(Counter(str(item.get("task_type")) for item in invalid_raw)),
        "invalid_final_by_task_type": dict(Counter(str(item.get("task_type")) for item in invalid_final)),
        "invalid_by_domain": dict(Counter(str(item.get("domain")) for item in invalid_final)),
        "task_wise_quality": grouped_quality(items, "task_type"),
        "domain_wise_quality": grouped_quality(items, "domain"),
        "issues_count": dict(Counter(issue for item in items for issue in item.get("final_issues", item.get("issues", []))).most_common()),
        "raw_issues_count": dict(Counter(issue for item in items for issue in item.get("raw_issues", [])).most_common()),
        "mcq_quality_score": q_summary.get("core_mcq_quality_score"),
        "option_quality_score": q_summary.get("core_option_quality_score"),
        "logical_consistency_score": q_summary.get("core_logical_consistency_score"),
        "website_ready_rate": q_summary.get("core_website_ready_rate"),
        "website_mode_allowed": q_summary.get("website_mode_allowed", False),
        "worst_raw_outputs": [compact(item, raw=True) for item in sorted(items, key=lambda row: score(row, "raw_quality_score"))[:10]],
        "worst_final_outputs": [compact(item, raw=False) for item in sorted(items, key=lambda row: score(row, "final_quality_score"))[:10]],
    }


def write_markdown(summary: Dict[str, Any]) -> None:
    lines = ["# All Generated Quality Summary", ""]
    for key in [
        "total_items",
        "raw_valid_count",
        "raw_valid_rate",
        "final_valid_count",
        "final_valid_rate",
        "raw_avg_quality_score",
        "final_avg_quality_score",
        "fallback_applied_count",
        "fallback_rate",
        "website_ready_rate",
        "mcq_quality_score",
        "option_quality_score",
        "logical_consistency_score",
        "website_mode_allowed",
    ]:
        lines.append(f"- {key}: {summary.get(key)}")
    lines.extend(["", "## Invalid Raw By Task Type", json.dumps(summary["invalid_raw_by_task_type"], ensure_ascii=False), ""])
    lines.extend(["## Invalid Final By Task Type", json.dumps(summary["invalid_final_by_task_type"], ensure_ascii=False), ""])
    lines.append("## Worst Raw Outputs")
    for item in summary["worst_raw_outputs"]:
        lines.extend(["", f"### {item['item_id']}", f"- issues: {item['issues']}", "```text", str(item["output"]), "```"])
    lines.append("")
    lines.append("## Worst Final Outputs")
    for item in summary["worst_final_outputs"]:
        lines.extend(["", f"### {item['item_id']}", f"- issues: {item['issues']}", "```text", str(item["output"]), "```"])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    items = json.loads(IN_JSON.read_text(encoding="utf-8")) if IN_JSON.exists() else []
    summary = build_summary(items)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(summary)
    for key in [
        "total_items",
        "raw_valid_rate",
        "final_valid_rate",
        "fallback_applied_count",
        "fallback_rate",
        "website_ready_rate",
        "mcq_quality_score",
        "option_quality_score",
        "website_mode_allowed",
    ]:
        print(f"{key}: {summary.get(key)}")
    print(f"summary_json: {OUT_JSON}")
    print(f"summary_md: {OUT_MD}")


if __name__ == "__main__":
    main()
