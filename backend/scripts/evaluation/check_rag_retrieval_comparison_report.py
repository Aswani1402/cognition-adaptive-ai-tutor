from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

from tutor.rag.option_c_tfidf_retriever import OptionCTFIDFRetriever
from tutor.rag.rag_chunk_store import RAGChunkStore
from tutor.rag.rag_context_builder import RAGContextBuilder
from tutor.rag.rag_grounding_checker import check_rag_grounding


PROJECT_ROOT = Path(__file__).resolve().parents[2]
JSON_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "rag_retrieval_comparison_report.json"
MD_REPORT = PROJECT_ROOT / "evaluation_outputs" / "reports" / "rag_retrieval_comparison_report.md"
RAG_GROUNDING_REPORT = PROJECT_ROOT / "evaluation_outputs" / "json" / "rag_grounding_report.json"

USEFUL_SECTIONS = {"definition", "examples", "key_points", "misconceptions", "real_world_use"}
SECTION_PRIORITY = {
    "definition": 1.00,
    "examples": 0.95,
    "key_points": 0.92,
    "misconceptions": 0.88,
    "real_world_use": 0.82,
    "next_concept": 0.35,
    "next_concept_link": 0.35,
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "rows",
    "the",
    "to",
    "why",
}

TEST_QUERIES = [
    {
        "query": "Python variables store values",
        "expected_domain": "Python",
        "expected_concepts": ["Variables"],
    },
    {
        "query": "why 2score is wrong",
        "expected_domain": "Python",
        "expected_concepts": ["Variables"],
    },
    {
        "query": "SQL SELECT filter rows",
        "expected_domain": "SQL",
        "expected_concepts": ["SELECT", "WHERE & Filters", "Where Filters"],
    },
    {
        "query": "HTML tags and elements",
        "expected_domain": "HTML",
        "expected_concepts": ["HTML Tags and Elements", "Tags and Elements"],
    },
    {
        "query": "Git commit history",
        "expected_domain": "Git",
        "expected_concepts": ["Commits & History", "Commits and History"],
    },
    {
        "query": "arrays index access",
        "expected_domain": "Data Structures",
        "expected_concepts": ["Arrays"],
    },
    {
        "query": "SQL JOIN combine tables",
        "expected_domain": "SQL",
        "expected_concepts": ["JOIN", "Joins"],
    },
    {
        "query": "Python loops repeat code",
        "expected_domain": "Python",
        "expected_concepts": ["Loops"],
    },
    {
        "query": "HTML forms input",
        "expected_domain": "HTML",
        "expected_concepts": ["Forms & Inputs", "Forms and Inputs"],
    },
    {
        "query": "Git branch merge conflict",
        "expected_domain": "Git",
        "expected_concepts": ["Merge & Conflict Basics", "Merge and Conflict Basics"],
    },
]


def _tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9_]+", str(text).lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _chunk_text(chunk: dict[str, Any]) -> str:
    return " ".join(
        str(chunk.get(key, "") or "")
        for key in ["domain", "topic", "concept_name", "section", "content", "text", "chunk_text"]
    )


def _chunk_topic(chunk: dict[str, Any]) -> str:
    return str(chunk.get("topic") or chunk.get("concept_name") or chunk.get("concept") or "")


def _chunk_domain(chunk: dict[str, Any]) -> str:
    return str(chunk.get("domain") or "")


def _with_text_field(chunk: dict[str, Any]) -> dict[str, Any]:
    item = dict(chunk)
    item.setdefault("text", item.get("content", ""))
    item.setdefault("concept_name", item.get("topic", ""))
    item.setdefault("concept_id", item.get("content_concept_id", ""))
    return item


def _domain_match(chunk: dict[str, Any], expected_domain: str) -> bool:
    return _norm(_chunk_domain(chunk)) == _norm(expected_domain)


