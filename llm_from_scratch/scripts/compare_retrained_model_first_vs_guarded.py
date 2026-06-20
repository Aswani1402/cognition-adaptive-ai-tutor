import json

from src.cognitutor_lm_config import ROOT

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "evaluation"
OUT_JSON = OUT_DIR / "retrained_vs_guarded_comparison.json"
OUT_MD = OUT_DIR / "retrained_vs_guarded_comparison.md"


def load(path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def recommendation(rate):
    if rate >= 0.85:
        return "model_first_primary_with_guarded_fallback"
    if rate >= 0.50:
        return "hybrid_model_first_if_valid"
    return "guarded_primary_with_live_attempt"


def main():
    full = load(OUT_DIR / "retrained_full_coverage.json", {})
    fast = load(OUT_DIR / "retrained_fast_evaluation.json", {})
    metrics = (full.get("metrics") or {}) if full else {}
    if not metrics:
        metrics = fast.get("metrics") or {}
    rate = float(metrics.get("model_valid_rate") or 0)
    report = {
        "status": "PASS" if metrics.get("learner_facing_safe_rate") == 1.0 else "FAIL",
        "retrained_model_valid_rate": rate,
        "guarded_valid_rate": 1.0,
        "retrained_average_quality": metrics.get("average_quality_score"),
        "guarded_average_quality": 1.0,
        "fallback_rate": metrics.get("fallback_rate"),
        "learner_facing_safe_rate": metrics.get("learner_facing_safe_rate"),
        "frontend_ready_rate": metrics.get("frontend_ready_rate") or metrics.get("frontend_renderable_rate"),
        "runtime_recommendation": recommendation(rate),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Retrained Model-First vs Guarded\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
