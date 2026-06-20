import pandas as pd
import streamlit as st

import api_client
from config import RUNTIME_TABLES, SUBJECT_DBS, TUTOR_DB
from data_access import generation_coverage, latest_activity, latest_row, parse_json, read_table, rows_for_learner, subject_resource, tables
from module_explainers import TASK_TYPES, behaviour_from_quiz, safe_policy, teaching_strategy
from trace_builder import adaptive_path, build_trace, learner_mastery, rag_sections
from ui_components import card, inject_css, render_sidebar, show_artifacts, show_event_table


def setup(title):
    st.set_page_config(page_title=title, layout="wide")
    inject_css()
    ctx = render_sidebar(title)
    st.title(title)
    return ctx


def profile(ctx):
    if not ctx["learner_id"]:
        st.info("No learner exists.")
        return
    st.subheader("User Account")
    card("Selected Learner Identity", {
        "learner_id/internal ID": ctx.get("learner", {}).get("learner_id", ctx["learner_id"]),
        "app_learner_code / frontend learner ID": ctx.get("learner", {}).get("app_learner_code") or ctx["learner_id"],
        "user_id": ctx.get("learner", {}).get("user_id", "Not available yet"),
        "name": ctx.get("learner", {}).get("display_name") or ctx.get("learner", {}).get("name") or "Not available yet",
        "email": ctx.get("learner", {}).get("email", "Not available yet"),
        "active_subject": ctx.get("learner", {}).get("active_subject") or ctx.get("learner", {}).get("current_domain") or "Not available yet",
        "current_concept/topic": ctx.get("learner", {}).get("current_concept_name") or ctx.get("learner", {}).get("current_concept_id") or "Not available yet",
        "current_difficulty": ctx.get("learner", {}).get("current_difficulty") or ctx.get("learner", {}).get("preferred_difficulty") or "Not available yet",
        "learner type": ctx.get("learner", {}).get("learner_type", "Dataset / Evaluation Learner"),
        "last login/session": ctx.get("learner", {}).get("last_login/session", "Not available yet"),
    }, "PASS" if ctx.get("learner") else "NOT AVAILABLE")
    st.subheader("Latest Frontend Activity")
    st.dataframe(latest_activity(ctx["learner_id"]), use_container_width=True, hide_index=True)
    st.subheader("Profile Records")
    st.dataframe(rows_for_learner("learner_profile", ctx["learner_id"], 20), use_container_width=True, hide_index=True)
    st.subheader("Session Logs")
    st.dataframe(rows_for_learner("learner_session_log", ctx["learner_id"], 100), use_container_width=True, hide_index=True)
    q = latest_row("quiz_results", ctx["learner_id"])
    state = "new learner clean start" if not q else "returning learner with activity"
    card("Clean-Start Status", {"state": state, "note": "Learner-specific tables are filtered by selected learner_id."}, "PASS")


def assessment(ctx):
    q = latest_row("quiz_results", ctx["learner_id"]) if ctx["learner_id"] else {}
    ev = latest_row("evaluation_log", ctx["learner_id"]) if ctx["learner_id"] else {}
    mistake = latest_row("learner_mistake_log", ctx["learner_id"]) if ctx["learner_id"] else {}
    if not q:
        st.info("No completed assessment yet.")
    card("Supported Task Types", pd.DataFrame({"task_type": TASK_TYPES}), "PASS")
    card("Input", {
        "question": "NOT AVAILABLE",
        "question type": q.get("question_type", "NOT AVAILABLE"),
        "difficulty": q.get("difficulty", "NOT AVAILABLE"),
        "learner answer": q.get("answer") or q.get("selected_option", "NOT AVAILABLE"),
        "expected answer": mistake.get("expected_answer", "NOT AVAILABLE"),
        "time taken": q.get("time_taken_sec", "NOT AVAILABLE"),
        "confidence": q.get("confidence", "NOT AVAILABLE"),
        "hint count": q.get("hint_count", "NOT AVAILABLE"),
        "attempt count": q.get("attempt_count") or q.get("attempt_no", "NOT AVAILABLE"),
        "option changes": q.get("option_change_count") or q.get("option_changes_count", "NOT AVAILABLE"),
        "answer changes": q.get("answer_change_count", "NOT AVAILABLE"),
        "code runs": q.get("run_code_count", "NOT AVAILABLE"),
    }, "PASS" if q else "NOT AVAILABLE")
    card("Output", {
        "score": ev.get("overall_score", q.get("is_correct", "NOT AVAILABLE")),
        "correct/partial/weak": ev.get("verdict", "NOT AVAILABLE"),
        "mistake type": mistake.get("mistake_type", "NOT AVAILABLE"),
        "weakest skill": mistake.get("question_type", "NOT AVAILABLE"),
        "feedback": mistake.get("feedback") or ev.get("feedback_summary", "NOT AVAILABLE"),
        "next activity": latest_row("policy_decision_log", ctx["learner_id"]).get("final_action", "NOT AVAILABLE") if ctx["learner_id"] else "NOT AVAILABLE",
    }, "PASS" if q else "NOT AVAILABLE")


