from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

import numpy as np

from tutor.rag.embedding_rag_retriever import (
    DEFAULT_MODEL_NAME,
    CORPUS_PATH,
    EMBEDDINGS_PATH,
    INDEX_PATH,
    _safe_import_sentence_transformer,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compose_chunk_text(chunk: dict[str, Any]) -> str:
    return " | ".join(
        part
        for part in [
            str(chunk.get("domain", "")).strip(),
            str(chunk.get("concept_name", "")).strip(),
            str(chunk.get("section", "")).strip(),
            str(chunk.get("text", "")).strip(),
        ]
        if part
    )


def _write_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    return payload


def build_embedding_index(
    corpus_path: Path = CORPUS_PATH,
    embeddings_path: Path = EMBEDDINGS_PATH,
    index_path: Path = INDEX_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
) -> dict[str, Any]:
    corpus_path = Path(corpus_path)
    embeddings_path = Path(embeddings_path)
    index_path = Path(index_path)
    index_path.parent.mkdir(parents=True, exist_ok=True)

    if not corpus_path.exists():
        return _write_manifest(
            {
                "status": "fallback_only",
                "reason": f"RAG corpus not found at {corpus_path}",
                "built_at": _utc_now_iso(),
                "corpus_path": str(corpus_path),
                "embeddings_path": str(embeddings_path),
            }
        )

    with corpus_path.open("r", encoding="utf-8") as handle:
        corpus = json.load(handle)

    if not isinstance(corpus, list) or not corpus:
        return _write_manifest(
            {
                "status": "fallback_only",
                "reason": "RAG corpus is empty or invalid",
                "built_at": _utc_now_iso(),
                "corpus_path": str(corpus_path),
                "embeddings_path": str(embeddings_path),
            }
        )

    SentenceTransformer, import_error = _safe_import_sentence_transformer()
    if SentenceTransformer is None:
        return _write_manifest(
            {
                "status": "fallback_only",
                "reason": import_error or "sentence-transformers import failed",
                "built_at": _utc_now_iso(),
                "corpus_path": str(corpus_path),
                "embeddings_path": str(embeddings_path),
                "item_count": len(corpus),
                "model_name": model_name,
            }
        )

    texts: List[str] = [_compose_chunk_text(chunk) for chunk in corpus]

    try:
        encoder = SentenceTransformer(model_name)
        embeddings = encoder.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as exc:
        return _write_manifest(
            {
                "status": "fallback_only",
                "reason": f"Embedding build failed: {exc}",
                "built_at": _utc_now_iso(),
                "corpus_path": str(corpus_path),
                "embeddings_path": str(embeddings_path),
                "item_count": len(corpus),
                "model_name": model_name,
            }
        )

    embeddings = np.asarray(embeddings, dtype=np.float32)
    np.save(embeddings_path, embeddings)

    return _write_manifest(
        {
            "status": "ready",
            "reason": "",
            "built_at": _utc_now_iso(),
            "corpus_path": str(corpus_path),
            "embeddings_path": str(embeddings_path),
            "model_name": model_name,
            "item_count": len(corpus),
            "embedding_dim": int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
        }
    )


def main() -> None:
    result = build_embedding_index()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
