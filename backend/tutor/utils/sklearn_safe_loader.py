from __future__ import annotations

import pickle
import warnings
from pathlib import Path
from typing import Any, Callable

import joblib
import sklearn
from sklearn.exceptions import InconsistentVersionWarning


def _warning_payload(caught: list[warnings.WarningMessage]) -> list[dict[str, str]]:
    return [
        {
            "category": item.category.__name__,
            "message": str(item.message),
        }
        for item in caught
    ]


def _has_version_mismatch(warnings_payload: list[dict[str, str]]) -> bool:
    return any(item.get("category") == "InconsistentVersionWarning" for item in warnings_payload)


def _metadata(
    *,
    path: Path,
    model_loaded: bool,
    warning_payload: list[dict[str, str]],
    error: Exception | None = None,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    version_mismatch = _has_version_mismatch(warning_payload)
    if fallback_reason is None:
        if error is not None and "_fill_dtype" in str(error):
            fallback_reason = "sklearn_simple_imputer_compatibility"
        elif version_mismatch:
            fallback_reason = "sklearn_version_mismatch"
        elif error is not None:
            fallback_reason = "model_load_or_prediction_error"

    fallback_needed = bool(fallback_reason) or not model_loaded
    return {
        "model_status": (
            "unavailable_version_mismatch"
            if version_mismatch
            else "unavailable_runtime_error"
            if error is not None
            else "available"
            if model_loaded
            else "unavailable_missing"
        ),
        "model_loaded": bool(model_loaded and not version_mismatch),
        "fallback_used": fallback_needed,
        "fallback_reason": fallback_reason,
        "current_sklearn_version": sklearn.__version__,
        "warning_count": len(warning_payload),
        "warnings": warning_payload,
        "error_type": type(error).__name__ if error else None,
        "error_message": str(error) if error else None,
        "recommendation": (
            "retrain_or_resave_model_with_current_sklearn"
            if fallback_needed
            else "model_available"
        ),
        "model_path": str(path),
    }


def safe_joblib_load(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {
            "model": None,
            "metadata": _metadata(
                path=path,
                model_loaded=False,
                warning_payload=[],
                fallback_reason="model_file_missing",
            ),
        }

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            model = joblib.load(path)
        except Exception as exc:
            return {
                "model": None,
                "metadata": _metadata(
                    path=path,
                    model_loaded=False,
                    warning_payload=_warning_payload(caught),
                    error=exc,
                ),
            }

    warning_payload = _warning_payload(caught)
    metadata = _metadata(
        path=path,
        model_loaded=not _has_version_mismatch(warning_payload),
        warning_payload=warning_payload,
    )
    return {
        "model": model if metadata["model_loaded"] else None,
        "metadata": metadata,
    }


def safe_pickle_load(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {
            "model": None,
            "metadata": _metadata(
                path=path,
                model_loaded=False,
                warning_payload=[],
                fallback_reason="model_file_missing",
            ),
        }

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            with path.open("rb") as handle:
                model = pickle.load(handle)
        except Exception as exc:
            return {
                "model": None,
                "metadata": _metadata(
                    path=path,
                    model_loaded=False,
                    warning_payload=_warning_payload(caught),
                    error=exc,
                ),
            }

    warning_payload = _warning_payload(caught)
    metadata = _metadata(
        path=path,
        model_loaded=not _has_version_mismatch(warning_payload),
        warning_payload=warning_payload,
    )
    return {
        "model": model if metadata["model_loaded"] else None,
        "metadata": metadata,
    }


def safe_model_call(
    model: Any,
    path: Path | str,
    call: Callable[[], Any],
) -> dict[str, Any]:
    path = Path(path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            value = call()
        except AttributeError as exc:
            return {
                "ok": False,
                "value": None,
                "metadata": _metadata(
                    path=path,
                    model_loaded=False,
                    warning_payload=_warning_payload(caught),
                    error=exc,
                ),
            }
        except Exception as exc:
            return {
                "ok": False,
                "value": None,
                "metadata": _metadata(
                    path=path,
                    model_loaded=False,
                    warning_payload=_warning_payload(caught),
                    error=exc,
                ),
            }

    warning_payload = _warning_payload(caught)
    metadata = _metadata(
        path=path,
        model_loaded=not _has_version_mismatch(warning_payload),
        warning_payload=warning_payload,
    )
    if metadata["fallback_used"]:
        return {"ok": False, "value": None, "metadata": metadata}
    return {"ok": True, "value": value, "metadata": metadata}


def merge_model_metadata(*items: dict[str, Any] | None) -> dict[str, Any]:
    payloads = [item for item in items if isinstance(item, dict)]
    if not payloads:
        return {}
    return {
        "model_status": "available"
        if all(item.get("model_status") == "available" for item in payloads)
        else "unavailable_version_mismatch"
        if any(item.get("fallback_reason") == "sklearn_version_mismatch" for item in payloads)
        else "unavailable_runtime_error",
        "model_loaded": all(bool(item.get("model_loaded")) for item in payloads),
        "fallback_used": any(bool(item.get("fallback_used")) for item in payloads),
        "fallback_reason": next(
            (item.get("fallback_reason") for item in payloads if item.get("fallback_reason")),
            None,
        ),
        "current_sklearn_version": sklearn.__version__,
        "warning_count": sum(int(item.get("warning_count", 0) or 0) for item in payloads),
        "recommendation": "retrain_or_resave_model_with_current_sklearn"
        if any(bool(item.get("fallback_used")) for item in payloads)
        else "model_available",
        "models": payloads,
    }
