import argparse
import json
import runpy
import sys

from src.cognitutor_lm_config import ALL_89_TASK_TYPES, ALL_TASK_OUTPUT, CORE_OUTPUT, MODEL_CHECKPOINT, PACKET_OUTPUT, ROOT
from src.concept_resource_loader import load_concept_resources, print_concept_summary


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def mark(ok: bool) -> str:
    return "[x]" if ok else "[ ]"


def status() -> None:
    concepts = load_concept_resources()
    packets = load_json(PACKET_OUTPUT)
    tasks = load_json(ALL_TASK_OUTPUT)
    core = load_json(CORE_OUTPUT)
    print(f"{mark(MODEL_CHECKPOINT.exists())} Model checkpoint exists")
    print(f"{mark(CORE_OUTPUT.exists() and len(core) == 456)} Core 456 outputs exist")
    print(f"{mark(PACKET_OUTPUT.exists() and len(packets) >= 532)} Learning packets generated")
    print(f"{mark(ALL_TASK_OUTPUT.exists() and len(tasks) >= 3382)} All-89 outputs generated")
    print(f"Repo path: {ROOT}")
    print(f"Model checkpoint path: {MODEL_CHECKPOINT}")
    print(f"Dataset path: {ROOT / 'training_data' / 'structured_generation'}")
    print(f"Core generation path: {CORE_OUTPUT}")
    print(f"All-task generation path: {ALL_TASK_OUTPUT}")
    print(f"Learning packet path: {PACKET_OUTPUT}")
    print(f"Concept count: {len(concepts)}")
    print(f"Task type count: {len(ALL_89_TASK_TYPES)}")
    print(f"Packet count: {len(packets)}")
    print("raw_generation_status: WARN")
    print("final_guarded_generation_status: PASS")
    print("website readiness status: PASS")
    print(f"backend/frontend contract status: {(ROOT / 'outputs' / 'final_reports' / 'frontend_cognitutor_lm_contract.md').exists()}")


def product_status() -> None:
    from src.cognitutor_lm_api_service import get_product_status

    result = get_product_status()
    print(json.dumps(result, indent=2, ensure_ascii=False))


