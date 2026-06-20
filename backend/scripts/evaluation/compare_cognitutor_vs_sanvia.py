from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from tutor.generation.llm_generation_comparator import LLMGenerationComparator


ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "cognitutor_vs_sanvia_comparison_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "cognitutor_vs_sanvia_comparison_report.md"
NOTES = ROOT / "docs" / "llm_comparison_notes.md"


def _table(headers: List[str], rows: List[List[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell).replace("\n", " ") for cell in row) + " |")
    return "\n".join(out)


def _write_notes(report: Dict[str, Any]) -> None:
    inspection = report["sanvia_inspection"]
    lines = [
        "# LLM Comparison Notes",
        "",
        "## Sanvia Folder Structure Summary",
        f"- Project path: `{inspection.get('project_path')}`",
        f"- Folder exists: `{inspection.get('folder_exists')}`",
        f"- Detected inference scripts: `{', '.join(inspection.get('inference_scripts') or []) or 'none'}`",
        f"- Detected config files: `{', '.join(inspection.get('config_files') or []) or 'none'}`",
        "",
        "## Detected Model Artifacts",
        f"- HuggingFace full local model folders: `{', '.join(inspection.get('hf_model_dirs') or []) or 'none'}`",
        f"- LoRA adapter folders: `{', '.join(inspection.get('lora_adapter_dirs') or []) or 'none'}`",
        "",
        "## Detected Inference Method",
        "- Sanvia includes `tutor/llm_finetune/pretrained_generator.py` and `model_loader.py`.",
        "- The loader applies a LoRA adapter to a configured base model and supports offline mode.",
        "",
        "## Runnable Status",
        f"- Available: `{report['services']['sanvia_pretrained_finetuned_llm'].get('available')}`",
        f"- Reason: `{report['services']['sanvia_pretrained_finetuned_llm'].get('reason')}`",
        "",
        "## Missing Requirements",
        "- A complete local base model path is required for LoRA inference when external downloads are disabled.",
        "- `transformers`, `torch`, and `peft` are required only if Sanvia local inference is attempted.",
        "",
        "## Safe Integration Decision",
        "- Do not replace the current backend generation pipeline.",
        "- Use Sanvia only as an optional comparison service when local model loading succeeds.",
        "- Keep template/RAG fallback active for safety.",
    ]
    NOTES.parent.mkdir(parents=True, exist_ok=True)
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _markdown(report: Dict[str, Any]) -> str:
    services = report["services"]
    availability_rows = [
        [name, data.get("available"), data.get("status"), data.get("connector_mode", data.get("runnable_strategy", "")), data.get("reason", "")]
        for name, data in services.items()
    ]
    avg_rows = [
        [
            service,
            metrics.get("quality_score"),
            metrics.get("grounding_score"),
            metrics.get("format_validity"),
            metrics.get("task_success"),
            metrics.get("latency_ms"),
            metrics.get("fallback_rate"),
        ]
        for service, metrics in report["service_averages"].items()
    ]
    task_rows = []
    for task, best in report["best_service_by_task_type"].items():
        task_rows.append([task, best])
    sampled_rows = [
        [
            row["task_type"],
            row["concept_name"],
            row["service"],
            row["available"],
            row["metrics"]["quality_score"],
            row["metrics"]["format_validity"],
            row["metrics"]["grounding_score"],
            row["metrics"]["fallback_rate"],
        ]
        for row in report["results"][:48]
    ]
    inspection = report["sanvia_inspection"]
    return "\n".join(
        [
            "# CogniTutorLM vs Sanvia LLM Comparison Report",
            "",
            report["evaluation_wording"],
            "",
            "## 1. Service Availability",
            _table(["Service", "Available", "Status", "Mode", "Reason"], availability_rows),
            "",
            "## 2. Sanvia Folder Inspection Summary",
            f"- Project path: `{inspection.get('project_path')}`",
            f"- Inference scripts: `{', '.join(inspection.get('inference_scripts') or []) or 'none'}`",
            f"- LoRA adapter folders: `{', '.join(inspection.get('lora_adapter_dirs') or []) or 'none'}`",
            f"- Full HF model folders: `{', '.join(inspection.get('hf_model_dirs') or []) or 'none'}`",
            f"- Decision reason: `{inspection.get('reason')}`",
            "",
            "## 3. CogniTutorLM Connector Status",
            f"`{json.dumps(services['cognitutor_lm_from_scratch'], ensure_ascii=False)}`",
            "",
            "## 4. Model-Generated vs Fallback/Template Status",
            "- Sanvia outputs are not faked when local inference is unavailable.",
            "- CogniTutorLM status is reported from the current main connector mode.",
            "",
            "## 5. Task-Wise Comparison Table",
            _table(["Task", "Concept", "Service", "Available", "Quality", "Format", "Grounding", "Fallback"], sampled_rows),
            "",
            "## 6. Service-Wise Average Metrics",
            _table(["Service", "Quality", "Grounding", "Format", "Task Success", "Latency ms", "Fallback"], avg_rows),
            "",
            "## 7. Best Service By Task Type",
            _table(["Task Type", "Best Service"], task_rows),
            "",
            "## 8. Latency Comparison",
            "See service-wise average metrics and `llm_comparison_latency.png` after chart generation.",
            "",
            "## 9. Format Validity Comparison",
            "See service-wise average metrics and `llm_comparison_format_validity.png`.",
            "",
            "## 10. Grounding Comparison",
            "See service-wise average metrics and `llm_comparison_grounding.png`.",
            "",
            "## 11. Repetition/Fallback Comparison",
            "See `repetition_rate` and `fallback_rate` metrics in the JSON report.",
            "",
            "## 12. Limitations",
            "\n".join(f"- {item}" for item in report["limitations"]),
            "",
            "## 13. Final Recommendation",
            report["final_recommendation"],
            "",
        ]
    )


def main() -> None:
    comparator = LLMGenerationComparator()
    report = comparator.compare_all()
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_REPORT.write_text(_markdown(report), encoding="utf-8")
    _write_notes(report)
    sanvia_status = "available" if report["services"]["sanvia_pretrained_finetuned_llm"].get("available") else "unavailable"
    if report["services"]["sanvia_pretrained_finetuned_llm"].get("status") == "warning":
        sanvia_status = "warning"
    cog_status = "available" if report["services"]["cognitutor_lm_from_scratch"].get("available") else "unavailable"
    if report["services"]["cognitutor_lm_from_scratch"].get("status") == "warning":
        cog_status = "warning"
    status = "success" if sanvia_status == "available" and cog_status == "available" else "warning"
    print(f"STATUS: {status}")
    print("MODULE: cognitutor_vs_sanvia_comparison")
    print(f"JSON_REPORT: {JSON_REPORT.relative_to(ROOT)}")
    print(f"MD_REPORT: {MD_REPORT.relative_to(ROOT)}")
    print(f"SANVIA_STATUS: {sanvia_status}")
    print(f"COGNITUTOR_STATUS: {cog_status}")


if __name__ == "__main__":
    main()
