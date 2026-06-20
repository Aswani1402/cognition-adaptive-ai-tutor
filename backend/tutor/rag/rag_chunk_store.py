from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


CORE_DATA_DIR = Path("external/core_data")

SUBJECT_DBS = {
    "Python": "python_learning.db",
    "SQL": "database_sql.db",
    "HTML": "html_web_basics.db",
    "Git": "git_version_control.db",
    "Data Structures": "data_structures.db",
}


class RAGChunkStore:
    """
    Correct chunk loader using concept_resources (REAL CONTENT)
    """

    def __init__(self, core_data_dir: Path = CORE_DATA_DIR) -> None:
        self.core_data_dir = core_data_dir

    def load_all_chunks(self) -> List[Dict[str, Any]]:
        all_chunks: List[Dict[str, Any]] = []

        for domain, db_name in SUBJECT_DBS.items():
            db_path = self.core_data_dir / db_name

            if not db_path.exists():
                continue

            chunks = self._load_from_concept_resources(domain, db_path)
            all_chunks.extend(chunks)

        return all_chunks

    def _load_from_concept_resources(
        self,
        domain: str,
        db_path: Path,
    ) -> List[Dict[str, Any]]:

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute(
            "SELECT * FROM concept_resources"
        ).fetchall()

        chunks: List[Dict[str, Any]] = []

        for row in rows:
            data = dict(row)

            concept_id = str(data.get("concept_id", ""))
            topic = data.get("topic", concept_id)

            # Core sections from your DB
            sections = {
                "definition": data.get("base_content"),
                "examples": data.get("examples"),
                "key_points": data.get("key_points"),
                "misconceptions": data.get("misconceptions"),
                "real_world_use": data.get("real_world_use"),
                "next_concept": data.get("next_concept_link"),
            }

            for section_name, content in sections.items():
                if content:
                    chunks.append({
                        "chunk_id": f"{domain}:{concept_id}:{section_name}",
                        "domain": domain,
                        "content_concept_id": concept_id,
                        "topic": topic,
                        "section": section_name,
                        "content": str(content),
                        "source_db": db_path.name,
                    })

        conn.close()
        return chunks


if __name__ == "__main__":
    store = RAGChunkStore()
    chunks = store.load_all_chunks()

    print("TOTAL_CHUNKS:", len(chunks))

    for c in chunks[:5]:
        print("-" * 60)
        print("chunk_id:", c["chunk_id"])
        print("domain:", c["domain"])
        print("topic:", c["topic"])
        print("section:", c["section"])
        print("preview:", c["content"][:200])