from __future__ import annotations

import json
import warnings
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import sklearn
from sklearn.exceptions import InconsistentVersionWarning


ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = ROOT / "evaluation_outputs" / "json" / "sklearn_model_compatibility_report.json"
MD_REPORT = ROOT / "evaluation_outputs" / "reports" / "sklearn_model_compatibility_report.md"

MODEL_EXTENSIONS = {".pkl", ".joblib", ".sav"}
SEARCH_DIRS = [
    ROOT / "models",
    ROOT / "tutor",
    ROOT / "evaluation_outputs",
]
SKIP_PARTS = {
    ".git",
    ".idea",
    ".venv",
    "__pycache__",
    "site-packages",
    "CogniTutor_LM_from_scratch",
    "fine_tuing_llm",
    "sanvia_finetuning",
    "Sanvia",
}


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


def _find_model_artifacts() -> list[Path]:
    paths: list[Path] = []
    for directory in SEARCH_DIRS:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file():
                continue
            if _should_skip(path):
                continue
            if path.suffix.lower() in MODEL_EXTENSIONS:
                paths.append(path)
    return sorted(set(paths))


def _warning_payload(caught: list[warnings.WarningMessage]) -> list[dict[str, str]]:
    payload = []
    for item in caught:
        payload.append(
            {
                "category": item.category.__name__,
                "message": str(item.message),
            }
        )
    return payload


def _has_inconsistent_warning(caught: list[warnings.WarningMessage]) -> bool:
    return any(issubclass(item.category, InconsistentVersionWarning) for item in caught)


def _recommendation(
    load_status: str,
    warnings_payload: list[dict[str, str]],
    error_message: str | None,
    simple_imputer_issue_count: int,
) -> str:
    warning_text = " ".join(item["message"] for item in warnings_payload).lower()
    if load_status == "error":
        if error_message and "_fill_dtype" in error_message:
            return "Retrain or re-save this pipeline with the current sklearn version; use the existing fallback path until then."
        return "Keep fallback enabled and inspect/retrain this artifact before production use."
    if simple_imputer_issue_count:
        return "Model loads but contains SimpleImputer objects missing _fill_dtype; fallback is recommended until the artifact is retrained or re-saved with the current sklearn version."
    if "trying to unpickle estimator" in warning_text:
        return "Artifact was saved with a different sklearn version; schedule retraining/re-saving with the current environment and keep fallback enabled."
    if warnings_payload:
        return "Model loaded with warnings; review before using as a production decision source."
    return "Model loaded without sklearn compatibility warnings."


def _simple_imputer_missing_fill_dtype_count(model: Any, max_nodes: int = 5000) -> int:
    try:
        from sklearn.impute import SimpleImputer
    except Exception:
        return 0

    seen: set[int] = set()
    queue: deque[Any] = deque([model])
    missing_count = 0
    visited = 0
    scalar_types = (str, bytes, int, float, bool, type(None))

    while queue and visited < max_nodes:
        current = queue.popleft()
        visited += 1
        obj_id = id(current)
        if obj_id in seen:
            continue
        seen.add(obj_id)

        if isinstance(current, SimpleImputer) and not hasattr(current, "_fill_dtype"):
            missing_count += 1

        if isinstance(current, scalar_types):
            continue
        if isinstance(current, dict):
            queue.extend(current.keys())
            queue.extend(current.values())
            continue
        if isinstance(current, (list, tuple, set, frozenset)):
            queue.extend(current)
            continue
        if hasattr(current, "steps"):
            try:
                queue.extend(step for _, step in current.steps)
            except Exception:
                pass
        if hasattr(current, "transformers"):
            try:
                queue.extend(transformer for _, transformer, _ in current.transformers)
            except Exception:
                pass
        if hasattr(current, "__dict__"):
            try:
                queue.extend(vars(current).values())
            except Exception:
                pass

    return missing_count


