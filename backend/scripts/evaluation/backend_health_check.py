from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "external" / "core_data" / "tutor.db"
RAG_CORPUS_PATH = PROJECT_ROOT / "models" / "rag" / "rag_corpus.json"


def _run_module(module_name: str, timeout_seconds: int = 180) -> dict[str, Any]:
    cmd = [sys.executable, "-m", module_name]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_seconds,
    )
    output = (result.stdout or "").strip()
    error = (result.stderr or "").strip()
    return {
        "name": module_name,
        "passed": result.returncode == 0,
        "returncode": result.returncode,
        "stdout": output,
        "stderr": error,
    }


def _check_profile_test_report() -> dict[str, Any]:
    result = _run_module("scripts.evaluation.profile_test_report", timeout_seconds=240)
    output = result["stdout"]
    passed = result["passed"] and "PROFILE TEST REPORT" in output and "error" not in output.lower()
    detail = "profile test report completed"
    if not passed:
        error_rows = sum(
            1
            for line in output.splitlines()
            if "|" in line and "| error " in f" {line} "
        )
        if error_rows:
            detail = f"profile test report returned error rows for {error_rows} profiles"
        else:
            detail = result["stderr"] or "profile test report failed"
    return {
        "name": "profile_test_report",
        "passed": passed,
        "detail": detail,
    }


def _check_dqn_policy_test() -> dict[str, Any]:
    result = _run_module("scripts.rl.dqn.test_dqn_policy")
    output = result["stdout"]
    passed = result["passed"] and output.count("OUTPUT:") >= 3
    detail = "DQN policy test produced 3 outputs"
    if not passed:
        detail = result["stderr"] or result["stdout"] or "DQN policy test failed"
    return {
        "name": "dqn_policy_test",
        "passed": passed,
        "detail": detail,
    }


def _check_embedding_rag_retriever_test() -> dict[str, Any]:
    result = _run_module("scripts.rag.test_embedding_rag_retriever", timeout_seconds=300)
    output = result["stdout"]
    passed = result["passed"] and "All 5 domain retrieval checks passed." in output
    detail = "embedding RAG retriever test passed for 5 domains"
    if not passed:
        detail = result["stderr"] or result["stdout"] or "embedding RAG retriever test failed"
    return {
        "name": "embedding_rag_retriever_test",
        "passed": passed,
        "detail": detail,
    }


def _check_rag_context_builder_test() -> dict[str, Any]:
    result = _run_module("scripts.rag.test_rag_context_builder", timeout_seconds=240)
    output = result["stdout"]
    passed = result["passed"] and "RAG CONCEPT RESOURCE" in output and "LESSON PACK" in output
    detail = "RAG context builder test completed"
    if not passed:
        detail = result["stderr"] or result["stdout"] or "RAG context builder test failed"
    return {
        "name": "rag_context_builder_test",
        "passed": passed,
        "detail": detail,
    }


def _check_lesson_orchestrator_test() -> dict[str, Any]:
    result = _run_module("scripts.test_lesson_orchestrator", timeout_seconds=180)
    output = result["stdout"]
    passed = result["passed"] and "lesson_pack" in output
    detail = "lesson orchestrator test completed"
    if not passed:
        detail = result["stderr"] or result["stdout"] or "lesson orchestrator test failed"
    return {
        "name": "lesson_orchestrator_test",
        "passed": passed,
        "detail": detail,
    }


def _check_rl_log_count() -> dict[str, Any]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM rl_experience_log")
        total = int(cursor.fetchone()[0])
        conn.close()
    except Exception as exc:
        return {
            "name": "rl_log_count",
            "passed": False,
            "detail": f"failed to read RL logs: {exc}",
        }

    return {
        "name": "rl_log_count",
        "passed": total > 0,
        "detail": f"{total} RL experience rows found",
    }


def _check_rag_corpus_chunk_count() -> dict[str, Any]:
    try:
        with RAG_CORPUS_PATH.open("r", encoding="utf-8") as handle:
            corpus = json.load(handle)
        total = len(corpus) if isinstance(corpus, list) else 0
    except Exception as exc:
        return {
            "name": "rag_corpus_chunk_count",
            "passed": False,
            "detail": f"failed to read RAG corpus: {exc}",
        }

    return {
        "name": "rag_corpus_chunk_count",
        "passed": total > 0,
        "detail": f"{total} corpus chunks found",
    }


def run_backend_health_check() -> list[dict[str, Any]]:
    return [
        _check_profile_test_report(),
        _check_dqn_policy_test(),
        _check_embedding_rag_retriever_test(),
        _check_rag_context_builder_test(),
        _check_lesson_orchestrator_test(),
        _check_rl_log_count(),
        _check_rag_corpus_chunk_count(),
    ]


def print_summary(results: list[dict[str, Any]]) -> None:
    print("BACKEND HEALTH CHECK")
    print()

    passed_count = sum(1 for item in results if item["passed"])
    total_count = len(results)

    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"[{status}] {item['name']}: {item['detail']}")

    print()
    print(f"Summary: {passed_count}/{total_count} checks passed")


def main() -> None:
    results = run_backend_health_check()
    print_summary(results)
    if not all(item["passed"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
