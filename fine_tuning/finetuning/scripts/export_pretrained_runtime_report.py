from __future__ import annotations

import json

from scripts.inspect_pretrained_finetune import (
    REPORT_JSON,
    REPORT_MD,
    inspect_project,
    render_markdown,
)
from scripts.run_pretrained_local_inference import run_inference


def render_export_markdown(report: dict, inference: dict) -> str:
    base_markdown = render_markdown(report).rstrip()
    status = "available" if inference.get("available") else "unavailable"
    reason = inference.get("reason") or "none"
    next_step = report.get("next_step")

    return "\n".join(
        [
            base_markdown,
            "",
            "## Runtime inference check",
            "",
            f"- Inference runnable: `{inference.get('available')}`",
            f"- Runtime status: `{status}`",
            f"- Reason: `{reason}`",
            f"- Exact next step needed: {next_step}",
            "",
            "Pretrained's fine-tuned LLM folder contains LoRA adapter checkpoints and inference-related scripts, but no complete local base model or merged model folder was detected. Since external downloads are disabled, the model cannot be safely run for local comparison yet. To enable runtime comparison, the matching base model must be placed locally and configured in pretrained_inference_config.json, or the LoRA adapter must be merged into a full local model artifact."
            if not inference.get("available")
            else "Pretrained local inference is available with the configured local model artifacts.",
            "",
        ]
    )


def export_report() -> dict:
    report = inspect_project(write_report=False)
    inference = run_inference(
        task="explanation",
        concept="Python Variables",
        prompt="Explain Python variables for a beginner.",
    )

    report["runtime_inference_check"] = inference
    report["inference_runnable"] = bool(inference.get("available"))
    if not inference.get("available"):
        report["reason"] = inference.get("reason")
        report["what_is_missing"] = (
            "A complete matching local base model folder or merged model folder."
        )
        report["exact_next_step_needed"] = report["next_step"]
    else:
        report["reason"] = None
        report["what_is_missing"] = None
        report["exact_next_step_needed"] = (
            "Call scripts/run_pretrained_local_inference.py through subprocess."
        )

    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    REPORT_MD.write_text(
        render_export_markdown(report, inference),
        encoding="utf-8",
    )
    return report


def main() -> None:
    report = export_report()
    print(
        json.dumps(
            {
                "status": report["status"],
                "module": "export_pretrained_runtime_report",
                "report_md": REPORT_MD.name,
                "report_json": REPORT_JSON.name,
                "inference_runnable": report["inference_runnable"],
                "reason": report.get("reason"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