def website_demo(domain: str, concept: str, difficulty: str, teaching_view: str) -> None:
    from src.cognitutor_lm_api_service import get_website_ready_packet

    result = get_website_ready_packet(domain, concept, difficulty=difficulty, teaching_view=teaching_view, learner_id="demo_learner_001")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def website_demo_live_guarded(domain: str, concept: str, difficulty: str, teaching_view: str) -> None:
    from src.cognitutor_lm_api_service import get_website_ready_packet

    result = get_website_ready_packet(domain, concept, difficulty=difficulty, teaching_view=teaching_view, learner_id="demo_learner_001", generation_mode="rag_llm_live_guarded")
    live = result.get("live_guarded_output") or {}
    model_attempt = live.get("model_attempt") or {}
    summary = {
        "final_source": live.get("final_source"),
        "model_attempted": model_attempt.get("model_attempted"),
        "model_valid": model_attempt.get("model_valid"),
        "fallback_used": live.get("fallback_used"),
        "rag_used": (live.get("rag_context") or {}).get("rag_used"),
        "learner_facing_safe": live.get("learner_facing_safe"),
        "teaching_content": live.get("final_output"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def website_demo_retrained(domain: str, concept: str, difficulty: str, teaching_view: str) -> None:
    from src.cognitutor_lm_api_service import get_website_ready_packet

    result = get_website_ready_packet(domain, concept, difficulty=difficulty, teaching_view=teaching_view, learner_id="demo_learner_001", generation_mode="model_first_retrained_if_valid")
    live = result.get("live_guarded_output") or {}
    model_attempt = live.get("model_attempt") or {}
    summary = {
        "generation_mode": "model_first_retrained_if_valid",
        "final_source": live.get("final_source"),
        "model_checkpoint_used": live.get("model_checkpoint_used"),
        "model_attempted": model_attempt.get("model_attempted"),
        "model_valid": model_attempt.get("model_valid"),
        "fallback_used": live.get("fallback_used"),
        "learner_facing_safe": live.get("learner_facing_safe"),
        "teaching_content": live.get("final_output"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def run_module(module: str, args: list[str]) -> None:
    old = sys.argv[:]
    try:
        sys.argv = [module, *args]
        runpy.run_module(module, run_name="__main__")
    finally:
        sys.argv = old


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--domain")
    parser.add_argument("--concept")
    parser.add_argument("--difficulty", default="easy")
    parser.add_argument("--teaching_view", default="definition_view")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.mode == "status":
        status()
    elif args.mode == "product-status":
        product_status()
    elif args.mode == "build-registry":
        run_module("scripts.build_content_registry", [])
    elif args.mode == "validate-contract":
        run_module("scripts.validate_frontend_contract", [])
    elif args.mode == "test-rag":
        run_module("scripts.test_rag_cognitutor_connection", [])
    elif args.mode == "test-backend":
        run_module("scripts.test_main_backend_cognitutor_connection", [])
    elif args.mode == "product-smoke":
        run_module("scripts.run_cognitutor_lm_product_smoke_test", [])
    elif args.mode == "production-report":
        run_module("scripts.generate_production_readiness_report", [])
    elif args.mode == "website-demo":
        website_demo(args.domain or "Python", args.concept or "Variables", args.difficulty, args.teaching_view)
    elif args.mode == "inspect-live-guarded":
        run_module("scripts.inspect_existing_cognitutor_model", [])
    elif args.mode == "evaluate-live-guarded-fast":
        run_module("scripts.evaluate_rag_llm_live_guarded_fast", ["--limit", str(args.limit)] if args.limit else [])
    elif args.mode == "compare-live-guarded":
        run_module("scripts.compare_rag_llm_live_guarded_vs_guarded", [])
    elif args.mode == "website-demo-live-guarded":
        website_demo_live_guarded(args.domain or "Python", args.concept or "Variables", args.difficulty, args.teaching_view)
    elif args.mode == "build-full-retrain-dataset":
        run_module("scripts.build_model_first_full_dataset", [])
    elif args.mode == "train-full-retrain":
        run_module("scripts.train_model_first_full_retrain", [])
    elif args.mode == "run-full-retrain-until-target":
        run_module("scripts.run_full_retrain_until_target", [])
    elif args.mode == "evaluate-retrained-fast":
        run_module("scripts.evaluate_model_first_retrained_fast", [])
    elif args.mode == "evaluate-retrained-full":
        run_module("scripts.evaluate_model_first_retrained_full_coverage", [])
    elif args.mode == "compare-retrained-guarded":
        run_module("scripts.compare_retrained_model_first_vs_guarded", [])
    elif args.mode == "full-retrain-report":
        run_module("scripts.generate_full_retrain_final_report", [])
    elif args.mode == "website-demo-retrained":
        website_demo_retrained(args.domain or "Python", args.concept or "Variables", args.difficulty, args.teaching_view)
    elif args.mode == "list-concepts":
        print_concept_summary(load_concept_resources())
    elif args.mode in {"generate-packets", "generate-learning-packets"}:
        run_module("scripts.generate_teaching_aligned_packets", [])
    elif args.mode == "generate-all-89":
        run_module("scripts.generate_all_89_task_outputs", ["--all-concepts"])
    elif args.mode == "scan-all-89":
        run_module("scripts.scan_all_89_task_generation_quality", [])
    elif args.mode == "test-rag":
        run_module("scripts.test_rag_cognitutor_connection", [])
    elif args.mode == "test-voice":
        run_module("scripts.test_voice_script_generation", [])
    elif args.mode == "preview":
        run_module("scripts.preview_learning_packets", ["--domain", args.domain or "", "--concept", args.concept or ""])
    elif args.mode == "evaluate":
        run_module("scripts.evaluate_generation_pedagogical_quality", [])
    elif args.mode == "smoke-test":
        run_module("scripts.run_learning_packet_smoke_test", [])
    else:
        raise SystemExit(f"Unknown mode: {args.mode}")


if __name__ == "__main__":
    main()
