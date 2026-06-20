import sqlite3
from collections import defaultdict
from typing import Dict, List


# =========================================================
# 1. LOAD MAPPING
# =========================================================
def load_mapping(tutor_db: str):

    conn = sqlite3.connect(tutor_db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT system_concept_id, content_concept_id
        FROM concept_id_map
    """)

    content_to_system = {}

    for sys_id, content_id in cursor.fetchall():
        content_to_system[str(content_id)] = str(sys_id)

    conn.close()
    return content_to_system


# =========================================================
# 2. LOAD GRAPH (SYSTEM SPACE)
# =========================================================
def load_graph(db_paths: List[str], content_to_system: Dict[str, str]):

    concepts = set()
    reverse_adj = defaultdict(list)

    for db_path in db_paths:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Concepts
        cursor.execute("SELECT concept_id FROM concepts")
        for (cid,) in cursor.fetchall():
            if cid in content_to_system:
                concepts.add(content_to_system[cid])

        # Dependencies
        try:
            cursor.execute("""
                SELECT concept_id, prerequisite_id
                FROM concept_dependencies
            """)

            for concept, prereq in cursor.fetchall():
                if concept in content_to_system and prereq in content_to_system:
                    c_sys = content_to_system[concept]
                    p_sys = content_to_system[prereq]
                    reverse_adj[c_sys].append(p_sys)

        except:
            pass

        conn.close()

    return concepts, reverse_adj


# =========================================================
# 3. LOAD MASTERY
# =========================================================
def load_mastery(tutor_db: str, learner_id: str, content_to_system: Dict[str, str]):

    conn = sqlite3.connect(tutor_db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT state_json
        FROM knowledge_state
        WHERE student_id = ?
        ORDER BY updated_at DESC
        LIMIT 1
    """, (learner_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {}

    import json
    try:
        data = json.loads(row[0])   # your format: { "P1": 0.8 }
    except:
        return {}

    mastery = {}

    for cid, val in data.items():
        if cid in content_to_system:
            mastery[content_to_system[cid]] = float(val)

    return mastery


# =========================================================
# 4. LOAD BEHAVIOUR
# =========================================================
def load_behavior(tutor_db: str, learner_id: str):

    conn = sqlite3.connect(tutor_db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT behavior_score, behavior_label
        FROM behaviour_state
        WHERE learner_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (learner_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"behavior_score": 0.0, "label": "normal"}

    return {
        "behavior_score": float(row[0]),
        "label": row[1]
    }


# =========================================================
# 5. THRESHOLD (ONLY MASTERY BASED)
# =========================================================
def get_threshold(mastery: Dict[str, float]):

    if not mastery:
        return 0.6

    avg = sum(mastery.values()) / len(mastery)

    if avg < 0.3:
        return 0.5
    elif avg < 0.6:
        return 0.6
    else:
        return 0.7


# =========================================================
# 6. UNLOCK / BLOCK (NO BEHAVIOUR HERE)
# =========================================================
def compute_unlocked_blocked(concepts, reverse_adj, mastery):

    threshold = get_threshold(mastery)

    unlocked = []
    blocked = []

    for cid in concepts:

        prereqs = reverse_adj.get(cid, [])

        if not prereqs:
            unlocked.append(cid)
            continue

        failed = []
        prereq_mastery = {}

        for p in prereqs:
            m = mastery.get(p, 0.0)
            prereq_mastery[p] = m

            if m < threshold:
                failed.append(p)

        if not failed:
            unlocked.append(cid)
        else:
            blocked.append({
                "concept_id": cid,
                "blocked_by": failed,
                "prereq_mastery": prereq_mastery,
                "threshold": threshold
            })

    return unlocked, blocked, threshold


# =========================================================
# 7. DIFFICULTY DECISION (BEHAVIOUR USED HERE)
# =========================================================
def decide_difficulty(mastery_value: float, behavior: Dict):

    # Base difficulty from mastery
    if mastery_value < 0.6:
        difficulty = "easy"
    elif mastery_value < 0.8:
        difficulty = "medium"
    else:
        difficulty = "hard"

    # Behaviour adjustment 
    behavior_score = behavior.get("behavior_score", 0)

    if behavior_score >= 0.7:
        # reduce difficulty
        if difficulty == "hard":
            difficulty = "medium"
        elif difficulty == "medium":
            difficulty = "easy"

    return difficulty


# =========================================================
# 8. MAIN PIPELINE
# =========================================================
def run_dependency_module(tutor_db, db_paths, learner_id):

    content_to_system = load_mapping(tutor_db)

    concepts, reverse_adj = load_graph(db_paths, content_to_system)

    mastery = load_mastery(tutor_db, learner_id, content_to_system)

    behavior = load_behavior(tutor_db, learner_id)

    unlocked, blocked, threshold = compute_unlocked_blocked(
        concepts, reverse_adj, mastery
    )

    # Difficulty for unlocked concepts
    difficulty_map = {}

    # 🔥 NEW: strategy + content maps
    strategy_map = {}
    content_type_map = {}

    for cid in unlocked:
        mastery_value = mastery.get(cid, 0.0)

        # existing
        difficulty_map[cid] = decide_difficulty(mastery_value, behavior)

        # 🔥 NEW: strategy_type
        if mastery_value < 0.4:
            strategy = "remedial"
        elif mastery_value < 0.7:
            strategy = "practice"
        else:
            strategy = "advanced"

        # behaviour override
        # if behavior.get("behavior_score", 0) >= 0.7:
        #     strategy = "support"

        strategy_map[cid] = strategy

        # 🔥 NEW: content_type
        if strategy in ["remedial", "support"]:
            content_type = "worked_example"
        elif strategy == "practice":
            content_type = "guided_practice"
        else:
            content_type = "challenge_problem"

        content_type_map[cid] = content_type

    return {
        "unlocked_concepts": unlocked,
        "blocked_concepts": blocked,
        "threshold": threshold,
        "behavior": behavior,
        "difficulty_map": difficulty_map,
        "strategy_map": strategy_map,            # ✅ NEW
        "content_type_map": content_type_map     # ✅ NEW
    }


# =========================================================
# 9. TEST
# =========================================================
if __name__ == "__main__":

    result = run_dependency_module(
        tutor_db="Updated_DB/tutor.db",
        db_paths=[
            "Updated_DB/python_learning.db",
            "Updated_DB/database_sql.db",
            "Updated_DB/html_web_basics.db",
            "Updated_DB/git_version_control.db",
            "Updated_DB/data_structures.db",
        ],
        learner_id="14"
    )

    print("\nUnlocked:", result["unlocked_concepts"])
    print("\nBlocked:", result["blocked_concepts"])
    print("\nDifficulty:", result["difficulty_map"])
    print("\nBehavior:", result["behavior"])