def _concept_match(chunk: dict[str, Any], expected_concepts: list[str]) -> bool:
    topic = _norm(_chunk_topic(chunk))
    content = _norm(chunk.get("content", ""))
    for concept in expected_concepts:
        expected = _norm(concept)
        if expected and (expected == topic or expected in topic or topic in expected or expected in content):
            return True
    return False


def _concept_and_domain_match(chunk: dict[str, Any], expected_domain: str, expected_concepts: list[str]) -> bool:
    return _domain_match(chunk, expected_domain) and _concept_match(chunk, expected_concepts)


class LocalBM25Retriever:
    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.documents = [_tokens(_chunk_text(chunk)) for chunk in chunks]
        self.doc_lengths = [len(doc) for doc in self.documents]
        self.avg_doc_length = mean(self.doc_lengths) if self.doc_lengths else 1.0
        self.idf = self._build_idf()

    def _build_idf(self) -> dict[str, float]:
        total_docs = len(self.documents)
        df: Counter[str] = Counter()
        for doc in self.documents:
            for token in set(doc):
                df[token] += 1
        return {
            token: math.log(1 + ((total_docs - count + 0.5) / (count + 0.5)))
            for token, count in df.items()
        }

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        k1 = 1.5
        b = 0.75
        scored = []
        for idx, doc_tokens in enumerate(self.documents):
            counts = Counter(doc_tokens)
            doc_len = self.doc_lengths[idx] or 1
            score = 0.0
            for token in query_tokens:
                tf = counts.get(token, 0)
                if not tf:
                    continue
                denominator = tf + k1 * (1 - b + b * doc_len / max(1.0, self.avg_doc_length))
                score += self.idf.get(token, 0.0) * ((tf * (k1 + 1)) / denominator)
            item = dict(self.chunks[idx])
            item["retrieval_score"] = round(score, 4)
            item["retriever"] = "local_bm25"
            scored.append(item)
        scored.sort(key=lambda item: item.get("retrieval_score", 0.0), reverse=True)
        return scored[:top_k]


class HeuristicReranker:
    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.bm25 = LocalBM25Retriever(chunks)

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        candidates = self.bm25.search(query, top_k=30)
        query_tokens = set(_tokens(query))
        reranked = []
        for item in candidates:
            text_tokens = set(_tokens(_chunk_text(item)))
            topic_tokens = set(_tokens(_chunk_topic(item)))
            domain_tokens = set(_tokens(_chunk_domain(item)))
            overlap = len(query_tokens & text_tokens) / max(1, len(query_tokens))
            topic_overlap = len(query_tokens & topic_tokens)
            domain_overlap = len(query_tokens & domain_tokens)
            section_weight = SECTION_PRIORITY.get(str(item.get("section", "")).lower(), 0.65)
            score = (
                0.55 * float(item.get("retrieval_score", 0.0))
                + 0.30 * overlap
                + 0.20 * topic_overlap
                + 0.12 * domain_overlap
                + 0.10 * section_weight
            )
            new_item = dict(item)
            new_item["retrieval_score"] = round(score, 4)
            new_item["reranker"] = "transparent_heuristic_reranker"
            reranked.append(new_item)
        reranked.sort(key=lambda item: item.get("retrieval_score", 0.0), reverse=True)
        return reranked[:top_k]


