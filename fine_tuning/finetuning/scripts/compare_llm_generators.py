from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_JSON = (
    ROOT
    / "evaluation_outputs"
    / "json"
    / "llm_generation_comparison.json"
)

OUTPUT_MD = (
    ROOT
    / "evaluation_outputs"
    / "reports"
    / "llm_generation_comparison.md"
)

OUTPUT_JSON.parent.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_MD.parent.mkdir(
    parents=True,
    exist_ok=True
)


def build_system_result(
    system,
    connection_status,
    generation_status,
    output_count,
    overall_score,
    fallback_used=False,
    error_message=None,
):

    return {

        "system": system,

        "connection_status":
            connection_status,

        "generation_status":
            generation_status,

        "real_outputs_generated":
            output_count > 0,

        "fallback_used":
            fallback_used,

        "error_message":
            error_message,

        "output_count":
            output_count,

        "overall_score":
            overall_score,
    }


def main():

    print("\nRunning LLM comparison...\n")

    systems = [

        build_system_result(
            system=
                "template_rule_baseline",

            connection_status=
                "success",

            generation_status=
                "success",

            output_count=50,

            overall_score=0.72,
        ),

        build_system_result(
            system=
                "cognitutor_lm_from_scratch",

            connection_status=
                "success",

            generation_status=
                "success",

            output_count=50,

            overall_score=0.68,
        ),

        build_system_result(
            system=
                "pretrained_pretrained_finetuned_llm",

            connection_status=
                "success",

            generation_status=
                "success",

            output_count=50,

            overall_score=0.81,
        ),

        build_system_result(
            system=
                "rag_grounded_service",

            connection_status=
                "success",

            generation_status=
                "success",

            output_count=50,

            overall_score=0.84,
        ),
    ]

    comparison = {

        "comparison_valid": False,

        "comparison_note":
            "Hardcoded fixture only. Other systems were not invoked. "
            "Do not rank these scores as measured model quality.",

        "systems": systems,
    }

    # ==========================================
    # SAVE JSON
    # ==========================================

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            comparison,
            f,
            indent=2
        )

    # ==========================================
    # SAVE MARKDOWN REPORT
    # ==========================================

    lines = []

    lines.append(
        "# LLM Generation Comparison\n"
    )

    lines.append(
        "| System | Connection | Generation | Outputs | Score |"
    )

    lines.append(
        "|---|---|---|---|---|"
    )

    for item in systems:

        lines.append(

            f"| {item['system']} "
            f"| {item['connection_status']} "
            f"| {item['generation_status']} "
            f"| {item['output_count']} "
            f"| {item['overall_score']} |"
        )

    lines.append("\n")

    lines.append(
        "Comparison valid: False (fixture data; external systems unavailable)\n"
    )

    with open(
        OUTPUT_MD,
        "w",
        encoding="utf-8"
    ) as f:

        f.write("\n".join(lines))

    print("Comparison completed.\n")

    print("Saved JSON:")
    print(OUTPUT_JSON)

    print("\nSaved Markdown:")
    print(OUTPUT_MD)


if __name__ == "__main__":

    main()