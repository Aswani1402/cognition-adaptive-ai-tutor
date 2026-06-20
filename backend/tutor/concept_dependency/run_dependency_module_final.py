from __future__ import annotations

import json
import sqlite3
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Optional, Any


# =========================================================
# A) Load Concepts and Dependencies from Multiple DB Files
# =========================================================

def load_concepts_and_edges(db_paths: List[str]) -> Tuple[Dict[str, dict], List[dict]]:
    concepts: Dict[str, dict] = {}
    edges: List[dict] = []

    for db_path in db_paths:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT concept_id, name, difficulty, description FROM concepts"
        )

        for row in cursor.fetchall():
            concept_id = str(row[0])
            concepts[concept_id] = {
                "concept_id": concept_id,
                "name": row[1],
                "difficulty": row[2],
                "description": row[3],
            }

        try:
            cursor.execute(
                "SELECT concept_id, prerequisite_id, weight FROM concept_dependencies"
            )
        except Exception:
            cursor.execute(
                "SELECT concept_id, prerequisite_id, 1.0 as weight FROM concept_dependencies"
            )

        for row in cursor.fetchall():
            edges.append({
                "concept_id": str(row[0]),
                "prerequisite_id": str(row[1]),
                "weight": float(row[2]) if row[2] is not None else 1.0,
                "source_db": db_path,
            })

        conn.close()

    return concepts, edges


# =========================================================
# B) Build Graph + Cycle Detection
# =========================================================