class DenseRetriever:
    def __init__(self) -> None:
        self.available = False
        self.reason = "Dense retrieval not initialized."
        self.corpus: list[dict[str, Any]] = []
        self.embeddings: np.ndarray | None = None
        self.encoder: Any = None
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self._load()

    def _load(self) -> None:
        index_path = PROJECT_ROOT / "models" / "rag" / "rag_embedding_index.json"
        embeddings_path = PROJECT_ROOT / "models" / "rag" / "rag_embeddings.npy"
        corpus_path = PROJECT_ROOT / "models" / "rag" / "rag_corpus.json"
        if not index_path.exists() or not embeddings_path.exists() or not corpus_path.exists():
            self.reason = "Dense retrieval artifacts are missing."
            return
        try:
            meta = json.loads(index_path.read_text(encoding="utf-8"))
            self.model_name = meta.get("model_name") or self.model_name
            self.embeddings = np.load(embeddings_path)
            self.corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.reason = f"Dense retrieval artifacts could not be loaded: {exc}"
            return
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            self.reason = f"sentence-transformers is unavailable: {exc}"
            return
        try:
            self.encoder = SentenceTransformer(self.model_name, local_files_only=True)
        except TypeError:
            self.reason = "Installed sentence-transformers does not expose safe local_files_only loading."
            return
        except Exception as exc:
            self.reason = f"Local dense query encoder is unavailable: {exc}"
            return
        if len(self.corpus) != int(self.embeddings.shape[0]):
            self.reason = "Dense corpus and embedding matrix sizes do not match."
            return
        self.available = True
        self.reason = "Dense retrieval is available from local artifacts."

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        if not self.available or self.encoder is None or self.embeddings is None:
            return []
        vector = self.encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
        scores = self.embeddings @ vector
        ranked = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in ranked:
            item = dict(self.corpus[int(idx)])
            item["retrieval_score"] = round(float(scores[int(idx)]), 4)
            item["retriever"] = "dense_local_sentence_transformer"
            if "topic" not in item and "concept_name" in item:
                item["topic"] = item.get("concept_name")
            if "content_concept_id" not in item and "concept_id" in item:
                item["content_concept_id"] = item.get("concept_id")
            results.append(item)
        return results


def _generated_text_for_grounding(query: str, ranking: list[dict[str, Any]]) -> str:
    top = ranking[0] if ranking else {}
    content = str(top.get("content") or top.get("text") or "")
    topic = _chunk_topic(top)
    return f"{query}. {topic}. {content[:450]}".strip()


def _evaluate_query(
    *,
    method: str,
    query_spec: dict[str, Any],
    ranking: list[dict[str, Any]],
    latency_ms: float,
) -> dict[str, Any]:
    query = query_spec["query"]
    expected_domain = query_spec["expected_domain"]
    expected_concepts = query_spec["expected_concepts"]
    top = ranking[0] if ranking else {}
    top3 = ranking[:3]
    context_found = bool(ranking)
    top_domain_match = bool(top and _domain_match(top, expected_domain))
    top_concept_match = bool(top and _concept_match(top, expected_concepts))
    top3_expected = any(_concept_and_domain_match(item, expected_domain, expected_concepts) for item in top3)
    topk_expected = any(_concept_and_domain_match(item, expected_domain, expected_concepts) for item in ranking)
    domain_topk = any(_domain_match(item, expected_domain) for item in ranking)
    reciprocal_rank = 0.0
    for idx, item in enumerate(ranking, start=1):
        if _concept_and_domain_match(item, expected_domain, expected_concepts):
            reciprocal_rank = 1.0 / idx
            break

    sections = sorted({str(item.get("section", "")).lower() for item in ranking if item.get("section")})
    useful_sections = sorted(set(sections) & USEFUL_SECTIONS)
    grounding = check_rag_grounding(
        generated_text=_generated_text_for_grounding(query, ranking),
        chunks=[_with_text_field(item) for item in ranking],
        concept_name=expected_concepts[0],
        domain=expected_domain,
    )

    return {
        "method": method,
        "query": query,
        "expected_domain": expected_domain,
        "expected_concepts": expected_concepts,
        "context_found": context_found,
        "top_domain": _chunk_domain(top),
        "top_concept": _chunk_topic(top),
        "top_section": str(top.get("section", "")),
        "top_concept_match": top_concept_match,
        "top_domain_match": top_domain_match,
        "expected_concept_found_in_top_k": topk_expected,
        "expected_domain_found_in_top_k": domain_topk,
        "precision_at_1": 1.0 if top_concept_match and top_domain_match else 0.0,
        "precision_at_3": 1.0 if top3_expected else 0.0,
        "reciprocal_rank": round(reciprocal_rank, 4),
        "section_coverage": round(len(useful_sections) / len(USEFUL_SECTIONS), 4),
        "useful_section_count": len(useful_sections),
        "sections": sections,
        "grounding_score": grounding.get("grounding_score", 0.0),
        "safe_to_generate": bool(grounding.get("safe_to_generate")),
        "fallback_needed": bool(grounding.get("fallback_recommended")),
        "latency_ms": round(latency_ms, 2),
    }


