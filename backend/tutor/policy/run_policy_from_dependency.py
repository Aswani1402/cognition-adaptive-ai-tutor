import sys
sys.path.append(".")
from typing import Dict, Optional
from tutor.concept_dependency.run_dependency_module_final import run_dependency_module_final


def choose_next_concept(result: Dict) -> Optional[str]:
    unlocked = result.get("unlocked_concepts", [])
    strategy_map = result.get("strategy_map", {})
    difficulty_map = result.get("difficulty_map", {})

    if not unlocked:
        return None


    remedial = [c for c in unlocked if strategy_map.get(c) == "remedial"]
    practice = [c for c in unlocked if strategy_map.get(c) == "practice"]
    advanced = [c for c in unlocked if strategy_map.get(c) == "advanced"]

    if remedial:
        pool = remedial
    elif practice:
        pool = practice
    elif advanced:
        pool = advanced
    else:
        pool = unlocked

    # choose easiest alphabetically for now
    return sorted(pool)[0]


def run_policy_once(tutor_db: str, concept_db_paths: list[str], learner_id: str):
    dep = run_dependency_module_final(
        tutor_db=tutor_db,
        concept_db_paths=concept_db_paths,
        learner_id=learner_id
    )

    next_concept = choose_next_concept(dep)

    if next_concept is None:
        return {
            "learner_id": learner_id,
            "next_concept_id": None,
            "difficulty": None,
            "strategy": None,
            "content_type": None,
            "decision_type": "no_unlocked_concepts",
        }

    return {
        "learner_id": learner_id,
        "next_concept_id": next_concept,
        "difficulty": dep["difficulty_map"].get(next_concept),
        "strategy": dep["strategy_map"].get(next_concept),
        "content_type": dep["content_type_map"].get(next_concept),
        "decision_type": "selected_from_dependency_module",
        "threshold": dep["threshold"],
        "space_used": dep["space_used"],
    }


if __name__ == "__main__":
    result = run_policy_once(
        tutor_db="external/core_data/tutor.db",
        concept_db_paths=[
            "external/core_data/python_learning.db",
            "external/core_data/database_sql.db",
            "external/core_data/html_web_basics.db",
            "external/core_data/git_version_control.db",
            "external/core_data/data_structures.db",
        ],
        learner_id="LNR-DEMO-SAMPLE"
    )

    print(result)
