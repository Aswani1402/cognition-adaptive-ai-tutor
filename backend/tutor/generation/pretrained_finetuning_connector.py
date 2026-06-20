"""Comparison-only connector for the pretrained fine-tuning track.

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