def _summarize(method: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "method": method,
            "query_count": 0,
            "available": False,
        }
    return {
        "method": method,
        "query_count": len(rows),
        "available": True,
        "context_found_rate": round(mean(1.0 if row["context_found"] else 0.0 for row in rows), 4),
        "domain_match_rate": round(mean(1.0 if row["top_domain_match"] else 0.0 for row in rows), 4),
        "concept_match_rate": round(mean(1.0 if row["top_concept_match"] else 0.0 for row in rows), 4),
        "precision_at_1": round(mean(float(row["precision_at_1"]) for row in rows), 4),
        "precision_at_3": round(mean(float(row["precision_at_3"]) for row in rows), 4),
        "mean_reciprocal_rank": round(mean(float(row["reciprocal_rank"]) for row in rows), 4),
        "average_grounding_score": round(mean(float(row["grounding_score"]) for row in rows), 4),
        "safe_to_generate_rate": round(mean(1.0 if row["safe_to_generate"] else 0.0 for row in rows), 4),
        "average_latency_ms": round(mean(float(row["latency_ms"]) for row in rows), 2),
    }


def _run_method(method: str, searcher: Any) -> list[dict[str, Any]]:
    rows = []
    for query_spec in TEST_QUERIES:
        start = time.perf_counter()
        ranking = searcher.search(query_spec["query"], top_k=8)
        latency_ms = (time.perf_counter() - start) * 1000.0
        rows.append(
            _evaluate_query(
                method=method,
                query_spec=query_spec,
                ranking=ranking,
                latency_ms=latency_ms,
            )
        )
    return rows


class OptionCSearchAdapter:
    def __init__(self) -> None:
        self.builder = RAGContextBuilder()

    def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        # Build context to exercise the active pipeline path, then use the
        # retriever ranking for top-k metrics so precision/MRR are meaningful.
        self.builder.build_context(query=query, top_k=top_k)
        return self.builder.retriever.search(query=query, top_k=top_k, candidate_k=30)


def _load_grounding_summary() -> dict[str, Any]:
    if not RAG_GROUNDING_REPORT.exists():
        return {"exists": False}
    try:
        data = json.loads(RAG_GROUNDING_REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"exists": True, "error": str(exc)}
    return {
        "exists": True,
        "status": data.get("status") or data.get("overall_status"),
        "module": data.get("module"),
        "summary": data.get("summary", {}),
    }