def _check_model(path: Path) -> dict[str, Any]:
    caught_warnings: list[warnings.WarningMessage]
    model: Any = None
    error_message: str | None = None
    error_type: str | None = None

    with warnings.catch_warnings(record=True) as caught:
        caught_warnings = caught
        warnings.simplefilter("always")
        try:
            model = joblib.load(path)
        except AttributeError as exc:
            error_type = type(exc).__name__
            error_message = str(exc)
        except Exception as exc:
            error_type = type(exc).__name__
            error_message = str(exc)

    warnings_payload = _warning_payload(caught_warnings)
    simple_imputer_issue_count = (
        _simple_imputer_missing_fill_dtype_count(model)
        if error_message is None
        else 0
    )
    has_inconsistent = _has_inconsistent_warning(caught_warnings)

    if error_message:
        load_status = "error"
    elif has_inconsistent or warnings_payload or simple_imputer_issue_count:
        load_status = "warning"
    else:
        load_status = "success"

    fallback_needed = load_status in {"warning", "error"}
    return {
        "model_path": _relative(path),
        "load_status": load_status,
        "warnings": warnings_payload,
        "error_type": error_type,
        "error_message": error_message,
        "simple_imputer_missing_fill_dtype_count": simple_imputer_issue_count,
        "fallback_needed": fallback_needed,
        "recommendation": _recommendation(
            load_status=load_status,
            warnings_payload=warnings_payload,
            error_message=error_message,
            simple_imputer_issue_count=simple_imputer_issue_count,
        ),
    }


def build_report() -> dict[str, Any]:
    model_paths = _find_model_artifacts()
    results = [_check_model(path) for path in model_paths]
    warning_count = sum(1 for item in results if item["load_status"] == "warning")
    error_count = sum(1 for item in results if item["load_status"] == "error")
    status = "warning" if warning_count or error_count else "success"
    return {
        "status": status,
        "module": "sklearn_model_compatibility",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "current_sklearn_version": sklearn.__version__,
        "search_dirs": [_relative(path) for path in SEARCH_DIRS],
        "total_models_checked": len(results),
        "success_count": sum(1 for item in results if item["load_status"] == "success"),
        "warning_count": warning_count,
        "error_count": error_count,
        "fallback_needed_count": sum(1 for item in results if item["fallback_needed"]),
        "results": results,
        "notes": [
            "This report is read-only: no model files were deleted, modified, or retrained.",
            "Fallback is recommended for artifacts with sklearn version warnings or SimpleImputer _fill_dtype compatibility issues.",
        ],
    }


def write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Sklearn Model Compatibility Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Current sklearn version: `{report['current_sklearn_version']}`",
        f"- Total models checked: `{report['total_models_checked']}`",
        f"- Success count: `{report['success_count']}`",
        f"- Warning count: `{report['warning_count']}`",
        f"- Error count: `{report['error_count']}`",
        f"- Fallback needed count: `{report['fallback_needed_count']}`",
        "",
        "## Notes",
        "",
        *[f"- {note}" for note in report["notes"]],
        "",
        "## Model Results",
        "",
    ]
    for item in report["results"]:
        lines.extend(
            [
                f"### `{item['model_path']}`",
                "",
                f"- Load status: `{item['load_status']}`",
                f"- Fallback needed: `{item['fallback_needed']}`",
                f"- SimpleImputer missing `_fill_dtype` count: `{item['simple_imputer_missing_fill_dtype_count']}`",
                f"- Error: `{item['error_message']}`",
                f"- Recommendation: {item['recommendation']}",
                "- Warnings:",
            ]
        )
        if item["warnings"]:
            lines.extend(
                f"  - `{warning['category']}`: {warning['message']}"
                for warning in item["warnings"]
            )
        else:
            lines.append("  - None")
        lines.append("")
    MD_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report()
    write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: sklearn_model_compatibility")
    print(f"total_models_checked: {report['total_models_checked']}")
    print(f"warning_count: {report['warning_count']}")
    print(f"error_count: {report['error_count']}")
    print(f"JSON_REPORT: {_relative(JSON_REPORT)}")
    print(f"MD_REPORT: {_relative(MD_REPORT)}")


if __name__ == "__main__":
    main()
