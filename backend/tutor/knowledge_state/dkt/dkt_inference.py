from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from tutor.knowledge_state.bkt.bkt_baseline import BKTModel
from tutor.knowledge_state.dkt.dkt_model import DKTModel
from tutor.knowledge_state.dkt.simple_infer import predict_mastery_simple


DEFAULT_ARTIFACT_DIRS = [
    Path("models/dkt"),
]
BKT_MODEL_PATH = Path("models/kt/bkt_baseline.json")
PHASE1_EXTERNAL_ARTIFACT_NOTE = "phase1_external_artifact_not_used_due_to_skill_mapping_mismatch"


def _find_artifact_dir() -> Path | None:
    for artifact_dir in DEFAULT_ARTIFACT_DIRS:
        if (artifact_dir / "model.pt").exists() and (artifact_dir / "id_map.json").exists():
            return artifact_dir
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _fallback_result(
    learner_id: str,
    concept_ids: list[int],
    correct_values: list[int],
    error: str | None = None,
) -> dict[str, Any]:
    if not concept_ids:
        return {
            "status": "error",
            "source": "fallback_cumulative_mastery",
            "kt_source": "fallback_cumulative_mastery",
            "model_used": False,
            "fallback_used": True,
            "learner_id": learner_id,
            "sequence_length": 0,
            "predicted_mastery_last": 0.0,
            "concept_mastery": {},
            "confidence": 0.0,
            "error": error or "No valid KT interactions available.",
            "schema_version": "kt_v2",
            "written_state": {},
            "concepts": {},
            "model_path": None,
            "id_map_path": None,
            "inference_error": error or "No valid KT interactions available.",
            "phase1_external_artifact_note": PHASE1_EXTERNAL_ARTIFACT_NOTE,
        }

    inter_ids = [
        int(concept_id) * 2 + int(correct)
        for concept_id, correct in zip(concept_ids, correct_values)
    ]
    inter_tensor = torch.tensor([inter_ids], dtype=torch.long)
    target_tensor = torch.tensor([concept_ids], dtype=torch.long)
    probs = predict_mastery_simple(inter_tensor, target_tensor, num_skills=10000)

    concept_mastery: dict[str, float] = {}
    for idx, concept_id in enumerate(concept_ids):
        concept_mastery[str(concept_id)] = float(probs[0, idx].item())

    predicted_mastery_last = float(probs[0, -1].item())

    result = {
        "status": "success",
        "source": "fallback_cumulative_mastery",
        "kt_source": "fallback_cumulative_mastery",
        "model_used": False,
        "fallback_used": True,
        "learner_id": learner_id,
        "sequence_length": len(concept_ids),
        "predicted_mastery_last": predicted_mastery_last,
        "concept_mastery": concept_mastery,
        "confidence": max(0.0, min(1.0, predicted_mastery_last)),
        "error": error,
        "schema_version": "kt_v2",
        "written_state": concept_mastery,
        "concepts": {
            concept_id: {"mastery": mastery, "source": "fallback_cumulative"}
            for concept_id, mastery in concept_mastery.items()
        },
        "model_path": None,
        "id_map_path": None,
        "inference_error": error,
        "phase1_external_artifact_note": PHASE1_EXTERNAL_ARTIFACT_NOTE,
    }
    return result


def _bkt_result(
    learner_id: str,
    raw_concept_ids: list[str],
    concept_ids: list[int],
    correct_values: list[int],
    error: str | None = None,
) -> dict[str, Any]:
    if not BKT_MODEL_PATH.exists():
        return _fallback_result(
            learner_id=learner_id,
            concept_ids=concept_ids,
            correct_values=correct_values,
            error=error or "BKT artifact not found; used cumulative fallback.",
        )

    try:
        model = BKTModel.from_dict(json.loads(BKT_MODEL_PATH.read_text(encoding="utf-8")))
        concept_mastery: dict[str, float] = {}
        for raw_id, numeric_id, correct in zip(raw_concept_ids, concept_ids, correct_values):
            candidates = [str(raw_id), str(numeric_id), str(raw_id).upper()]
            concept_key = next(
                (item for item in candidates if item in model.concept_params),
                str(raw_id),
            )
            mastery = model.update(learner_id, concept_key, correct)
            concept_mastery[str(numeric_id)] = float(mastery)

        predicted_mastery_last = list(concept_mastery.values())[-1] if concept_mastery else 0.0
        return {
            "status": "success",
            "source": "bkt_baseline",
            "kt_source": "fallback_cumulative_mastery",
            "model_used": True,
            "fallback_used": True,
            "learner_id": learner_id,
            "sequence_length": len(concept_ids),
            "predicted_mastery_last": predicted_mastery_last,
            "concept_mastery": concept_mastery,
            "confidence": max(0.0, min(1.0, predicted_mastery_last)),
            "error": error,
            "artifact_dir": str(BKT_MODEL_PATH.parent),
            "schema_version": "kt_v2",
            "written_state": concept_mastery,
            "concepts": {
                concept_id: {"mastery": mastery, "source": "bkt_baseline"}
                for concept_id, mastery in concept_mastery.items()
            },
            "model_path": str(BKT_MODEL_PATH),
            "id_map_path": None,
            "inference_error": error,
            "phase1_external_artifact_note": PHASE1_EXTERNAL_ARTIFACT_NOTE,
        }
    except Exception as exc:
        combined_error = f"{error + ' ' if error else ''}BKT inference failed: {exc}"
        return _fallback_result(
            learner_id=learner_id,
            concept_ids=concept_ids,
            correct_values=correct_values,
            error=combined_error,
        )


