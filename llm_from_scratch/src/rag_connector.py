import inspect
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_MAIN_TUTOR_PATH = Path(
    r"C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\cognition_adaptive_AI_tutor"
)

OUTPUT_DIR = ROOT_DIR / "outputs" / "rag_connector"
OUTPUT_JSON = OUTPUT_DIR / "rag_connector_demo.json"
OUTPUT_MD = OUTPUT_DIR / "rag_connector_demo.md"


PREFERRED_RAG_FUNCTIONS = [
    "get_rag_context",
    "build_rag_context",
    "retrieve_context",
    "build_context",
    "get_context",
]

OBJECT_REPR_MARKERS = [
    "<tutor.rag.rag_context_builder.RAGContextBuilder object at",
    "<__main__.RAGContextBuilder object at",
]


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def short_text(value: Any, max_chars: int = 500) -> str:
    text = normalize_text(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].strip() + "..."


class RagConnector:
    """
    Connector between CogniTutorLM-from-scratch and the main tutor RAG.

    Main tutor RAG path:
    cognition_adaptive_AI_tutor/tutor/rag/

    Current confirmed RAG:
    - rag_chunk_store.py
    - rag_context_builder.py
    - local/no API
    - source: option_c_plus_rag
    - 228 chunks
    - section-aware chunks from concept_resources

    This connector normalizes any RAG output into:

    {
      "status": "success",
      "source": "main_tutor_rag",
      "concept_id": "...",
      "domain": "...",
      "query": "...",
      "chunks": [...],
      "context_text": "..."
    }
    """

    def __init__(self, main_tutor_path: Optional[Path] = None):
        env_path = os.environ.get("MAIN_TUTOR_PROJECT_PATH")
        self.main_tutor_path = Path(env_path) if env_path else (main_tutor_path or DEFAULT_MAIN_TUTOR_PATH)

        self.rag_module = None
        self.rag_builder_class = None
        self.rag_function = None
        self.import_error = None

        self._load_main_rag()

    @contextmanager
    def _main_tutor_cwd(self):
        old_cwd = Path.cwd()
        try:
            os.chdir(self.main_tutor_path)
            yield
        finally:
            os.chdir(old_cwd)

    def _load_main_rag(self) -> None:
        if not self.main_tutor_path.exists():
            self.import_error = f"Main tutor path not found: {self.main_tutor_path}"
            return

        main_path_str = str(self.main_tutor_path)

        if main_path_str not in sys.path:
            sys.path.insert(0, main_path_str)

        try:
            from tutor.rag.rag_context_builder import build_rag_concept_resource  # type: ignore

            self.rag_module = "tutor.rag.rag_context_builder"
            self.rag_builder_class = None
            self.rag_function = build_rag_concept_resource

        except Exception as exc:
            self.import_error = f"Failed to import main tutor RAG: {exc}"

    def _find_rag_function(self, module: Any) -> Optional[Any]:
        for name in PREFERRED_RAG_FUNCTIONS:
            fn = getattr(module, name, None)
            if callable(fn):
                return fn

        # Fallback: find any callable with "rag" and "context" in name.
        for name in dir(module):
            lower = name.lower()
            if "rag" in lower and "context" in lower:
                fn = getattr(module, name, None)
                if callable(fn):
                    return fn

        return None

    def get_rag_context(
            self,
            query: str,
            concept_id: Optional[str] = None,
            domain: Optional[str] = None,
            top_k: int = 5,
    ) -> Dict[str, Any]:
        if self.import_error:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason=self.import_error,
            )

        if self.rag_module is None:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason="RAG module was not loaded.",
            )

        if self.rag_function is None:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason="build_rag_concept_resource function was not loaded.",
            )

        try:
            raw_result = self._call_rag_resource_function(
                fn=self.rag_function,
                query=query,
                concept_id=concept_id,
                domain=domain,
                top_k=top_k,
            )

            return self.normalize_rag_output(
                raw_result=raw_result,
                query=query,
                concept_id=concept_id,
                domain=domain,
                top_k=top_k,
            )

        except Exception as exc:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason=f"RAG call failed: {exc}",
            )




    def _call_rag_resource_function(
            self,
            fn: Any,
            query: str,
            concept_id: Optional[str],
            domain: Optional[str],
            top_k: int,
    ) -> Any:
        """
        Call main tutor build_rag_concept_resource().
        This is the preferred RAG interface because it accepts query/domain/concept_id/top_k.
        """

        signature = inspect.signature(fn)
        params = signature.parameters

        kwargs = {}

        if "query" in params:
            kwargs["query"] = query

        if "domain" in params:
            kwargs["domain"] = domain

        if "concept_id" in params:
            kwargs["concept_id"] = concept_id

        if "concept_name" in params:
            kwargs["concept_name"] = None

        if "top_k" in params:
            kwargs["top_k"] = top_k

        with self._main_tutor_cwd():
            return fn(**kwargs)

    def normalize_rag_output(
        self,
        raw_result: Any,
        query: str,
        concept_id: Optional[str] = None,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        if raw_result is None:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason="RAG returned None.",
            )
        if not isinstance(raw_result, (dict, list, str)):
            raw_result = self._object_to_dict(raw_result)

        if isinstance(raw_result, list):
            raw = {
                "status": "success",
                "chunks": raw_result,
            }
        elif isinstance(raw_result, dict):
            raw = raw_result
        else:
            raw = self._object_to_dict(raw_result)

        resolved_domain = raw.get("domain") or domain
        resolved_concept_id = raw.get("concept_id") or raw.get("content_concept_id") or concept_id
        resolved_topic = raw.get("topic") or raw.get("concept_name") or raw.get("concept_title")

        chunks = self._extract_chunks(raw, resolved_domain, resolved_concept_id, resolved_topic)

        context_text = self._build_context_text(raw, chunks)

        if self._looks_like_object_repr(context_text):
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason="RAG returned an object repr instead of meaningful context text.",
            )

        if raw.get("status") == "success" and not chunks and not context_text:
            return self._fallback_response(
                query=query,
                concept_id=concept_id,
                domain=domain,
                reason="RAG returned success without chunks or context text.",
            )

        return {
            "status": raw.get("status", "success") if context_text or chunks else "fallback",
            "source": raw.get("source", "main_tutor_rag"),
            "connector_source": "CogniTutorLM.rag_connector",
            "rag_connected": True,
            "query": query,
            "concept_id": resolved_concept_id,
            "concept_name": resolved_topic,
            "domain": resolved_domain,
            "top_k": top_k,
            "chunks": chunks[:top_k],
            "context_text": context_text,
            "raw_summary": {
                "definition_preview": raw.get("definition_preview"),
                "examples_count": raw.get("examples_count"),
                "key_points_count": raw.get("key_points_count"),
                "misconceptions_count": raw.get("misconceptions_count"),
                "chunk_count": raw.get("chunk_count") or len(chunks),
            },
        }

    def _object_to_dict(self, raw_result: Any) -> Dict[str, Any]:
        raw = {}

        for attr in [
            "status",
            "source",
            "domain",
            "concept_id",
            "content_concept_id",
            "topic",
            "concept_name",
            "definition",
            "definition_preview",
            "examples",
            "key_points",
            "misconceptions",
            "chunks",
            "retrieved_chunks",
            "context_text",
            "chunk_count",
        ]:
            if hasattr(raw_result, attr):
                raw[attr] = getattr(raw_result, attr)

        if raw:
            return raw

        return {
            "status": "error",
            "context_text": str(raw_result),
            "chunks": [],
        }

    def _looks_like_object_repr(self, value: Any) -> bool:
        text = str(value or "").strip()

        if not text:
            return False

        if text.startswith("<") and " object at 0x" in text and text.endswith(">"):
            return True

        return any(marker in text for marker in OBJECT_REPR_MARKERS)

    def _extract_chunks(
        self,
        raw: Dict[str, Any],
        domain: Optional[str],
        concept_id: Optional[str],
        concept_name: Optional[str],
    ) -> List[Dict[str, Any]]:
        chunks = []

        raw_chunks = raw.get("chunks") or raw.get("retrieved_chunks") or raw.get("results") or []

        if isinstance(raw_chunks, list):
            for idx, item in enumerate(raw_chunks):
                if isinstance(item, dict):
                    chunks.append(
                        {
                            "section": item.get("section") or item.get("section_tag") or "context",
                            "text": item.get("text") or item.get("content") or item.get("preview") or "",
                            "score": item.get("score") or item.get("similarity") or item.get("rank_score") or 1.0,
                            "source_db": item.get("source_db"),
                            "concept_id": item.get("concept_id") or item.get("content_concept_id") or concept_id,
                            "concept_name": item.get("concept_name") or item.get("topic") or concept_name,
                            "domain": item.get("domain") or domain,
                            "chunk_id": item.get("chunk_id") or f"chunk_{idx + 1}",
                        }
                    )
                else:
                    chunks.append(
                        {
                            "section": "context",
                            "text": str(item),
                            "score": 1.0,
                            "source_db": None,
                            "concept_id": concept_id,
                            "concept_name": concept_name,
                            "domain": domain,
                            "chunk_id": f"chunk_{idx + 1}",
                        }
                    )

        # Main RAG demo output gives summary fields, not full chunks.
        # Convert summary previews/counts into normalized pseudo-chunks.
        definition_text = raw.get("definition_preview") or raw.get("definition")
        if definition_text:
            chunks.append(
                {
                    "section": "definition",
                    "text": definition_text,
                    "score": 1.0,
                    "source_db": raw.get("source_db"),
                    "concept_id": concept_id,
                    "concept_name": concept_name,
                    "domain": domain,
                    "chunk_id": f"{domain}:{concept_id}:definition_preview",
                }
            )

        for section_name, field_name in [
            ("examples", "examples"),
            ("key_points", "key_points"),
            ("misconceptions", "misconceptions"),
            ("real_world_use", "real_world_use"),
            ("next_concept_link", "next_concept_link"),
        ]:
            value = raw.get(field_name)

            if isinstance(value, list):
                text = "\n".join(str(x) for x in value)
            else:
                text = str(value or "").strip()

            if text:
                chunks.append(
                    {
                        "section": section_name,
                        "text": text,
                        "score": 0.9,
                        "source_db": raw.get("source_db"),
                        "concept_id": concept_id,
                        "concept_name": concept_name,
                        "domain": domain,
                        "chunk_id": f"{domain}:{concept_id}:{section_name}",
                    }
                )

        return [chunk for chunk in chunks if chunk.get("text")]

    def _build_context_text(
        self,
        raw: Dict[str, Any],
        chunks: List[Dict[str, Any]],
    ) -> str:
        if raw.get("context_text") and not self._looks_like_object_repr(raw.get("context_text")):
            return str(raw["context_text"]).strip()

        parts = []

        for chunk in chunks:
            section = chunk.get("section", "context")
            text = chunk.get("text", "")
            if text:
                parts.append(f"[{section}]\n{text}")

        return "\n\n".join(parts).strip()

    def _fallback_response(
        self,
        query: str,
        concept_id: Optional[str],
        domain: Optional[str],
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "status": "fallback",
            "source": "rag_connector_fallback",
            "connector_source": "CogniTutorLM.rag_connector",
            "rag_connected": False,
            "query": query,
            "concept_id": concept_id,
            "concept_name": None,
            "domain": domain,
            "chunks": [],
            "context_text": "",
            "reason": reason,
        }


