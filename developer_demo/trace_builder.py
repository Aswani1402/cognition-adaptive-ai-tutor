import pandas as pd

from config import FALLBACK_PATHS, SUBJECT_DBS
from data_access import latest_row, parse_json, rows_for_learner, subject_resource, tables, read_table
from module_explainers import behaviour_from_quiz, safe_policy, teaching_strategy


def latest_interaction(learner_id):
    q = latest_row("quiz_results", learner_id)
    if not q:
        return {}
    concept_id = q.get("concept_id")
    mistake = latest_row("learner_mistake_log", learner_id)
    eval_log = latest_row("evaluation_log", learner_id)
    policy = latest_row("policy_decision_log", learner_id)
    strategy = latest_row("teaching_strategy_training_log", learner_id)
    xai = latest_row("xai_log", learner_id)
    return {"quiz": q, "mistake": mistake, "evaluation": eval_log, "policy": policy, "strategy": strategy, "xai": xai, "concept_id": concept_id}


def learner_mastery(learner_id):
    ks = latest_row("knowledge_state", learner_id)
    state = parse_json(ks.get("state_json")) if ks else {}
    progress = rows_for_learner("learner_concept_progress", learner_id, 500)
    if not progress.empty:
        vals = pd.to_numeric(progress.get("mastery"), errors="coerce").dropna()
        overall = float(vals.mean()) if not vals.empty else None
    else:
        overall = None
    return {"knowledge_state": ks, "state_json": state, "progress": progress, "overall": overall}


def build_trace(learner_id, subject, concept):
    interaction = latest_interaction(learner_id)
    quiz = interaction.get("quiz", {})
    mastery = learner_mastery(learner_id)
    b = latest_row("behaviour_state", learner_id)
    behaviour = b.get("behavior_label") or behaviour_from_quiz(quiz).get("state")
    score = quiz.get("is_correct")
    if score is not None:
        score = 1.0 if int(score) else 0.0
    if interaction.get("evaluation", {}).get("overall_score") is not None:
        score = interaction["evaluation"].get("overall_score")
    ts = teaching_strategy(mastery["overall"], behaviour, interaction.get("mistake", {}).get("mistake_type"), quiz.get("difficulty"))
    policy = safe_policy(score, mastery["overall"], behaviour)
    resource = subject_resource(subject, concept)
    final_source = "RAG/concept resource fallback"
    generation = latest_row("generation_history", learner_id)
    if generation:
        final_source = generation.get("item_type") or "generation_history"
    return {
        "interaction": interaction,
        "quiz": quiz,
        "mastery": mastery,
        "behaviour": b or behaviour_from_quiz(quiz),
        "teaching": ts,
        "policy": policy,
        "resource": resource,
        "generation": generation,
        "final_source": final_source,
        "flow": [
            "Learner Action", "Answer Evaluation", "Behaviour Signals", "Knowledge Tracing",
            "Mistake Diagnosis", "Concept Dependency", "Teaching Strategy", "Policy/RL Safe Decision",
            "RAG Retrieval", "CogniTutorLM / Guarded Generation", "Notebook Memory", "Revision",
            "Reward", "XAI", "Next Activity",
        ],
    }


def adaptive_path(subject, concept):
    path = FALLBACK_PATHS.get(subject, [])
    current = concept or (path[0] if path else "NOT AVAILABLE")
    idx = next((i for i, item in enumerate(path) if item.lower() in str(current).lower() or str(current).lower() in item.lower()), 0)
    return {
        "current concept": current,
        "prerequisites": path[:idx],
        "locked/unlocked concepts": [{"concept": c, "status": "completed/unlocked" if i <= idx else "locked"} for i, c in enumerate(path)],
        "completed concepts": path[:idx],
        "next concept": path[idx + 1] if idx + 1 < len(path) else "End of fallback path",
        "difficulty path": "easy -> medium -> hard",
        "can move forward": "yes" if idx + 1 < len(path) else "no",
        "reason": "Fallback path shown when live dependency decision is unavailable.",
    }


def rag_sections(subject, concept):
    resource = subject_resource(subject, concept)
    source = str(SUBJECT_DBS.get(subject)) if SUBJECT_DBS.get(subject) else "NOT AVAILABLE"
    sections = {k: resource.get(k, "NOT AVAILABLE") for k in ["definition", "base_content", "examples", "key_points", "misconceptions", "real_world_use", "next_concept_link"] if k in resource}
    if not sections:
        sections = {"definition": "NOT AVAILABLE"}
    return {"source DB": source, "retrieved sections": sections, "top chunks": read_table(SUBJECT_DBS.get(subject), "concept_resources", 5) if subject in SUBJECT_DBS else pd.DataFrame()}