def _load_id_map(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def _predict_with_model(
    artifact_dir: Path,
    learner_id: str,
    raw_concept_ids: list[str],
    concept_ids: list[int],
    correct_values: list[int],
) -> dict[str, Any]:
    id_map = _load_id_map(artifact_dir / "id_map.json")
    skill2idx = id_map.get("concept_to_idx") or id_map.get("skill2idx", {})
    if not isinstance(skill2idx, dict) or not skill2idx:
        raise ValueError("id_map.json does not contain a usable concept_to_idx/skill2idx mapping.")

    mapped_skills = []
    mapped_correct = []
    mapped_output_concepts = []

    for raw_id, numeric_id, correct in zip(raw_concept_ids, concept_ids, correct_values):
        candidates = [str(raw_id), str(numeric_id), str(raw_id).upper()]
        skill_idx = next((skill2idx[item] for item in candidates if item in skill2idx), None)
        if skill_idx is None:
            continue
        mapped_skills.append(int(skill_idx))
        mapped_correct.append(int(correct))
        mapped_output_concepts.append(str(numeric_id))

    if not mapped_skills:
        raise ValueError("No runtime concept ids could be mapped to DKT skill ids.")

    num_skills = int(id_map.get("num_concepts") or id_map.get("num_skills") or (max(int(value) for value in skill2idx.values()) + 1))
    embed_dim = int(id_map.get("embedding_dim") or 32)
    hidden_dim = int(id_map.get("hidden_dim") or 64)
    model = DKTModel(num_skills=num_skills, embed_dim=embed_dim, hidden_dim=hidden_dim)
    state_dict = torch.load(artifact_dir / "model.pt", map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()

    skill_tensor = torch.tensor([mapped_skills], dtype=torch.long)
    correct_tensor = torch.tensor([mapped_correct], dtype=torch.float32)

    with torch.no_grad():
        logits = model(skill_tensor, correct_tensor)
        probs_by_skill = torch.sigmoid(logits)

    concept_mastery: dict[str, float] = {}
    for idx, (concept_id, skill_idx) in enumerate(zip(mapped_output_concepts, mapped_skills)):
        concept_mastery[str(concept_id)] = float(probs_by_skill[0, idx, skill_idx].item())

    predicted_mastery_last = list(concept_mastery.values())[-1]

    return {
        "status": "success",
        "source": "dkt_current_tutor_runtime",
        "kt_source": "dkt_runtime",
        "model_used": True,
        "fallback_used": False,
        "learner_id": learner_id,
        "sequence_length": len(mapped_skills),
        "predicted_mastery_last": predicted_mastery_last,
        "concept_mastery": concept_mastery,
        "confidence": max(0.0, min(1.0, 1.0 - abs(predicted_mastery_last - 0.5) * 2.0)),
        "error": None,
        "artifact_dir": str(artifact_dir),
        "schema_version": "kt_v2",
        "written_state": concept_mastery,
        "concepts": {
            concept_id: {"mastery": mastery, "source": "dkt_current_tutor_runtime"}
            for concept_id, mastery in concept_mastery.items()
        },
        "model_path": str(artifact_dir / "model.pt"),
        "id_map_path": str(artifact_dir / "id_map.json"),
        "inference_error": None,
        "phase1_external_artifact_note": PHASE1_EXTERNAL_ARTIFACT_NOTE,
    }


def predict_mastery_dkt_or_fallback(
    learner_id: str,
    interactions: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_concept_ids: list[str] = []
    concept_ids: list[int] = []
    correct_values: list[int] = []

    for interaction in interactions:
        try:
            raw_concept_id = str(interaction.get("raw_concept_id", interaction.get("concept_id"))).strip()
            concept_id = int(interaction.get("concept_id"))
            correct = int(interaction.get("correct", 0))
        except Exception:
            continue

        raw_concept_ids.append(raw_concept_id)
        concept_ids.append(concept_id)
        correct_values.append(1 if correct else 0)

    artifact_dir = _find_artifact_dir()
    if artifact_dir is None:
        return _bkt_result(
            learner_id=learner_id,
            raw_concept_ids=raw_concept_ids,
            concept_ids=concept_ids,
            correct_values=correct_values,
            error="DKT model artifacts not found; used BKT baseline.",
        )

    try:
        return _predict_with_model(
            artifact_dir=artifact_dir,
            learner_id=learner_id,
            raw_concept_ids=raw_concept_ids,
            concept_ids=concept_ids,
            correct_values=correct_values,
        )
    except Exception as exc:
        return _bkt_result(
            learner_id=learner_id,
            raw_concept_ids=raw_concept_ids,
            concept_ids=concept_ids,
            correct_values=correct_values,
            error=f"DKT model inference failed; used BKT baseline. Error: {exc}",
        )