def build_markdown(results: List[Dict[str, Any]]) -> str:
    lines = []

    lines.append("# CogniTutorLM RAG Connector Demo")
    lines.append("")
    lines.append("This report verifies the connector between CogniTutorLM and the main tutor RAG.")
    lines.append("")

    for result in results:
        lines.append(f"## Query: {result.get('query')}")
        lines.append("")
        lines.append(f"- Status: `{result.get('status')}`")
        lines.append(f"- Source: `{result.get('source')}`")
        lines.append(f"- RAG connected: `{result.get('rag_connected')}`")
        lines.append(f"- Domain: `{result.get('domain')}`")
        lines.append(f"- Concept ID: `{result.get('concept_id')}`")
        lines.append(f"- Concept name: `{result.get('concept_name')}`")
        lines.append(f"- Chunk count: `{len(result.get('chunks', []))}`")
        lines.append("")

        if result.get("reason"):
            lines.append(f"Reason: {result['reason']}")
            lines.append("")

        lines.append("### Context Preview")
        lines.append("")
        lines.append(short_text(result.get("context_text"), 700))
        lines.append("")

        lines.append("### Chunks")
        lines.append("")
        for chunk in result.get("chunks", [])[:5]:
            lines.append(
                f"- **{chunk.get('section')}** | score={chunk.get('score')} | "
                f"{short_text(chunk.get('text'), 180)}"
            )
        lines.append("")

    return "\n".join(lines)


