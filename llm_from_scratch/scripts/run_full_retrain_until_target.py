import json
import runpy
import sys
from pathlib import Path

from src.cognitutor_lm_config import ROOT

OUT_DIR = ROOT / "outputs" / "model_first_full_retrain" / "run"
OUT_JSON = OUT_DIR / "full_retrain_until_target_report.json"
OUT_MD = OUT_DIR / "full_retrain_until_target_report.md"


def run_module(module):
    old = sys.argv[:]
    try:
        sys.argv = [module]
        runpy.run_module(module, run_name="__main__")
    finally:
        sys.argv = old


def load(path: Path, fallback):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else fallback


def main():
    rounds_run = 0
    run_module("scripts.build_model_first_full_dataset")
    run_module("scripts.train_model_first_full_retrain")
    rounds_run += 1
    run_module("scripts.evaluate_model_first_retrained_fast")
    fast = load(ROOT / "outputs" / "model_first_full_retrain" / "evaluation" / "retrained_fast_evaluation.json", {})
    rate = float((fast.get("metrics") or {}).get("model_valid_rate") or 0)
    target_reached = rate >= 0.85
    full_rate = None
    if target_reached:
        run_module("scripts.evaluate_model_first_retrained_full_coverage")
        full = load(ROOT / "outputs" / "model_first_full_retrain" / "evaluation" / "retrained_full_coverage.json", {})
        full_rate = (full.get("metrics") or {}).get("model_valid_rate")
    reason = "target_reached" if target_reached else "max_safe_rounds_for_this_run_reached"
    if rate >= 0.85:
        rec = "model_first_primary_with_guarded_fallback"
    elif rate >= 0.50:
        rec = "hybrid_model_first_if_valid"
    else:
        rec = "guarded_primary_with_live_attempt"
    report = {
        "rounds_run": rounds_run,
        "best_model_valid_rate_fast": rate,
        "best_model_valid_rate_full": full_rate,
        "best_checkpoint": str(ROOT / "models" / "cognitutor_lm_model_first_full" / "best_model.pt"),
        "target_reached": target_reached,
        "reason_stopped": reason,
        "recommended_runtime_mode": rec,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text("# Full Retrain Until Target Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in report.items()), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