def _write_reports(report: dict[str, Any]) -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    MD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# RAG Retrieval Comparison Report",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Method Summary",
        "",
        "| Method | Queries | Context | Domain@1 | Concept@1 | P@3 | MRR | Grounding | Safe Rate | Avg Latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in report["method_summaries"]:
        if not item.get("available"):
            lines.append(f"| {item['method']} | 0 | unavailable | - | - | - | - | - | - | - |")
            continue
        lines.append(
            "| {method} | {query_count} | {context_found_rate} | {domain_match_rate} | "
            "{concept_match_rate} | {precision_at_3} | {mean_reciprocal_rank} | "
            "{average_grounding_score} | {safe_to_generate_rate} | {average_latency_ms} |".format(**item)
        )

    lines.extend(
        [
            "",
            "## Availability",
            "",
        ]
    )
    for key, value in report["availability"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(
        [
            "",
            "## Classification",
            "",
            "- Option C remains the main local, no-API RAG baseline.",
            "- BM25 provides a transparent keyword baseline.",
            "- Heuristic reranker is a transparent comparison method, not a trained reranker.",
            "- Dense retrieval is used only when local query encoder artifacts can be loaded safely.",
            "",
            "## Limitations",
            "",
        ]
    )
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")

    lines.extend(
        [
            "",
            "## Future Upgrade Plan",
            "",
        ]
    )
    for step in report["future_upgrade_plan"]:
        lines.append(f"- {step}")

    MD_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_report() -> dict[str, Any]:
    chunks = RAGChunkStore().load_all_chunks()
    method_rows: dict[str, list[dict[str, Any]]] = {}
    availability: dict[str, Any] = {
        "chunk_count": len(chunks),
        "sections": sorted({str(chunk.get("section", "")) for chunk in chunks if chunk.get("section")}),
    }

    option_c_rows = _run_method("option_c_plus_rag", OptionCSearchAdapter())
    bm25_rows = _run_method("local_bm25", LocalBM25Retriever(chunks))
    heuristic_rows = _run_method("heuristic_reranker", HeuristicReranker(chunks))
    method_rows["option_c_plus_rag"] = option_c_rows
    method_rows["local_bm25"] = bm25_rows
    method_rows["heuristic_reranker"] = heuristic_rows

    dense = DenseRetriever()
    availability["dense_retrieval"] = "available" if dense.available else f"unavailable: {dense.reason}"
    if dense.available:
        method_rows["dense_retrieval"] = _run_method("dense_retrieval", dense)

    availability["rag_grounding_report"] = _load_grounding_summary()
    availability["option_c_plus_rag"] = "available"
    availability["local_bm25"] = "available"
    availability["heuristic_reranker"] = "available"

    method_summaries = [_summarize(method, rows) for method, rows in method_rows.items()]
    if not dense.available:
        method_summaries.append({"method": "dense_retrieval", "query_count": 0, "available": False, "reason": dense.reason})

    limitations = [
        "Dense retrieval is marked unavailable unless the local sentence-transformer query encoder can be loaded without network access.",
        "Heuristic reranking is transparent scoring, not a trained cross-encoder reranker.",
        "Expected concept labels are manually defined for ten audit queries, so this is a focused readiness evaluation rather than a full IR benchmark.",
        "Grounding score is keyword/section based and should later be complemented by semantic entailment or human relevance judgments.",
    ]
    future_upgrade_plan = [
        "Add a larger labeled query-to-concept benchmark with negative cases.",
        "Evaluate local dense retrieval using a pinned local embedding model artifact.",
        "Train or validate a reranker on tutor chunk relevance labels.",
        "Track recall@k, nDCG, MRR, latency, grounding safety, and source diversity in CI reports.",
        "Keep Option C as safe fallback until dense/reranker methods outperform it reliably.",
    ]

    required_methods_available = bool(option_c_rows and bm25_rows and heuristic_rows)
    status = "success" if required_methods_available and dense.available else "warning"
    if not required_methods_available:
        status = "error"

    return {
        "status": status,
        "module": "rag_retrieval_comparison_report",
        "current_active_source": "option_c_plus_rag",
        "query_count": len(TEST_QUERIES),
        "test_queries": TEST_QUERIES,
        "availability": availability,
        "method_summaries": method_summaries,
        "per_query_results": method_rows,
        "limitations": limitations,
        "future_upgrade_plan": future_upgrade_plan,
    }


def main() -> None:
    report = build_report()
    _write_reports(report)
    print(f"STATUS: {report['status']}")
    print("MODULE: rag_retrieval_comparison_report")
    print(f"JSON_REPORT: {JSON_REPORT}")
    print(f"MD_REPORT: {MD_REPORT}")


if __name__ == "__main__":
    main()
