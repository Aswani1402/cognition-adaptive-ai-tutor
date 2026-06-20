import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


CORE_DATA_DIR = Path("external/core_data")
OUTPUT_DIR = Path("models/rag")
OUTPUT_PATH = OUTPUT_DIR / "rag_corpus.json"


SUBJECT_DBS = [
    {
        "domain": "Python",
        "db_name": "python_learning.db",
    },
    {
        "domain": "SQL",
        "db_name": "database_sql.db",
    },
    {
        "domain": "HTML",
        "db_name": "html_web_basics.db",
    },
    {
        "domain": "Git",
        "db_name": "git_version_control.db",
    },
    {
        "domain": "Data Structures",
        "db_name": "data_structures.db",
    },
]


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def get_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def add_chunk(
    corpus: List[Dict[str, Any]],
    *,
    domain: str,
    source_db: str,
    concept_id: str,
    concept_name: str,
    section: str,
    text: str,
) -> None:
    text = safe_text(text)

    if not text:
        return

    corpus.append(
        {
            "domain": domain,
            "source_db": source_db,
            "concept_id": safe_text(concept_id),
            "concept_name": safe_text(concept_name),
            "section": section,
            "text": text,
        }
    )


def read_concepts(conn: sqlite3.Connection, domain: str, source_db: str) -> List[Dict[str, Any]]:
    if not table_exists(conn, "concepts"):
        return []

    cols = get_columns(conn, "concepts")
    rows = conn.execute("SELECT * FROM concepts").fetchall()

    concepts = []
    for row in rows:
        item = dict(zip(cols, row))

        concept_id = (
            item.get("concept_id")
            or item.get("id")
            or item.get("content_concept_id")
            or ""
        )

        concept_name = (
            item.get("concept_name")
            or item.get("topic")
            or item.get("title")
            or item.get("name")
            or str(concept_id)
        )

        concepts.append(
            {
                "domain": domain,
                "source_db": source_db,
                "concept_id": str(concept_id),
                "concept_name": str(concept_name),
                "raw": item,
            }
        )

    return concepts


def build_concept_name_lookup(concepts: List[Dict[str, Any]]) -> Dict[str, str]:
    lookup = {}

    for c in concepts:
        lookup[str(c["concept_id"])] = str(c["concept_name"])

    return lookup


def add_concept_chunks(
    corpus: List[Dict[str, Any]],
    concepts: List[Dict[str, Any]],
) -> None:
    useful_fields = [
        "topic",
        "concept_name",
        "title",
        "definition",
        "base_content",
        "content",
        "examples",
        "examples_base",
        "key_points",
        "key_points_base",
        "misconceptions",
        "misconceptions_base",
        "real_world_use",
        "syntax",
        "description",
    ]

    for concept in concepts:
        raw = concept["raw"]
        concept_id = concept["concept_id"]
        concept_name = concept["concept_name"]
        domain = concept["domain"]
        source_db = concept["source_db"]

        for field in useful_fields:
            if field in raw:
                add_chunk(
                    corpus,
                    domain=domain,
                    source_db=source_db,
                    concept_id=concept_id,
                    concept_name=concept_name,
                    section=f"concepts.{field}",
                    text=raw.get(field),
                )


def add_teaching_content_chunks(
    conn: sqlite3.Connection,
    corpus: List[Dict[str, Any]],
    *,
    domain: str,
    source_db: str,
    concept_lookup: Dict[str, str],
) -> None:
    if not table_exists(conn, "teaching_content"):
        return

    cols = get_columns(conn, "teaching_content")
    rows = conn.execute("SELECT * FROM teaching_content").fetchall()

    for row in rows:
        item = dict(zip(cols, row))

        concept_id = (
            item.get("concept_id")
            or item.get("content_concept_id")
            or item.get("system_concept_id")
            or ""
        )

        concept_name = (
            item.get("concept_name")
            or item.get("topic")
            or concept_lookup.get(str(concept_id))
            or str(concept_id)
        )

        strategy = item.get("strategy", "")
        difficulty = item.get("difficulty", "")
        content_type = item.get("content_type", "")

        section_parts = ["teaching_content"]
        if content_type:
            section_parts.append(str(content_type))
        if strategy:
            section_parts.append(str(strategy))
        if difficulty:
            section_parts.append(str(difficulty))

        section = ".".join(section_parts)

        text_fields = [
            "content",
            "body",
            "text",
            "base_content",
            "examples",
            "key_points",
            "misconceptions",
            "real_world_use",
        ]

        for field in text_fields:
            if field in item:
                add_chunk(
                    corpus,
                    domain=domain,
                    source_db=source_db,
                    concept_id=str(concept_id),
                    concept_name=str(concept_name),
                    section=f"{section}.{field}",
                    text=item.get(field),
                )


def add_dependency_chunks(
    conn: sqlite3.Connection,
    corpus: List[Dict[str, Any]],
    *,
    domain: str,
    source_db: str,
    concept_lookup: Dict[str, str],
) -> None:
    if not table_exists(conn, "concept_dependencies"):
        return

    cols = get_columns(conn, "concept_dependencies")
    rows = conn.execute("SELECT * FROM concept_dependencies").fetchall()

    for row in rows:
        item = dict(zip(cols, row))

        concept_id = (
            item.get("concept_id")
            or item.get("content_concept_id")
            or item.get("child_concept_id")
            or ""
        )

        prereq_id = (
            item.get("prerequisite_id")
            or item.get("prereq_concept_id")
            or item.get("parent_concept_id")
            or ""
        )

        concept_name = concept_lookup.get(str(concept_id), str(concept_id))
        prereq_name = concept_lookup.get(str(prereq_id), str(prereq_id))

        text = (
            f"{concept_name} depends on prerequisite concept {prereq_name}. "
            f"Learners should understand {prereq_name} before learning {concept_name}."
        )

        add_chunk(
            corpus,
            domain=domain,
            source_db=source_db,
            concept_id=str(concept_id),
            concept_name=str(concept_name),
            section="concept_dependencies",
            text=text,
        )


def build_corpus() -> List[Dict[str, Any]]:
    corpus: List[Dict[str, Any]] = []

    for subject in SUBJECT_DBS:
        domain = subject["domain"]
        db_name = subject["db_name"]
        db_path = CORE_DATA_DIR / db_name

        if not db_path.exists():
            print(f"[WARN] Missing DB: {db_path}")
            continue

        print(f"[READ] {domain}: {db_path}")

        conn = sqlite3.connect(db_path)

        concepts = read_concepts(conn, domain, db_name)
        concept_lookup = build_concept_name_lookup(concepts)

        add_concept_chunks(corpus, concepts)
        add_teaching_content_chunks(
            conn,
            corpus,
            domain=domain,
            source_db=db_name,
            concept_lookup=concept_lookup,
        )
        add_dependency_chunks(
            conn,
            corpus,
            domain=domain,
            source_db=db_name,
            concept_lookup=concept_lookup,
        )

        conn.close()

    return corpus


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    corpus = build_corpus()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print("\nRAG CORPUS BUILD COMPLETE")
    print("Output:", OUTPUT_PATH)
    print("Total chunks:", len(corpus))

    domain_counts = {}
    for item in corpus:
        domain = item["domain"]
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    print("\nChunks by domain:")
    for domain, count in sorted(domain_counts.items()):
        print(f"- {domain}: {count}")


if __name__ == "__main__":
    main()