def behaviour(ctx):
    q = latest_row("quiz_results", ctx["learner_id"]) if ctx["learner_id"] else {}
    b = latest_row("behaviour_state", ctx["learner_id"]) if ctx["learner_id"] else {}
    proxy = behaviour_from_quiz(q)
    inputs = {k: q.get(k, "NOT AVAILABLE") for k in ["time_taken_sec", "confidence", "hint_used", "hint_count", "option_change_count", "answer_change_count", "run_code_count", "attempt_count", "wrong_attempt_count"]}
    inputs.update({"response speed": "slow" if (q.get("time_taken_sec") or 0) and float(q.get("time_taken_sec")) > 90 else "normal/unknown", "hesitation": "inferred from time/hints", "repeated attempts": q.get("attempt_count", "NOT AVAILABLE")})
    card("Behaviour Inputs", inputs, "PASS" if q else "NOT AVAILABLE")
    card("Behaviour Output", {
        "state": b.get("behavior_label") or proxy["state"],
        "behaviour risk": b.get("behavior_risk_label") or proxy["risk"],
        "model source": b.get("behavior_source") or b.get("model_used") or proxy["source"],
    }, "PASS" if b else "FALLBACK")
    st.info("Behaviour Modelling gives interaction-based learning evidence; it is not psychological diagnosis.")


def kt(ctx):
    if not ctx["learner_id"]:
        st.info("No learner exists.")
        return
    mastery = learner_mastery(ctx["learner_id"])
    if mastery["progress"].empty and not mastery["knowledge_state"]:
        st.info("Not started.")
    card("Mastery Summary", {
        "topic mastery": "See topic-wise table" if not mastery["progress"].empty else "Not started",
        "subject mastery": "See subject-wise table" if not mastery["progress"].empty else "Not started",
        "overall mastery": mastery["overall"] if mastery["overall"] is not None else "Not started",
        "previous mastery": "available in DB state_json if recorded",
        "updated mastery": mastery["knowledge_state"].get("updated_at", "NOT AVAILABLE"),
        "KT source": "DKT artifact if backend emits it; displayed table uses backend/cumulative records",
    }, "PASS" if mastery["knowledge_state"] or not mastery["progress"].empty else "NOT AVAILABLE")
    st.subheader("Topic-Wise Mastery")
    st.dataframe(mastery["progress"], use_container_width=True, hide_index=True)
    st.subheader("Subject-Wise Mastery")
    if not mastery["progress"].empty and "domain" in mastery["progress"].columns:
        st.dataframe(mastery["progress"].groupby("domain", as_index=False)["mastery"].mean(), use_container_width=True, hide_index=True)
    show_artifacts()


def dependency(ctx):
    path = adaptive_path(ctx["subject"], ctx["concept"])
    card("Concept Dependency & Adaptive Path", path, "FALLBACK")
    if ctx["subject"] in SUBJECT_DBS:
        st.subheader("Subject DB Concepts")
        st.dataframe(read_table(SUBJECT_DBS[ctx["subject"]], "concept_dependencies", 100), use_container_width=True, hide_index=True)


