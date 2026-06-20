import streamlit as st

import api_client
from data_access import latest_activity
from trace_builder import build_trace
from ui_components import card, inject_css, render_sidebar, show_artifacts

st.set_page_config(page_title="Cognition-Adaptive AI Tutor Developer Demo", layout="wide")
inject_css()
ctx = render_sidebar("Overview Trace")

st.title("Cognition-Adaptive AI Tutor: Developer Demo")
st.caption("Reviewer dashboard showing backend intelligence, live records where available, and explicit fallback/status labels.")

trace = build_trace(ctx["learner_id"], ctx["subject"], ctx["concept"]) if ctx["learner_id"] else {}

if ctx.get("learner"):
    card("Selected Real-Time Learner", {
        "learner_id/internal ID": ctx["learner"].get("learner_id", ctx["learner_id"]),
        "app_learner_code / frontend learner ID": ctx["learner"].get("app_learner_code") or ctx["learner_id"],
        "user_id": ctx["learner"].get("user_id", "Not available yet"),
        "name": ctx["learner"].get("display_name") or ctx["learner"].get("name") or "Not available yet",
        "email": ctx["learner"].get("email", "Not available yet"),
        "active_subject": ctx["learner"].get("active_subject") or ctx["learner"].get("current_domain") or "Not available yet",
        "current_concept/topic": ctx["learner"].get("current_concept_name") or ctx["learner"].get("current_concept_id") or "Not available yet",
        "current_difficulty": ctx["learner"].get("current_difficulty") or ctx["learner"].get("preferred_difficulty") or "Not available yet",
        "learner type": ctx["learner"].get("learner_type", "Dataset / Evaluation Learner"),
        "last login/session": ctx["learner"].get("last_login/session", "Not available yet"),
    }, "PASS")
    st.subheader("Latest Frontend Activity")
    st.dataframe(latest_activity(ctx["learner_id"]), use_container_width=True, hide_index=True)

if trace.get("flow"):
    st.markdown(" -> ".join(f"`{step}`" for step in trace["flow"]))

cols = st.columns(5)
for idx, step in enumerate(trace.get("flow", [])):
    with cols[idx % 5]:
        card(step, "Input -> Processing -> Output", "PASS" if trace.get("quiz") else "NOT AVAILABLE")

if not trace or not trace.get("quiz"):
    st.info("No completed interaction yet. Answer a question in learner frontend to generate a trace.")
else:
    q = trace["quiz"]
    latest = {
        "learner_id": q.get("learner_id"),
        "email/name": ctx["learner_label"],
        "subject": q.get("subject") or ctx["subject"],
        "concept topic name": q.get("concept_name") or ctx["concept"],
        "difficulty": q.get("difficulty"),
        "question type": q.get("question_type"),
        "learner answer": q.get("answer") or q.get("selected_option"),
        "expected answer": trace.get("interaction", {}).get("mistake", {}).get("expected_answer", "NOT AVAILABLE"),
        "score": trace.get("interaction", {}).get("evaluation", {}).get("overall_score", q.get("is_correct")),
        "correctness": q.get("is_correct"),
        "next activity": trace.get("policy", {}).get("final safe action"),
        "content/generation source": trace.get("final_source"),
    }
    card("Latest Interaction", latest, "PASS")

show_artifacts()
with st.expander("Backend API Endpoint Status"):
    st.dataframe(api_client.endpoint_matrix(ctx["learner_id"], trace.get("concept_id") if trace else None), use_container_width=True, hide_index=True)
