import json

from src.cognitutor_lm_config import ROOT

BASE = ROOT / "outputs" / "model_first_full_retrain"
OUT_DIR = BASE / "reports"
OUT_JSON = OUT_DIR / "full_retrain_final_report.json"
OUT_MD = OUT_DIR / "full_retrain_final_report.md"


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def main():
    dataset = load(BASE / "dataset" / "model_first_full_dataset_report.json", {})
    training = load(BASE / "training" / "full_retrain_training_report.json", {})
    fixed_training = load(BASE / "training" / "full_fixed_training_report.json", {})
    fast = load(BASE / "evaluation" / "retrained_fast_evaluation.json", {})
    full = load(BASE / "evaluation" / "retrained_full_coverage_raw100.json", None) or load(BASE / "evaluation" / "retrained_full_coverage.json", {})
    comp = load(BASE / "evaluation" / "retrained_vs_guarded_comparison.json", {})
    metrics = full.get("metrics") or {}
    full_rate = float(metrics.get("raw_model_valid_rate_on_raw_decode") if metrics.get("raw_model_valid_rate_on_raw_decode") is not None else (metrics.get("model_valid_rate") or 0))
    fast_rate = float((fast.get("metrics") or {}).get("model_valid_rate") or 0)
    original_failed = (training.get("finite_update_count") == 0) or training.get("training_status") in {"WARN", "FAIL"}
    fixed_succeeded = fixed_training.get("training_status") == "PASS"
    if not fixed_succeeded:
        claim = "Full retraining was attempted, but the training loop did not produce a reliable improved checkpoint. The system remains guarded-primary with live model attempts."
    elif full_rate >= 0.85:
        claim = "Retrained CogniTutorLM reached the target validation threshold and is used as the primary generation attempt with guarded fallback."
    else:
        claim = "Retraining produced a usable checkpoint, but raw generation did not reach the strict reliability threshold. Runtime remains model-first-if-valid with guarded fallback."
    report = {
        "status": "PASS" if full_rate >= 0.85 and metrics.get("learner_facing_safe_rate") == 1.0 else "WARN",
        "motivation": "Improve raw model-first acceptance while preserving guarded learner-facing safety.",
        "dataset_coverage": dataset,
        "original_training_failed_due_to_zero_finite_updates": original_failed,
        "original_training_setup": training,
        "fixed_training_setup": fixed_training,
        "best_checkpoint": fixed_training.get("best_checkpoint") or training.get("best_checkpoint"),
        "checkpoint_actually_used": (fast.get("metrics") or {}).get("model_checkpoint_used") or metrics.get("model_checkpoint_used"),
        "fast_evaluation_result": fast.get("metrics", {}),
        "full_3382_case_evaluation_result": full.get("metrics", {}),
        "comparison_with_guarded_generator": comp,
        "runtime_recommendation": comp.get("runtime_recommendation") or "guarded_primary_with_live_attempt",
        "what_can_be_claimed": claim,
        "what_cannot_be_claimed": "Raw CogniTutorLM does not perfectly generate every live task unless full coverage metrics prove it.",
        "limitations_and_future_work": ["Raw full decode can be time-expensive.", "Additional epochs may improve task-format adherence.", "Fallback remains required for learner safety."],
        "fast_model_valid_rate": fast_rate,
        "full_raw_decoded_model_valid_rate": full_rate,
        "raw_decode_evaluated_count": metrics.get("raw_decode_evaluated_count"),
        "raw_limit_used": metrics.get("raw_limit_requested"),
        "learner_facing_safe_rate": metrics.get("learner_facing_safe_rate"),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# Full Retrain Final Report", "", claim, ""]
    for key in ["status", "original_training_failed_due_to_zero_finite_updates", "best_checkpoint", "checkpoint_actually_used", "fast_model_valid_rate", "full_raw_decoded_model_valid_rate", "raw_decode_evaluated_count", "learner_facing_safe_rate", "runtime_recommendation", "what_cannot_be_claimed"]:
        lines.append(f"- {key}: {report.get(key)}")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
