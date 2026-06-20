from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DKT_REPORT = Path("evaluation_outputs/json/dkt_runtime_training_report.json")
BKT_REPORT = Path("evaluation_outputs/json/bkt_training_report.json")
JSON_REPORT = Path("evaluation_outputs/json/kt_hyperparameter_sensitivity_report.json")
MD_REPORT = Path("evaluation_outputs/reports/kt_hyperparameter_sensitivity_report.md")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_report() -> dict[str, Any]:
    dkt = _load_json(DKT_REPORT)
    bkt = _load_json(BKT_REPORT)
    candidates = dkt.get("hyperparameter_results") or []
    best = dkt.get("best_hyperparameters") or {}
    status = "success" if candidates else "warning"

    effects = []
    for candidate in candidates:
        test = (candidate.get("metrics") or {}).get("test") or {}
        val = (candidate.get("metrics") or {}).get("val") or {}
        effects.append(
            {
                "model_name": candidate.get("name"),
                "embedding_dim": candidate.get("embedding_dim"),
                "hidden_dim": candidate.get("hidden_dim"),
                "learning_rate": candidate.get("learning_rate"),
                "max_seq_len": candidate.get("max_seq_len"),
                "val_log_loss": val.get("log_loss"),
                "val_brier_score": val.get("brier_score"),
                "test_auc": test.get("auc"),
                "test_rmse": test.get("rmse"),
            }
        )

    report = {
        "status": status,
        "module": "kt_hyperparameter_sensitivity_report",
        "selected_default": {
            "runtime_model": "current tutor DKT",
            "best_hyperparameters": best,
            "selection_rule": "lowest validation log loss, with Brier/RMSE checked for calibration.",
        },
        "tested_values": {
            "dkt_embedding_dim": sorted({item.get("embedding_dim") for item in candidates if item.get("embedding_dim") is not None}),
            "dkt_hidden_size": sorted({item.get("hidden_dim") for item in candidates if item.get("hidden_dim") is not None}),
            "dkt_learning_rate": sorted({item.get("learning_rate") for item in candidates if item.get("learning_rate") is not None}),
            "dkt_max_seq_len": sorted({item.get("max_seq_len") for item in candidates if item.get("max_seq_len") is not None}),
            "bkt_parameters": ["p_init", "p_learn", "p_guess", "p_slip"],
        },
        "observed_effects": effects,
        "bkt_parameter_notes": {
            "source": str(BKT_REPORT),
            "model_status": bkt.get("status", "unknown"),
            "notes": (
                "BKT is interpretable and useful as runtime fallback. Higher p_learn raises mastery faster; "
                "higher p_guess inflates predicted correctness for unmastered learners; higher p_slip penalizes "
                "occasional wrong answers less directly in correctness prediction but changes posterior updates."
            ),
        },
        "runtime_model_choice": {
            "primary": "DKT from current tutor data if artifacts load and concept mapping matches.",
            "baseline": "BKT baseline when DKT is missing or fails.",
            "safety_fallback": "fallback_cumulative when no model artifact is usable.",
        },
        "justification": (
            "The selected DKT artifact is trained on the current tutor concept IDs and optimizes validation log loss. "
            "BKT is retained because it is transparent and robust under artifact failure."
        ),
        "risk_of_too_small_model": "May underfit longer learner histories and miss sequence effects beyond cumulative correctness.",
        "risk_of_too_large_model": "May overfit the highly imbalanced correctness distribution and increase runtime cost.",
        "correctness_imbalance_limitation": (
            "The current data is dominated by correct answers, so accuracy is not enough; Brier score, RMSE, "
            "log loss, and AUC are reported alongside it."
        ),
        "warnings": [] if candidates else ["DKT hyperparameter candidates were not found. Run train_dkt_runtime_model first."],
    }
    return report


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        "# KT Hyperparameter Sensitivity Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Selected Default",
        "",
        f"- Runtime model: {report['selected_default']['runtime_model']}",
        f"- Best hyperparameters: `{report['selected_default']['best_hyperparameters']}`",
        f"- Selection rule: {report['selected_default']['selection_rule']}",
        "",
        "## DKT Candidate Effects",
        "",
    ]
    for effect in report["observed_effects"]:
        lines.append(
            f"- {effect['model_name']}: embedding={effect['embedding_dim']}, hidden={effect['hidden_dim']}, "
            f"lr={effect['learning_rate']}, max_seq_len={effect['max_seq_len']}, "
            f"val_log_loss={effect['val_log_loss']}, val_brier={effect['val_brier_score']}, "
            f"test_auc={effect['test_auc']}, test_rmse={effect['test_rmse']}"
        )
    lines.extend(
        [
            "",
            "## Runtime Choice",
            "",
            f"- Primary: {report['runtime_model_choice']['primary']}",
            f"- Baseline: {report['runtime_model_choice']['baseline']}",
            f"- Safety fallback: {report['runtime_model_choice']['safety_fallback']}",
            "",
            "## Limitations",
            "",
            f"- {report['correctness_imbalance_limitation']}",
            f"- Too small: {report['risk_of_too_small_model']}",
            f"- Too large: {report['risk_of_too_large_model']}",
        ]
    )
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: kt_hyperparameter_sensitivity_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
