from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path("external/core_data/tutor.db")

SEARCH_SOURCE_TABLES = [
    "learner_mistake_log",
    "learner_doubt_log",
    "learner_revision_log",
    "revision_schedule",
    "revision_card",
    "learner_session_log",
    "learner_profile",
    "knowledge_state",
    "behaviour_state",
    "teaching_strategy_log",
    "xai_log",
    "learner_notebook_memory",
]

TIMESTAMP_COLUMNS = [
    "created_at",
    "updated_at",
    "last_activity_at",
    "due_at",
    "last_seen_at",
    "timestamp",
]


class SemanticNotebookSearch:
    """SQLite-backed learner memory search with local TF-IDF and keyword fallback."""

    MODULE = "SemanticNotebookSearch"

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH, force_keyword: bool = False) -> None:
        self.db_path = Path(db_path)
        self.force_keyword = force_keyword

    def build_search_index(self, learner_id: str) -> dict[str, Any]:
        records = self._collect_records(str(learner_id))
        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": str(learner_id),
            "record_count": len(records),
            "source_tables": sorted({record["source_table"] for record in records}),
            "records": records,
        }

    def search(
        self,
        learner_id: str,
        query: str,
        top_k: int = 5,
        source_filter: str | None = None,
    ) -> dict[str, Any]:
        learner_id = str(learner_id)
        query = str(query or "").strip()
        top_k = max(1, int(top_k or 5))
        index = self.build_search_index(learner_id)
        records = index["records"]
        if source_filter:
            records = [record for record in records if record["source_table"] == source_filter]

        method = "keyword_fallback"
        fallback_used = True
        scored: list[dict[str, Any]] = []
        if records and query and not self.force_keyword:
            try:
                scored = self._tfidf_search(records, query)
                method = "tfidf_cosine"
                fallback_used = False
            except Exception:
                scored = self._keyword_search(records, query)
        else:
            scored = self._keyword_search(records, query)

        results = [
            self._result_payload(record, score)
            for record, score in scored[:top_k]
            if score > 0 or not query
        ]
        if not results and records:
            results = [self._result_payload(record, 0.0) for record in records[:top_k]]

        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": learner_id,
            "query": query,
            "method": method,
            "result_count": len(results),
            "results": results,
            "fallback_used": fallback_used,
        }

    def get_weakness_summary(self, learner_id: str) -> dict[str, Any]:
        learner_id = str(learner_id)
        records = self._collect_records(learner_id)
        weak_concepts = Counter()
        mistake_types = Counter()
        question_types = Counter()
        recent_doubts = []
        revision_focus = Counter()

        for record in records:
            concept = record.get("concept_name")
            if concept and any(tag in record["tags"] for tag in ["mistake", "weakness", "revision"]):
                weak_concepts[concept] += 1
            row = record.get("row", {})
            for key in ["mistake_type", "doubt_type", "task_type", "question_type", "assessment_type"]:
                value = row.get(key)
                if value and "mistake" in key:
                    mistake_types[str(value)] += 1
                elif value and key in {"task_type", "question_type", "assessment_type"}:
                    question_types[str(value)] += 1
            if record["source_table"] == "learner_doubt_log":
                recent_doubts.append(
                    {
                        "concept_name": concept,
                        "summary": record["summary"],
                        "timestamp": record.get("timestamp"),
                    }
                )
            if any(tag in record["tags"] for tag in ["revision", "schedule"]):
                revision_focus[concept or record["source_table"]] += 1

        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": learner_id,
            "weak_concepts": [item for item, _ in weak_concepts.most_common(8)],
            "dominant_mistake_types": [item for item, _ in mistake_types.most_common(8)],
            "weak_question_types": [item for item, _ in question_types.most_common(8)],
            "recent_doubts": recent_doubts[:8],
            "recommended_revision_focus": [item for item, _ in revision_focus.most_common(8)],
        }

    def get_recent_mistakes(self, learner_id: str, limit: int = 10) -> dict[str, Any]:
        records = [
            record
            for record in self._collect_records(str(learner_id))
            if record["source_table"] == "learner_mistake_log"
        ][: max(1, int(limit or 10))]
        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": str(learner_id),
            "mistake_count": len(records),
            "mistakes": [self._result_payload(record, 1.0) for record in records],
        }

    def get_revision_memory(self, learner_id: str, limit: int = 10) -> dict[str, Any]:
        records = [
            record
            for record in self._collect_records(str(learner_id))
            if "revision" in record["tags"] or record["source_table"] in {"revision_card", "revision_schedule"}
        ][: max(1, int(limit or 10))]
        return {
            "status": "success",
            "module": self.MODULE,
            "learner_id": str(learner_id),
            "revision_count": len(records),
            "revision_items": [self._result_payload(record, 1.0) for record in records],
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _collect_records(self, learner_id: str) -> list[dict[str, Any]]:
        if not self.db_path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._connect() as conn:
            for table_name in SEARCH_SOURCE_TABLES:
                if not self._table_exists(conn, table_name):
                    continue
                columns = self._columns(conn, table_name)
                if "learner_id" not in columns:
                    continue
                rows = conn.execute(
                    f"SELECT rowid AS _rowid, * FROM {table_name} WHERE learner_id = ? ORDER BY rowid DESC LIMIT 200",
                    (learner_id,),
                ).fetchall()
                for row in rows:
                    record = self._record_from_row(table_name, dict(row), columns)
                    if record["text"]:
                        records.append(record)
        return records

    def _record_from_row(self, table_name: str, row: dict[str, Any], columns: set[str]) -> dict[str, Any]:
        text_parts = []
        for key, value in row.items():
            if key.startswith("_") or value in (None, ""):
                continue
            if key.endswith("_json"):
                text_parts.append(str(value))
            elif key in {
                "concept_id",
                "concept_name",
                "domain",
                "task_type",
                "question_id",
                "mistake_type",
                "severity",
                "learner_answer",
                "expected_answer",
                "feedback",
                "doubt_text",
                "doubt_type",
                "answer_summary",
                "revision_view",
                "revision_reason",
                "status",
                "prompt",
                "answer",
                "event_type",
                "event_json",
                "display_name",
                "profile_json",
                "notebook_summary",
                "source_json",
                "strategy",
                "reason",
                "primary_decision",
                "primary_output",
            }:
                text_parts.append(str(value))
        tags = self._tags_for_table(table_name, row)
        return {
            "source_table": table_name,
            "record_id": str(row.get("id") or row.get("_rowid") or ""),
            "concept_id": row.get("concept_id") or row.get("current_concept_id"),
            "concept_name": row.get("concept_name") or row.get("current_concept_name"),
            "summary": self._summary_for_row(table_name, row),
            "timestamp": self._timestamp(row),
            "tags": tags,
            "text": self._normalize(" ".join(text_parts)),
            "row": row,
        }

    def _tfidf_search(self, records: list[dict[str, Any]], query: str) -> list[tuple[dict[str, Any], float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        corpus = [record["text"] for record in records]
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(corpus + [self._normalize(query)])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten().tolist()
        return sorted(zip(records, scores), key=lambda item: item[1], reverse=True)

    def _keyword_search(self, records: list[dict[str, Any]], query: str) -> list[tuple[dict[str, Any], float]]:
        query_tokens = set(self._tokens(query))
        scored = []
        for record in records:
            tokens = set(self._tokens(record["text"]))
            overlap = len(query_tokens & tokens)
            score = overlap / max(1, len(query_tokens)) if query_tokens else 1.0
            scored.append((record, float(score)))
        return sorted(scored, key=lambda item: item[1], reverse=True)

    def _result_payload(self, record: dict[str, Any], score: float) -> dict[str, Any]:
        return {
            "source_table": record["source_table"],
            "record_id": record["record_id"],
            "concept_id": record.get("concept_id"),
            "concept_name": record.get("concept_name"),
            "summary": record["summary"],
            "score": round(float(score), 6),
            "timestamp": record.get("timestamp"),
            "tags": record["tags"],
        }

    def _table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        ).fetchone()
        return bool(row)

    def _columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

    def _summary_for_row(self, table_name: str, row: dict[str, Any]) -> str:
        if table_name == "learner_mistake_log":
            return self._clean(
                f"{row.get('concept_name') or 'Concept'} mistake: {row.get('mistake_type') or row.get('task_type')}. {row.get('feedback') or row.get('learner_answer') or ''}"
            )
        if table_name == "learner_doubt_log":
            return self._clean(f"Doubt: {row.get('doubt_text') or ''} {row.get('answer_summary') or ''}")
        if table_name == "revision_card":
            return self._clean(f"Revision card: {row.get('prompt') or ''} {row.get('answer') or ''}")
        if table_name == "revision_schedule":
            return self._clean(f"Revision due for {row.get('concept_name') or 'concept'}: {row.get('reason') or row.get('priority') or ''}")
        if table_name == "learner_notebook_memory":
            return self._clean(row.get("notebook_summary") or "")
        return self._clean(" ".join(str(v) for k, v in row.items() if not k.startswith("_") and v not in (None, "")))[:320]

    def _tags_for_table(self, table_name: str, row: dict[str, Any]) -> list[str]:
        base = {
            "learner_mistake_log": ["mistake", "weakness"],
            "learner_doubt_log": ["doubt"],
            "learner_revision_log": ["revision"],
            "revision_schedule": ["revision", "schedule"],
            "revision_card": ["revision", "card"],
            "learner_session_log": ["session"],
            "learner_profile": ["profile"],
            "knowledge_state": ["knowledge"],
            "behaviour_state": ["behaviour"],
            "teaching_strategy_log": ["strategy"],
            "xai_log": ["xai"],
            "learner_notebook_memory": ["notebook", "weakness"],
        }.get(table_name, ["memory"])
        extras = []
        for key in ["task_type", "mistake_type", "doubt_type", "revision_view", "status"]:
            if row.get(key):
                extras.append(str(row[key]).lower().replace(" ", "_"))
        return list(dict.fromkeys([*base, *extras]))

    def _timestamp(self, row: dict[str, Any]) -> Any:
        for column in TIMESTAMP_COLUMNS:
            if row.get(column):
                return row.get(column)
        return None

    def _normalize(self, text: Any) -> str:
        return self._clean(str(text or "")).lower()

    def _clean(self, text: Any) -> str:
        return re.sub(r"\s+", " ", str(text or "")).strip()

    def _tokens(self, text: Any) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", self._normalize(text))