def run_self_test() -> None:
    print("\nRagConnector self-test")
    print("=" * 80)

    connector = RagConnector()

    test_cases = [
        {
            "query": "Python variables store values",
            "concept_id": "P1",
            "domain": "Python",
        },
        {
            "query": "why 2score is wrong",
            "concept_id": "P1",
            "domain": "Python",
        },
        {
            "query": "HTML tags and elements",
            "concept_id": "H2",
            "domain": "HTML",
        },
        {
            "query": "What should I study after SELECT?",
            "concept_id": "S2",
            "domain": "SQL",
        },
    ]

    results = []

    for case in test_cases:
        result = connector.get_rag_context(**case, top_k=5)
        results.append(result)

        print("\nQuery")
        print("-" * 80)
        print("status:", result.get("status"))
        print("source:", result.get("source"))
        print("domain:", result.get("domain"))
        print("concept_id:", result.get("concept_id"))
        print("concept_name/topic:", result.get("concept_name"))
        print("chunk_count:", len(result.get("chunks", [])))
        print("context_text preview:", short_text(result.get("context_text"), 300))
        print("")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2500])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with OUTPUT_MD.open("w", encoding="utf-8") as f:
        f.write(build_markdown(results))

    print("\nRAG connector demo saved.")
    print(f"JSON: {OUTPUT_JSON}")
    print(f"Markdown: {OUTPUT_MD}")
    print("\nSelf-test complete.")


if __name__ == "__main__":
    run_self_test()
