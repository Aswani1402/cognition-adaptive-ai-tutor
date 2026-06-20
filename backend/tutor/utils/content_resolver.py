import sqlite3
from typing import Optional, Dict, Any, List


def _fetch_concept_meta(concept_id: str, db_paths: List[str]) -> Optional[Dict[str, Any]]:
    for path in db_paths:
        conn = None
        try:
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            row = cur.execute(
                "SELECT concept_id, name, difficulty, description FROM concepts WHERE concept_id = ?",
                (concept_id,),
            ).fetchone()
            if row:
                return {
                    "concept_id": row[0],
                    "name": row[1],
                    "difficulty": row[2],
                    "description": row[3],
                    "source_db": path,
                }
        except Exception:
            pass
        finally:
            try:
                if conn:
                    conn.close()
            except Exception:
                pass
    return None


def find_concept_in_dbs(concept_id: str, db_paths: List[str]) -> Optional[Dict[str, Any]]:
    """
    1) Try direct lookup with concept_id (content id).
    2) If not found, try mapping from tutor.db: concept_id_map(system_concept_id -> content_concept_id)
    """
    # Try direct first
    direct = _fetch_concept_meta(concept_id, db_paths)
    if direct:
        direct["resolved_via"] = "direct"
        return direct

    # Try mapping via tutor.db
    tutor_db_path = sqlite3.connect  # placeholder for type hints


def find_concept_in_dbs_with_map(
    system_concept_id: str,
    tutor_db_path: str,
    db_paths: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Use system_concept_id like "37.0":
    - Look up mapped content_concept_id from tutor.db (concept_id_map)
    - Fetch concept metadata from content DBs using mapped id like "P4"
    """
    mapped_id = None
    conn = None
    try:
        conn = sqlite3.connect(tutor_db_path)
        row = conn.execute(
            "SELECT content_concept_id FROM concept_id_map WHERE system_concept_id = ? ORDER BY id DESC LIMIT 1",
            (system_concept_id,),
        ).fetchone()
        if row:
            mapped_id = row[0]
    except Exception:
        mapped_id = None
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass

    if not mapped_id:
        return None

    meta = _fetch_concept_meta(mapped_id, db_paths)
    if meta:
        meta["resolved_via"] = "map"
        meta["system_concept_id"] = system_concept_id
        meta["mapped_content_concept_id"] = mapped_id
        return meta

    return None

def build_teaching_content(
    concept_id: str,
    teaching_strategy: str,
    difficulty: str,
    db_paths: List[str],
    tutor_db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a simple content payload for the selected concept.
    Version 1: returns structured content, not LLM-generated text.
    """

    meta = find_concept_in_dbs(concept_id, db_paths)

    if meta is None and tutor_db_path:
        meta = find_concept_in_dbs_with_map(
            system_concept_id=concept_id,
            tutor_db_path=tutor_db_path,
            db_paths=db_paths,
        )

    if meta is None:
        meta = {
            "concept_id": concept_id,
            "name": f"Concept {concept_id}",
            "difficulty": difficulty,
            "description": f"No concept metadata found for concept_id={concept_id}",
            "source_db": None,
            "resolved_via": "fallback",
        }

    strategy_templates = {
        "definition": {
            "content_type": "definition",
            "instruction": f"Explain the basics of {meta['name']} clearly before asking the learner to solve anything."
        },
        "worked_example": {
            "content_type": "worked_example",
            "instruction": f"Show a step-by-step worked example for {meta['name']}."
        },
        "practice": {
            "content_type": "practice",
            "instruction": f"Give practice-oriented content for {meta['name']} at {difficulty} difficulty."
        },
        "revision": {
            "content_type": "revision",
            "instruction": f"Provide a quick revision summary of {meta['name']} and reinforce key points."
        },
    }

    strategy_info = strategy_templates.get(
        teaching_strategy,
        {
            "content_type": "generic_explanation",
            "instruction": f"Teach {meta['name']} in a clear way."
        }
    )

    return {
        "concept_id": concept_id,
        "concept_name": meta.get("name"),
        "teaching_strategy": teaching_strategy,
        "difficulty": difficulty,
        "content_type": strategy_info["content_type"],
        "instruction": strategy_info["instruction"],
        "description": meta.get("description"),
        "source_db": meta.get("source_db"),
        "resolved_via": meta.get("resolved_via"),
    }