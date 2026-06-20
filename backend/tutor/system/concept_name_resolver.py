import sqlite3
from pathlib import Path
from typing import Optional, Dict, List


DEFAULT_TUTOR_DB = Path("external/core_data/tutor.db")

DEFAULT_CONCEPT_DB_PATHS = [
    Path("external/core_data/python_learning.db"),
    Path("external/core_data/database_sql.db"),
    Path("external/core_data/html_web_basics.db"),
    Path("external/core_data/git_version_control.db"),
    Path("external/core_data/data_structures.db"),
]


FALLBACK_CONCEPT_NAMES: Dict[str, str] = {
    # Python numeric/system ids
    "1": "Variables",
    "2": "Data Types",
    "3": "Conditionals",
    "4": "Loops",
    "5": "Functions",
    "6": "OOP",
    "7": "Decorators & Generators",
    "8": "File Handling & I/O",

    # Python content ids
    "P1": "Variables",
    "P2": "Data Types",
    "P3": "Conditionals",
    "P4": "Loops",
    "P5": "Functions",
    "P6": "OOP",
    "P7": "Decorators & Generators",
    "P8": "File Handling & I/O",

    # SQL
    "S1": "Database Basics",
    "S2": "SELECT",
    "S3": "WHERE / Filters",
    "S4": "JOINs",
    "S5": "Indexes",
    "S6": "Window Functions",
    "S7": "Common Table Expressions",

    # HTML
    "H1": "What is HTML",
    "H2": "Tags & Elements",
    "H3": "Attributes & Links",
    "H4": "Images & Lists",
    "H5": "Forms & Inputs",
    "H6": "Accessibility",
    "H7": "Service Workers",
    "H8": "Web Components",

    # Git
    "G1": "Version Control",
    "G2": "Repositories",
    "G3": "Commits & History",
    "G4": "Branches",
    "G5": "Merge & Conflict Basics",
    "G6": "Interactive Rebase",
    "G7": "Submodules",

    # Data structures
    "D1": "Arrays",
    "D2": "Linked Lists",
    "D3": "Stacks",
    "D4": "Queues",
    "D5": "Trees",
    "D6": "Sets",
    "D7": "Graphs",
}


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name=?
        """,
        (table_name,),
    )
    return cur.fetchone() is not None


def _columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cur.fetchall()]


def _lookup_from_concept_id_map(
    concept_id: str,
    tutor_db: Path = DEFAULT_TUTOR_DB,
) -> Optional[str]:
    if not tutor_db.exists():
        return None

    try:
        conn = sqlite3.connect(tutor_db)

        if not _table_exists(conn, "concept_id_map"):
            conn.close()
            return None

        cols = _columns(conn, "concept_id_map")

        possible_id_cols = [
            "system_concept_id",
            "concept_id",
            "content_concept_id",
        ]

        possible_name_cols = [
            "concept_name",
            "topic",
            "name",
        ]

        id_cols = [col for col in possible_id_cols if col in cols]
        name_col = next((col for col in possible_name_cols if col in cols), None)

        if not id_cols or not name_col:
            conn.close()
            return None

        cur = conn.cursor()

        for id_col in id_cols:
            cur.execute(
                f"""
                SELECT {name_col}
                FROM concept_id_map
                WHERE CAST({id_col} AS TEXT) = ?
                LIMIT 1
                """,
                (str(concept_id),),
            )
            row = cur.fetchone()

            if row and row[0]:
                conn.close()
                return str(row[0])

        conn.close()
        return None

    except Exception:
        return None


def _lookup_from_subject_db(
    concept_id: str,
    db_path: Path,
) -> Optional[str]:
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Preferred new content table
        if _table_exists(conn, "concept_resources"):
            cols = _columns(conn, "concept_resources")

            id_col = "concept_id" if "concept_id" in cols else None
            name_col = "topic" if "topic" in cols else None

            if id_col and name_col:
                cur.execute(
                    f"""
                    SELECT {name_col}
                    FROM concept_resources
                    WHERE CAST({id_col} AS TEXT) = ?
                    LIMIT 1
                    """,
                    (str(concept_id),),
                )
                row = cur.fetchone()

                if row and row[0]:
                    conn.close()
                    return str(row[0])

        # Older possible concept table
        if _table_exists(conn, "concepts"):
            cols = _columns(conn, "concepts")

            id_col = "concept_id" if "concept_id" in cols else "id" if "id" in cols else None
            name_col = "concept_name" if "concept_name" in cols else "topic" if "topic" in cols else "name" if "name" in cols else None

            if id_col and name_col:
                cur.execute(
                    f"""
                    SELECT {name_col}
                    FROM concepts
                    WHERE CAST({id_col} AS TEXT) = ?
                    LIMIT 1
                    """,
                    (str(concept_id),),
                )
                row = cur.fetchone()

                if row and row[0]:
                    conn.close()
                    return str(row[0])

        conn.close()
        return None

    except Exception:
        return None


def resolve_concept_name(
    concept_id: str,
    tutor_db: Path = DEFAULT_TUTOR_DB,
    concept_db_paths: Optional[List[Path]] = None,
    fallback_name: str = "Unknown Concept",
) -> str:
    concept_id = str(concept_id)

    if not concept_id or concept_id.lower() in {"none", "null"}:
        return fallback_name

    # 1. direct fallback map
    if concept_id in FALLBACK_CONCEPT_NAMES:
        return FALLBACK_CONCEPT_NAMES[concept_id]

    # 2. concept_id_map table in tutor.db
    mapped_name = _lookup_from_concept_id_map(concept_id, tutor_db=tutor_db)
    if mapped_name:
        return mapped_name

    # 3. subject DBs
    paths = concept_db_paths or DEFAULT_CONCEPT_DB_PATHS

    for db_path in paths:
        subject_name = _lookup_from_subject_db(concept_id, Path(db_path))
        if subject_name:
            return subject_name

    # 4. final fallback
    return fallback_name


def resolve_concept_identity(
    concept_id: str,
    tutor_db: Path = DEFAULT_TUTOR_DB,
    concept_db_paths: Optional[List[Path]] = None,
) -> Dict[str, str]:
    name = resolve_concept_name(
        concept_id=concept_id,
        tutor_db=tutor_db,
        concept_db_paths=concept_db_paths,
    )

    return {
        "concept_id": str(concept_id),
        "concept_name": name,
    }


if __name__ == "__main__":
    for cid in ["1", "2", "3", "P1", "S2", "H1", "G1", "D1", "999"]:
        print(resolve_concept_identity(cid))