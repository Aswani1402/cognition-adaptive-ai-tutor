import ast
import re
import sqlite3
from typing import Any, Dict, List, Optional

from src.cognitutor_lm_config import SUBJECT_DBS


BROKEN_ENDING_PATTERNS = [
    r"\bth\.$",
    r"\bst\.$",
    r"\bbecom\.$",
    r"\belemen\.$",
    r"\bComp\.$",
]


def clean_text(value: Any, max_chars: Optional[int] = None) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("...", "implementation omitted")
    text = text.replace("N/A", "not available")
    text = text.replace("TODO", "future task")
    text = text.replace("placeholder", "input hint")
    text = text.replace("['", "").replace("']", "").replace('["', "").replace('"]', "")
    for pattern in BROKEN_ENDING_PATTERNS:
        text = re.sub(pattern, "", text).strip(" ,.;:")
    if max_chars and len(text) > max_chars:
        cut = text[:max_chars]
        boundary = max(cut.rfind("."), cut.rfind("\n"), cut.rfind(" "))
        if boundary > int(max_chars * 0.65):
            text = cut[:boundary].strip(" ,;:")
        else:
            text = cut.strip(" ,;:")
    return text


def clean_list(value: Any, max_items: int = 10) -> List[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        raw_items = []
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, list):
                    raw_items = parsed
            except (SyntaxError, ValueError):
                raw_items = []
        if not raw_items:
            raw_items = []
            for line in text.splitlines():
                line = line.strip().lstrip("-* ").strip()
                if not line:
                    continue
                if "|" in line:
                    raw_items.extend(part.strip() for part in line.split("|") if part.strip())
                else:
                    raw_items.append(line)
            if len(raw_items) <= 1 and ". " in text:
                raw_items = [part.strip() + "." for part in text.split(". ") if part.strip()]
    cleaned: List[str] = []
    for item in raw_items:
        text = clean_text(item)
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:max_items]


def _column(row: sqlite3.Row, *names: str) -> Any:
    keys = set(row.keys())
    for name in names:
        if name in keys:
            return row[name]
    return ""


def load_concept_resources() -> List[Dict[str, Any]]:
    concepts: List[Dict[str, Any]] = []
    for domain, db_path in SUBJECT_DBS.items():
        if not db_path.exists():
            continue
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM concept_resources ORDER BY concept_id").fetchall()
        conn.close()
        for row in rows:
            base = clean_text(_column(row, "base_content", "definition"), 4000)
            concepts.append(
                {
                    "domain": domain,
                    "concept_id": clean_text(_column(row, "concept_id"), 80),
                    "concept_name": clean_text(_column(row, "topic", "concept_name"), 160),
                    "topic": clean_text(_column(row, "topic", "concept_name"), 160),
                    "base_content": base,
                    "definition": base,
                    "examples": clean_list(_column(row, "examples"), 12),
                    "key_points": clean_list(_column(row, "key_points"), 12),
                    "misconceptions": clean_list(_column(row, "misconceptions"), 12),
                    "real_world_use": clean_text(_column(row, "real_world_use"), 1600),
                    "next_concept_link": clean_text(_column(row, "next_concept_link"), 800),
                }
            )
    return concepts


def load_all_concepts_by_domain() -> Dict[str, Dict[str, Dict[str, Any]]]:
    all_concepts: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for concept in load_concept_resources():
        all_concepts.setdefault(concept["domain"], {})[concept["concept_id"]] = concept
    return all_concepts


def print_concept_summary(concepts: Optional[List[Dict[str, Any]]] = None) -> None:
    concepts = concepts or load_concept_resources()
    print("Domain | concept_id | concept_name | has_definition | has_examples | has_key_points | has_misconceptions | has_real_world_use")
    for c in concepts:
        print(
            f"{c['domain']} | {c['concept_id']} | {c['concept_name']} | "
            f"{bool(c.get('definition'))} | {bool(c.get('examples'))} | "
            f"{bool(c.get('key_points'))} | {bool(c.get('misconceptions'))} | {bool(c.get('real_world_use'))}"
        )


def find_concept(domain: str, concept: Optional[str] = None, concept_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    nd = clean_text(domain).lower()
    nc = clean_text(concept).lower() if concept else None
    ni = clean_text(concept_id).lower() if concept_id else None
    aliases = {
        ("sql", "join"): "join operations",
        ("html", "forms"): "forms and inputs",
        ("git", "branching"): "branches",
        ("git", "branch"): "branches",
    }
    if nc:
        nc = aliases.get((nd, nc), nc)
    for row in load_concept_resources():
        if row["domain"].lower() != nd:
            continue
        if ni and row["concept_id"].lower() == ni:
            return row
        if nc and (nc == row["concept_name"].lower() or nc in row["concept_name"].lower() or nc == row["concept_id"].lower()):
            return row
    return None


def safe_name(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", str(value)).strip("_")
