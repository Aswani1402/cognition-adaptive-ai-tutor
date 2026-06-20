from typing import Any


def _make_chunk(bundle: dict[str, Any], chunk_type: str, chunk_text: str, chunk_order: int) -> dict[str, Any] | None:
    text = (chunk_text or "").strip()
    if not text:
        return None

    return {
        "system_concept_id": str(bundle["system_concept_id"]),
        "content_concept_id": str(bundle["content_concept_id"]),
        "chunk_type": chunk_type,
        "chunk_text": text,
        "chunk_order": chunk_order,
        "source_db": bundle.get("source_db", ""),
    }


def make_definition_chunk(bundle: dict[str, Any], chunk_order: int = 1) -> dict[str, Any] | None:
    resource = bundle.get("resource_bundle", {})
    return _make_chunk(bundle, "definition", resource.get("definition", ""), chunk_order)


def make_example_chunks(bundle: dict[str, Any], start_order: int = 1) -> list[dict[str, Any]]:
    resource = bundle.get("resource_bundle", {})
    chunks: list[dict[str, Any]] = []
    order = start_order
    for example in resource.get("examples", []):
        chunk = _make_chunk(bundle, "example", example, order)
        if chunk:
            chunks.append(chunk)
            order += 1
    return chunks


def make_key_point_chunks(bundle: dict[str, Any], start_order: int = 1) -> list[dict[str, Any]]:
    resource = bundle.get("resource_bundle", {})
    chunks: list[dict[str, Any]] = []
    order = start_order
    for key_point in resource.get("key_points", []):
        chunk = _make_chunk(bundle, "key_point", key_point, order)
        if chunk:
            chunks.append(chunk)
            order += 1
    return chunks


def make_misconception_chunks(bundle: dict[str, Any], start_order: int = 1) -> list[dict[str, Any]]:
    resource = bundle.get("resource_bundle", {})
    chunks: list[dict[str, Any]] = []
    order = start_order
    for misconception in resource.get("misconceptions", []):
        chunk = _make_chunk(bundle, "misconception", misconception, order)
        if chunk:
            chunks.append(chunk)
            order += 1
    return chunks


def make_practice_idea_chunks(bundle: dict[str, Any], start_order: int = 1) -> list[dict[str, Any]]:
    resource = bundle.get("resource_bundle", {})
    chunks: list[dict[str, Any]] = []
    order = start_order
    for idea in resource.get("practice_ideas", []):
        chunk = _make_chunk(bundle, "practice_idea", idea, order)
        if chunk:
            chunks.append(chunk)
            order += 1
    return chunks


def chunk_resource_bundle(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    if not bundle or bundle.get("status") != "success":
        return []

    chunks: list[dict[str, Any]] = []
    order = 1

    definition_chunk = make_definition_chunk(bundle, chunk_order=order)
    if definition_chunk:
        chunks.append(definition_chunk)
        order += 1

    for producer in (
        make_example_chunks,
        make_key_point_chunks,
        make_misconception_chunks,
        make_practice_idea_chunks,
    ):
        generated = producer(bundle, start_order=order)
        chunks.extend(generated)
        order += len(generated)

    return chunks