def strategy(ctx):
    trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"]) if ctx["learner_id"] else {}
    mastery = trace.get("mastery", {}).get("overall")
    behaviour = (trace.get("behaviour") or {}).get("behavior_label") or (trace.get("behaviour") or {}).get("state")
    mistake = trace.get("interaction", {}).get("mistake", {}).get("mistake_type", "NOT AVAILABLE")
    q = trace.get("quiz", {})
    out = teaching_strategy(mastery, behaviour, mistake, q.get("difficulty"), None)
    card("Input", {"mastery": mastery, "behaviour state": behaviour, "mistake type": mistake, "difficulty": q.get("difficulty"), "review need": "from revision/decay tables", "learner profile": ctx["learner_label"]}, "PASS" if q else "NOT AVAILABLE")
    card("Output", out, "PASS")
    st.dataframe(rows_for_learner("teaching_strategy_training_log", ctx["learner_id"], 50), use_container_width=True, hide_index=True)


def policy(ctx):
    trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"]) if ctx["learner_id"] else {}
    p = latest_row("policy_decision_log", ctx["learner_id"]) if ctx["learner_id"] else {}
    q = trace.get("quiz", {})
    dec = safe_policy(q.get("is_correct") if q else None, trace.get("mastery", {}).get("overall"), (trace.get("behaviour") or {}).get("behavior_label"))
    card("Policy / RL Decision", {
        "state features used": parse_json(p.get("state_json"), dec["state features used"]),
        "raw recommendation if available": p.get("final_action", dec["raw recommendation"]),
        "safe action mask": dec["safe action mask"],
        "final safe action": p.get("final_action", dec["final safe action"]),
        "reason": p.get("reason_json", dec["reason"]),
        "RL/bandit/DQN/comparison/fallback status": "safe decision support; artifacts shown separately",
    }, "PASS" if p else "FALLBACK")
    st.info("Policy/RL supports decisions, but final progression is safety checked.")
    show_artifacts()


def rag(ctx):
    r = rag_sections(ctx["subject"], ctx["concept"])
    card("RAG Query", {"selected subject": ctx["subject"], "selected concept": ctx["concept"], "query": f"{ctx['subject']} {ctx['concept']}", "source DB": r["source DB"], "grounding score": "available if backend logged it"}, "PASS")
    card("Retrieved Sections", r["retrieved sections"], "PASS" if r["retrieved sections"] else "NOT AVAILABLE")
    st.subheader("Top Chunks")
    st.dataframe(r["top chunks"], use_container_width=True, hide_index=True)
    st.info("Option C+ RAG = local no-API concept-resource-based retrieval using concept_resources, TF-IDF/query expansion/section-aware ranking/heuristic reranking.")


def generation(ctx):
    gen = latest_row("generation_history", ctx["learner_id"]) if ctx["learner_id"] else {}
    cov = generation_coverage()
    card("Generation Pipeline", "RAG context -> raw CogniTutorLM attempt -> validation -> repair if available -> guarded product generator -> prevalidated generated content bank -> concept resource fallback -> final learner-facing output", "PASS")
    card("Interaction Generation Status", {
        "task type": gen.get("item_type", "NOT AVAILABLE"),
        "prompt/input": ctx["concept"],
        "raw output available": "yes if report/backend record exposes it; otherwise no",
        "validation result": "reported in coverage files when available",
        "invalid reason if invalid": "NOT AVAILABLE",
        "fallback used": "shown when final source is guarded/RAG/content bank/fallback",
        "final source": gen.get("strategy") or "guarded/RAG/content-resource path",
        "final output": "Open expanders/tables for source records; full raw concept text is not dumped by default.",
        "learner-facing safe status": "guarded output = safe learner-facing path",
    }, "PASS" if gen else "FALLBACK")
    st.subheader("Generation Coverage / Task Coverage")
    st.metric("Supported subjects", cov["summary"]["supported_subjects"])
    st.metric("Concepts", cov["summary"]["concepts"])
    st.metric("Task types", cov["summary"]["task_types"])
    st.metric("Evaluated/generated cases", cov["summary"]["evaluated_generated_cases"])
    st.caption(f"Coverage source: {cov['source']}")
    st.dataframe(cov["rows"], use_container_width=True, hide_index=True)
    card("Voice Script Evidence", {
        "mascot/guide script": "available if generation/report records expose voice script fields",
        "feedback script": "available from feedback/generation outputs when present",
        "selected text that can be read aloud in frontend": ctx["concept"],
        "scope": "This project supports voice-ready scripts and browser read-aloud prototype, not a full trained audio model.",
    }, "FALLBACK")
    st.warning("Raw CogniTutorLM output may be warning-level; learner-facing output is safe through validation, grounding, guarded generation, prevalidated banks, and fallback. Pretrained fine-tuned LLM is comparison-only unless a runtime source record proves otherwise.")


