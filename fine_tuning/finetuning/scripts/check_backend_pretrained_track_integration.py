from pathlib import Path

from scripts.pretrained_track_utils import BACKEND_ROOT, REPO_ROOT, iter_files, rel, write_json, write_md


CONNECTOR_REL = Path("tutor/generation/pretrained_finetuning_connector.py")
CONNECTOR_TEXT = '''"""Comparison-only connector for the pretrained fine-tuning track.

This module must not be used as the learner-facing generation route.
"""

from typing import Any, Dict, List, Optional


def get_pretrained_generation_comparison_packet(
    task_outputs: Optional[List[Dict[str, Any]]] = None,
    validation: Optional[Dict[str, Any]] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    outputs = task_outputs or []
    model_loaded = any(item.get("model_loaded") for item in outputs if isinstance(item, dict))
    return {
        "status": "success" if model_loaded else "warn",
        "source": "pretrained_finetuning_track",
        "comparison_only": True,
        "runtime_enabled": False,
        "model_loaded": model_loaded,
        "task_outputs": outputs,
        "validation": validation or {},
        "reason": reason or "comparison-only connector; learner-facing runtime is disabled",
    }
'''


def _backend_evidence():
    if not BACKEND_ROOT.exists():
        return []
    evidence = []
    for path in iter_files(BACKEND_ROOT):
        if path.suffix.lower() != ".py":
            continue
        lower = rel(path, BACKEND_ROOT).lower()
        if any(term in lower for term in ("generation", "rag", "tutor", "llm")):
            evidence.append(rel(path, BACKEND_ROOT))
    return sorted(evidence)


def main() -> None:
    connector_path = BACKEND_ROOT / CONNECTOR_REL
    backend_exists = BACKEND_ROOT.exists()
    evidence = _backend_evidence()
    connector_status = "not_created"
    reason = None
    if not backend_exists:
        status = "FAIL"
        reason = f"backend path does not exist: {BACKEND_ROOT}"
    else:
        connector_path.parent.mkdir(parents=True, exist_ok=True)
        if not connector_path.exists() or connector_path.read_text(encoding="utf-8", errors="ignore") != CONNECTOR_TEXT:
            connector_path.write_text(CONNECTOR_TEXT, encoding="utf-8")
            connector_status = "created_or_updated"
        else:
            connector_status = "already_present"
        status = "PASS"
        reason = "comparison-only connector exists; backend learner-facing route was not changed"
    data = {
        "status": status,
        "backend_path": str(BACKEND_ROOT),
        "backend_exists": backend_exists,
        "generation_related_files": evidence,
        "connector_path": str(connector_path),
        "connector_status": connector_status,
        "comparison_only": True,
        "runtime_enabled": False,
        "route_replacement_performed": False,
        "reason": reason,
    }
    write_json(REPO_ROOT / "outputs/evaluation/backend_pretrained_track_integration_check.json", data)
    write_md(
        REPO_ROOT / "outputs/evaluation/backend_pretrained_track_integration_check.md",
        "Backend Pretrained Fine-Tuning Track Integration Check",
        {
            "Status": status,
            "Backend Path": str(BACKEND_ROOT),
            "Connector": str(connector_path),
            "Connector Status": connector_status,
            "Comparison Only": True,
            "Runtime Enabled": False,
            "Route Replacement Performed": False,
            "Reason": reason,
            "Generation Related Files": evidence[:50],
        },
    )
    print(status, "backend integration check saved")


if __name__ == "__main__":
    main()

