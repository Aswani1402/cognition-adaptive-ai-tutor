from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

from tutor.system.orchestrator import run_orchestrator
from tutor.system.teaching_action_mapper import map_teaching_action
from tutor.utils.fetch_learning_content import get_learning_content


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_DATA_DIR = PROJECT_ROOT / "external" / "core_data"

SUBJECT_DB_MAP = {
    "P": CORE_DATA_DIR / "python_learning.db",
    "H": CORE_DATA_DIR / "html_web_basics.db",
    "S": CORE_DATA_DIR / "database_sql.db",
    "G": CORE_DATA_DIR / "git_version_control.db",
    "D": CORE_DATA_DIR / "data_structures.db",
}


class TeachingContentConnector:
    def get_subject_db_path(self, concept_id: str) -> Optional[Path]:
        if not concept_id:
            return None
        prefix = str(concept_id)[0].upper()
        return SUBJECT_DB_MAP.get(prefix)

    def get_content_concept_id(self, conn_core, system_concept_id: str) -> Optional[str]:
        row = conn_core.execute(
            """
            SELECT content_concept_id
            FROM concept_id_map
            WHERE system_concept_id = ?
            LIMIT 1
            """,
            (system_concept_id,),
        ).fetchone()

        if row:
            return row["content_concept_id"]

        return None

    def fetch_content(
        self,
        concept_id: str,
        strategy: str,
        content_type: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        """
        New content fetch path:
        system_concept_id -> concept_id_map -> subject DB -> concept_resources

        We intentionally use get_learning_content(system_concept_id),
        not content_concept_id, because that utility already performs:
        system id -> mapped content id -> domain -> subject DB -> concept_resources
        """

        print(f"[DEBUG] NEW fetch_content concept_id={concept_id}")

        try:
            resource = get_learning_content(str(concept_id))
            print(f"[DEBUG] concept_resources used = {bool(resource)}")
        except Exception as e:
            resource = None
            print(f"[DEBUG] concept_resources error = {e}")

        if resource:
            return {
                "found": True,
                "source": "concept_resources",
                "content": {
                    "concept_id": resource.get("concept_id"),
                    "topic": resource.get("topic"),
                    "strategy": strategy,
                    "content_type": content_type,
                    "difficulty": difficulty,
                    "content": resource.get("base_content"),
                    "base_content": resource.get("base_content"),
                    "examples": resource.get("examples"),
                    "key_points": resource.get("key_points"),
                    "misconceptions": resource.get("misconceptions"),
                    "real_world_use": resource.get("real_world_use"),
                    "next_concept_link": resource.get("next_concept_link"),
                },
            }

        return {
            "found": False,
            "reason": "concept_resources not found",
            "content": None,
        }

    def run(
        self,
        learner_id: str,
        concept_id: str,
    ) -> Dict[str, Any]:
        orchestrator_output = run_orchestrator(
            learner_id=learner_id,
            concept_id=concept_id,
        )

        teaching_action = map_teaching_action(orchestrator_output)

        core_db_path = CORE_DATA_DIR / "tutor.db"
        conn_core = sqlite3.connect(str(core_db_path))
        conn_core.row_factory = sqlite3.Row

        try:
            content_concept_id = self.get_content_concept_id(conn_core, concept_id)
        finally:
            conn_core.close()

        # IMPORTANT:
        # use system concept id here, not content_concept_id,
        # because get_learning_content() expects system_concept_id
        content_result = self.fetch_content(
            concept_id=concept_id,
            strategy=teaching_action["strategy"],
            content_type=teaching_action["content_type"],
            difficulty=teaching_action["difficulty"],
        )

        return {
            "learner_id": learner_id,
            "concept_id": concept_id,
            "content_concept_id": content_concept_id,
            "orchestrator": orchestrator_output,
            "teaching_action": teaching_action,
            "content_result": content_result,
        }


def run_teaching_content_connector(learner_id: str, concept_id: str) -> Dict[str, Any]:
    connector = TeachingContentConnector()
    return connector.run(learner_id=learner_id, concept_id=concept_id)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=True)
    args = parser.parse_args()

    output = run_teaching_content_connector(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id),
    )
    print(json.dumps(output, indent=2))