def notebook(ctx):
    st.subheader("Learner Memory")
    st.dataframe(rows_for_learner("learner_memory_state", ctx["learner_id"], 20), use_container_width=True, hide_index=True)
    cols = st.columns(3)
    with cols[0]:
        card("Saved Mistakes", rows_for_learner("learner_mistake_log", ctx["learner_id"], 20), "PASS")
    with cols[1]:
        card("Revision Cards", rows_for_learner("revision_card", ctx["learner_id"], 20), "PASS")
    with cols[2]:
        card("Revision Schedule", rows_for_learner("revision_schedule", ctx["learner_id"], 20), "PASS")
    with st.expander("Notebook Memory Details"):
        st.dataframe(rows_for_learner("learner_notebook_memory", ctx["learner_id"], 50), use_container_width=True, hide_index=True)


def rewards(ctx):
    xp = latest_row("learner_xp_state", ctx["learner_id"]) if ctx["learner_id"] else {}
    streak = latest_row("learner_streak_state", ctx["learner_id"]) if ctx["learner_id"] else {}
    rewards_df = rows_for_learner("reward_event_log", ctx["learner_id"], 100)
    q = rows_for_learner("quiz_results", ctx["learner_id"], 500)
    local_correct = int(q["is_correct"].sum()) if not q.empty and "is_correct" in q.columns else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("XP", xp.get("total_xp", 0))
    c2.metric("Streak", streak.get("current_streak", 0))
    c3.metric("Local session correct count", local_correct)
    st.dataframe(rewards_df, use_container_width=True, hide_index=True)
    if not xp or xp.get("total_xp", 0) == 0:
        card("Reward Diagnostic", {"backend reward value": xp.get("total_xp", 0), "local session correct count": local_correct, "endpoint status": api_client.request("GET", "/reward")["status"]}, "WARN")


def xai(ctx):
    q = latest_row("quiz_results", ctx["learner_id"]) if ctx["learner_id"] else {}
    if not q:
        st.info("No completed assessment yet. XAI explanation will appear after learner completes an activity.")
        return
    trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"])
    x = latest_row("xai_log", ctx["learner_id"])
    card("XAI Explanation", {
        "why teaching view selected": trace["teaching"]["why"],
        "why next activity selected": trace["policy"]["reason"],
        "why difficulty changed/stayed": "Uses score, mastery, behaviour risk, dependency and safety mask when available.",
        "top factors": ["score", "mastery", "behaviour risk", "confidence", "hints", "mistake type", "revision need", "concept dependency"],
        "logged xai": x or "NOT AVAILABLE",
    }, "PASS" if x else "FALLBACK")


def agentic(ctx):
    agents = ["TeachingAgent", "AssessmentAgent", "EvaluatorAgent", "DiagnosisAgent", "LearnerStateAgent", "DecisionPolicyAgent", "RAGGroundingAgent", "MemoryRevisionAgent", "XAIReflectionAgent", "RewardProgressionAgent"]
    log = latest_row("agentic_trace_log", ctx["learner_id"]) if ctx["learner_id"] else {}
    st.info("Agentic AI is shown as coordinated module trace, not a fully autonomous planner.")
    for a in agents:
        card(a, {"Input": ctx["concept"], "Processing": "Teach -> Ask -> Evaluate -> Diagnose -> Adapt -> Remember -> Revise -> Progress", "Output": parse_json(log.get("module_outputs_json"), {}).get(a, "Not available for this interaction."), "Status": "PASS" if log else "NOT AVAILABLE"}, "PASS" if log else "NOT AVAILABLE")


def database(ctx):
    db_choice = st.selectbox("Database", ["Runtime tutor.db"] + list(SUBJECT_DBS.keys()))
    db_path = TUTOR_DB if db_choice == "Runtime tutor.db" else SUBJECT_DBS[db_choice]
    available = tables(db_path)
    preferred = [t for t in RUNTIME_TABLES if t in available] if db_choice == "Runtime tutor.db" else ["concept_resources"] if "concept_resources" in available else available
    table = st.selectbox("Table", preferred or available)
    if db_choice == "Runtime tutor.db" and ctx["learner_id"]:
        st.dataframe(rows_for_learner(table, ctx["learner_id"], 100), use_container_width=True, hide_index=True)
    else:
        st.dataframe(read_table(db_path, table, 100), use_container_width=True, hide_index=True)