def build_dependency_graph(concepts: Dict[str, dict], edges: List[dict]) -> dict:
    adjacency = defaultdict(list)
    reverse_adjacency = defaultdict(list)
    valid_edges = []

    for edge in edges:
        prereq = edge["prerequisite_id"]
        concept = edge["concept_id"]

        if prereq in concepts and concept in concepts:
            adjacency[prereq].append(concept)
            reverse_adjacency[concept].append(prereq)
            valid_edges.append(edge)

    concept_ids = sorted(concepts.keys())
    concept_index = {cid: i for i, cid in enumerate(concept_ids)}
    index_concept = concept_ids.copy()

    n = len(concept_ids)
    matrix = [[0.0 for _ in range(n)] for _ in range(n)]

    for edge in valid_edges:
        i = concept_index[edge["prerequisite_id"]]
        j = concept_index[edge["concept_id"]]
        matrix[i][j] = edge["weight"]

    visited: Dict[str, int] = {}
    stack: List[str] = []
    cycles: List[List[str]] = []
    is_dag = True

    def dfs(node: str) -> None:
        nonlocal is_dag
        visited[node] = 1
        stack.append(node)

        for neighbor in adjacency[node]:
            state = visited.get(neighbor, 0)

            if state == 0:
                dfs(neighbor)
            elif state == 1:
                is_dag = False
                cycle_start = stack.index(neighbor)
                cycles.append(stack[cycle_start:] + [neighbor])

        stack.pop()
        visited[node] = 2

    for cid in concept_ids:
        if visited.get(cid, 0) == 0:
            dfs(cid)

    topo_order: List[str] = []

    if is_dag:
        in_degree = {cid: 0 for cid in concept_ids}
        for parent in adjacency:
            for child in adjacency[parent]:
                in_degree[child] += 1

        queue = deque([cid for cid in concept_ids if in_degree[cid] == 0])

        while queue:
            node = queue.popleft()
            topo_order.append(node)

            for neighbor in adjacency[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    return {
        "concept_index": concept_index,
        "index_concept": index_concept,
        "concepts": concepts,
        "edges": valid_edges,
        "adjacency": dict(adjacency),
        "reverse_adjacency": dict(reverse_adjacency),
        "matrix": matrix,
        "is_dag": is_dag,
        "topological_order": topo_order,
        "cycles": cycles,
    }


# =========================================================
# C) Threshold + Unlock / Blocked
# =========================================================

def compute_prereq_threshold(
    mastery: Dict[str, float],
    default_threshold: float = 0.6,
) -> float:
    if not mastery:
        return default_threshold

    vals = [float(v) for v in mastery.values()]
    avg_mastery = sum(vals) / len(vals)

    if avg_mastery < 0.30:
        return 0.50
    if avg_mastery < 0.60:
        return 0.60
    return 0.70


def compute_unlocked_and_blocked(
    concepts: Dict[str, dict],
    reverse_adjacency: dict,
    mastery: Dict[str, float],
    threshold: Optional[float] = None,
) -> dict:
    mastery = {str(k): float(v) for k, v in mastery.items()}
    adaptive_threshold = (
        compute_prereq_threshold(mastery)
        if threshold is None
        else float(threshold)
    )

    unlocked: List[str] = []
    blocked: List[dict] = []

    # use all concepts from graph, not only those already in mastery
    for concept in sorted(concepts.keys()):
        prereqs = reverse_adjacency.get(concept, [])

        if not prereqs:
            unlocked.append(concept)
            continue

        failed = []
        prereq_mastery = {}

        for prereq in prereqs:
            m = float(mastery.get(prereq, 0.0))
            prereq_mastery[prereq] = m
            if m < adaptive_threshold:
                failed.append(prereq)

        if not failed:
            unlocked.append(concept)
        else:
            blocked.append({
                "concept_id": concept,
                "blocked_by": failed,
                "prereq_mastery": prereq_mastery,
                "threshold": adaptive_threshold,
            })

    return {
        "unlocked": unlocked,
        "blocked": blocked,
        "threshold_used": adaptive_threshold,
    }


# =========================================================
# D) Metadata mapping for teaching layer
# =========================================================

def build_teaching_maps(
    concepts: Dict[str, dict],
    content_to_system: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    difficulty_map: Dict[str, str] = {}
    strategy_map: Dict[str, str] = {}
    content_type_map: Dict[str, str] = {}

    for content_id, meta in concepts.items():
        if content_id not in content_to_system:
            continue

        system_id = content_to_system[content_id]
        diff = str(meta.get("difficulty", "medium") or "medium").strip().lower()

        if diff == "easy":
            difficulty_map[system_id] = "easy"
            strategy_map[system_id] = "remedial"
            content_type_map[system_id] = "worked_example"
        elif diff == "medium":
            difficulty_map[system_id] = "medium"
            strategy_map[system_id] = "practice"
            content_type_map[system_id] = "guided_practice"
        else:
            difficulty_map[system_id] = "hard"
            strategy_map[system_id] = "advanced"
            content_type_map[system_id] = "challenge_problem"

    return difficulty_map, strategy_map, content_type_map


# =========================================================
# E) Adaptive next concept selection
# =========================================================

def choose_next_concept(
    unlocked_system: List[str],
    mastery_system: Dict[str, float],
    current_concept_id: Optional[str] = None,
) -> Optional[str]:
    if not unlocked_system:
        return None

    # remove current concept if possible when selecting "next"
    candidates = [cid for cid in unlocked_system if cid != str(current_concept_id)]
    if not candidates:
        candidates = unlocked_system[:]

    # prefer lowest-mastery unlocked concept that is still available
    candidates_sorted = sorted(
        candidates,
        key=lambda cid: float(mastery_system.get(str(cid), 0.0))
    )
    return candidates_sorted[0] if candidates_sorted else None


# =========================================================
# F) Entry function for current tutor system
# =========================================================

def run_dependency_module_final(
    tutor_db: str,
    concept_db_paths: List[str],
    learner_id: str,
    current_concept_id: Optional[str] = None,
    attach_learned_path_ranker_output: bool = False,
) -> Dict[str, Any]:
    conn = sqlite3.connect(tutor_db)
    cursor = conn.cursor()

    # knowledge_state schema handling
    state_json = None
    for learner_col in ("student_id", "learner_id"):
        try:
            cursor.execute(
                f"""
                SELECT state_json
                FROM knowledge_state
                WHERE {learner_col} = ?
                LIMIT 1
                """,
                (learner_id,),
            )
            row = cursor.fetchone()
            if row and row[0]:
                state_json = row[0]
                break
        except Exception:
            continue

    try:
        cursor.execute(
            """
            SELECT system_concept_id, content_concept_id
            FROM concept_id_map
            """
        )
        map_rows = cursor.fetchall()
    finally:
        conn.close()

    if not state_json:
        return {
            "status": "no_mastery_data",
            "learner_id": str(learner_id),
            "current_concept_id": str(current_concept_id) if current_concept_id else None,
            "recommended_next_concept": None,
            "unlocked_concepts": [],
            "blocked_concepts": [],
            "difficulty_map": {},
            "strategy_map": {},
            "content_type_map": {},
            "threshold": 0.6,
            "space_used": "system",
        }

    try:
        state = json.loads(state_json)
    except Exception:
        return {
            "status": "error",
            "learner_id": str(learner_id),
            "current_concept_id": str(current_concept_id) if current_concept_id else None,
            "reason": "invalid state_json",
            "recommended_next_concept": None,
            "unlocked_concepts": [],
            "blocked_concepts": [],
            "difficulty_map": {},
            "strategy_map": {},
            "content_type_map": {},
            "threshold": 0.6,
            "space_used": "system",
        }

    system_to_content = {str(s): str(c) for s, c in map_rows}
    content_to_system = {str(c): str(s) for s, c in map_rows}

    mastery_system = {}
    if (
        isinstance(state, dict)
        and state.get("schema_version") == "kt_v2"
        and isinstance(state.get("concepts"), dict)
    ):
        state_items = {
            concept_id: concept_state.get("mastery")
            for concept_id, concept_state in state["concepts"].items()
            if isinstance(concept_state, dict)
        }.items()
    else:
        state_items = state.items()

    for k, v in state_items:
        try:
            mastery_system[str(k)] = float(v)
        except Exception:
            continue

    mastery_content = {
        system_to_content[k]: float(v)
        for k, v in mastery_system.items()
        if k in system_to_content
    }

    threshold = compute_prereq_threshold(mastery_content)

    concepts, edges = load_concepts_and_edges(concept_db_paths)
    graph = build_dependency_graph(concepts, edges)

    unlock_result = compute_unlocked_and_blocked(
        concepts=graph["concepts"],
        reverse_adjacency=graph["reverse_adjacency"],
        mastery=mastery_content,
        threshold=threshold,
    )

    unlocked_content = unlock_result["unlocked"]
    blocked_content = unlock_result["blocked"]

    unlocked_system = [
        content_to_system[cid]
        for cid in unlocked_content
        if cid in content_to_system
    ]

    blocked_system = []
    for item in blocked_content:
        content_id = item["concept_id"]
        if content_id not in content_to_system:
            continue

        blocked_by_system = [
            content_to_system[p]
            for p in item.get("blocked_by", [])
            if p in content_to_system
        ]

        prereq_mastery_system = {
            content_to_system[p]: m
            for p, m in item.get("prereq_mastery", {}).items()
            if p in content_to_system
        }

        blocked_system.append({
            "concept_id": content_to_system[content_id],
            "blocked_by": blocked_by_system,
            "prereq_mastery": prereq_mastery_system,
            "threshold": item.get("threshold", threshold),
        })

    difficulty_map, strategy_map, content_type_map = build_teaching_maps(
        concepts=concepts,
        content_to_system=content_to_system,
    )

    recommended_next_concept = choose_next_concept(
        unlocked_system=unlocked_system,
        mastery_system=mastery_system,
        current_concept_id=current_concept_id,
    )

    out: Dict[str, Any] = {
        "status": "success",
        "learner_id": str(learner_id),
        "current_concept_id": str(current_concept_id) if current_concept_id else None,
        "recommended_next_concept": recommended_next_concept,
        "unlocked_concepts": unlocked_system,
        "blocked_concepts": blocked_system,
        "mastery_used": mastery_system,
        "difficulty_map": difficulty_map,
        "strategy_map": strategy_map,
        "content_type_map": content_type_map,
        "threshold": threshold,
        "graph_is_dag": graph["is_dag"],
        "topological_order_sample": graph["topological_order"][:10],
        "space_used": "system",
    }

    if attach_learned_path_ranker_output:
        try:
            from tutor.concept_dependency.learned_adaptive_path_ranker import LearnedAdaptivePathRanker

            mast_vals = [float(v) for v in mastery_system.values()] if mastery_system else []
            cur_m = float(mast_vals[0]) if mast_vals else 0.5
            prereq_m = float(sum(mast_vals) / len(mast_vals)) if mast_vals else cur_m
            evidence = {
                "current_mastery": cur_m,
                "prerequisite_mastery": prereq_m,
                "behaviour_risk": 0.35,
                "behaviour_confidence": 0.65,
                "fused_score": 0.5,
                "recent_score": 0.5,
                "wrong_streak": 0.0,
                "review_due": 0.25,
                "time_gap_days": 2.0,
                "attempts_on_concept": 2.0,
                "hint_usage": 0.0,
                "mistake_count": 0.0,
                "weak_concept_flag": cur_m < 0.45,
                "concept_unlock_status": "unlocked",
                "difficulty": "medium",
                "reward_xp": 0.0,
                "anomaly_score": 0.2,
                "path_position": 0.5,
                "review_queue_concept_ids": [],
            }
            rnk = LearnedAdaptivePathRanker()
            rnk.load()
            cur = str(current_concept_id) if current_concept_id else str(recommended_next_concept or "")
            out["learned_path_ranker_output"] = rnk.predict_with_fallback(
                str(learner_id),
                cur,
                out,
                evidence,
                None,
            )
        except Exception as ex:
            out["learned_path_ranker_output"] = {
                "status": "warning",
                "module": "LearnedAdaptivePathRanker",
                "model_used": False,
                "fallback_used": True,
                "limitations": [str(ex)],
            }

    return out


if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser()
    parser.add_argument("--tutor_db", required=True)
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--current_concept_id", required=False, default=None)
    parser.add_argument("--concept_dbs", nargs="+", required=True)
    args = parser.parse_args()

    result = run_dependency_module_final(
        tutor_db=args.tutor_db,
        concept_db_paths=args.concept_dbs,
        learner_id=str(args.learner_id),
        current_concept_id=str(args.current_concept_id) if args.current_concept_id else None,
    )
    print(_json.dumps(result, indent=2))