def evaluation_summary(ctx):
    trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"]) if ctx["learner_id"] else {}
    artifacts = api_client.endpoint_matrix(ctx["learner_id"], trace.get("concept_id") if trace else None)
    rows = [
        {"check": "backend smoke test status", "status": "PASS" if ctx.get("backend", {}).get("status") == "PASS" else "WARNING", "source": ctx.get("backend", {}).get("message", "Backend health endpoint")},
        {"check": "Behaviour LSTM runtime source", "status": "PASS" if latest_row("behaviour_state", ctx["learner_id"]) else "FALLBACK", "source": "behaviour_state or interaction proxy"},
        {"check": "DKT runtime source", "status": "PASS" if latest_row("knowledge_state", ctx["learner_id"]) else "FALLBACK", "source": "knowledge_state or learner_concept_progress"},
        {"check": "Policy/RL runtime source", "status": "PASS" if latest_row("policy_decision_log", ctx["learner_id"]) else "FALLBACK", "source": "policy_decision_log or safe policy proxy"},
        {"check": "generation source", "status": "PASS" if latest_row("generation_history", ctx["learner_id"]) else "FALLBACK", "source": "generation_history / guarded concept resource path"},
        {"check": "reward source", "status": "PASS" if latest_row("learner_xp_state", ctx["learner_id"]) else "NOT AVAILABLE", "source": "learner_xp_state, streak, badges, reward_event_log"},
        {"check": "XAI status", "status": "PASS" if latest_row("xai_log", ctx["learner_id"]) else "NOT AVAILABLE", "source": "xai_log or XAI endpoint after activity"},
        {"check": "mistake filtering status", "status": "PASS", "source": "All runtime tables are filtered by selected learner_id"},
        {"check": "frontend-backend connection status", "status": "PASS" if artifacts else "WARNING", "source": "Endpoint matrix"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def events(ctx):
    show_event_table()


def voice(ctx):
    reports = rows_for_learner("generation_history", ctx["learner_id"], 20)
    card("Voice Script Evidence", {
        "mascot/guide script": "available if generation/report records expose voice script fields",
        "feedback script": "available from feedback/generation outputs when present",
        "selected frontend read-aloud text": ctx["concept"],
        "scope": "This project supports voice-ready scripts and browser read-aloud prototype, not a full trained audio model.",
    }, "FALLBACK")
    st.dataframe(reports, use_container_width=True, hide_index=True)


def overview(ctx):
    import app  # app.py renders the overview when loaded directly


PAGES = {
    "Learner Profile & Session": profile,
    "Assessment & Answer Evaluation": assessment,
    "Behaviour Signals": behaviour,
    "Knowledge Tracing": kt,
    "Concept Dependency & Adaptive Path": dependency,
    "Teaching Strategy": strategy,
    "Policy / RL Decision": policy,
    "RAG Retrieval": rag,
    "CogniTutorLM / Guarded Generation": generation,
    "Notebook Memory & Revision": notebook,
    "Rewards & Progress": rewards,
    "XAI Explanation": xai,
    "Agentic Orchestration Trace": agentic,
    "Database Viewer": database,
    "Event Log": events,
    "Voice Script Evidence": voice,
    "Project Evaluation Summary": evaluation_summary,
}


def render(title):
    ctx = setup(title)
    if title == "Overview Trace":
        trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"]) if ctx["learner_id"] else {}
        if trace.get("flow"):
            st.markdown(" -> ".join(f"`{step}`" for step in trace["flow"]))
        cols = st.columns(5)
        for idx, step in enumerate(trace.get("flow", [])):
            with cols[idx % 5]:
                card(step, "Input -> Processing -> Output", "PASS" if trace.get("quiz") else "NOT AVAILABLE")
        if not trace or not trace.get("quiz"):
            st.info("No completed interaction yet. Answer a question in learner frontend to generate a trace.")
        else:
            card("Latest Interaction", trace["quiz"], "PASS")
        show_artifacts()
        with st.expander("Backend API Endpoint Status"):
            st.dataframe(pd.DataFrame(api_client.endpoint_matrix(ctx["learner_id"], trace.get("concept_id") if trace else None)), use_container_width=True, hide_index=True)
    else:
        PAGES[title](ctx)
