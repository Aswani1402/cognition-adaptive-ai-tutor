import pandas as pd
import streamlit as st

import api_client
from config import SUBJECT_DBS, TUTOR_DB
from data_access import append_event, artifact_status, db_status, get_users, learner_summary, read_events, subject_concepts


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem;}
        .card {border: 1px solid #d8dee9; border-radius: 8px; padding: 14px; margin: 8px 0; background: #ffffff;}
        .small {color: #5b6472; font-size: 0.9rem;}
        .badge {display:inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.78rem; border:1px solid #ccd3dd;}
        .PASS {background:#e8f6ef;color:#17633a;} .WARN {background:#fff5df;color:#815800;}
        .FALLBACK {background:#eef2ff;color:#354da1;} .NOTAVAILABLE {background:#f3f4f6;color:#4b5563;}
        .arrow {text-align:center; color:#667085; font-weight:600;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def badge(status):
    css = str(status).replace(" ", "")
    st.markdown(f"<span class='badge {css}'>{status}</span>", unsafe_allow_html=True)


def card(title, body=None, status=None):
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    cols = st.columns([4, 1])
    cols[0].markdown(f"**{title}**")
    if status:
        with cols[1]:
            badge(status)
    if body is not None:
        if isinstance(body, pd.DataFrame):
            st.dataframe(body, use_container_width=True, hide_index=True)
        elif isinstance(body, dict):
            st.json(body)
        else:
            st.write(body)
    st.markdown("</div>", unsafe_allow_html=True)


def safe_text(value, fallback="NOT AVAILABLE"):
    if value is None or value == "":
        return fallback
    return value


def render_sidebar(page_name="Dashboard"):
    st.sidebar.title("Developer Demo")
    if st.sidebar.button("Refresh"):
        st.cache_data.clear()
        st.rerun()

    health = api_client.backend_health()
    st.sidebar.caption("Backend status")
    st.sidebar.markdown(f"<span class='badge {health['status'].replace(' ', '')}'>{health['status']}</span>", unsafe_allow_html=True)
    dbs = db_status(TUTOR_DB)
    st.sidebar.caption("Database status")
    st.sidebar.markdown(f"<span class='badge {dbs['status'].replace(' ', '')}'>{dbs['status']}</span>", unsafe_allow_html=True)

    users = get_users()
    if users.empty:
        st.sidebar.warning("No learner exists.")
        learner_id = None
        learner_label = "No learner"
    else:
        def label(row):
            name = row.get("display_name") or row.get("name") or row.get("email") or row.get("learner_id")
            code = row.get("app_learner_code") or row.get("learner_id") or row.get("id")
            learner_type = row.get("learner_type") or "Dataset / Evaluation Learner"
            email = row.get("email") or "no email"
            return f"{code} | {name} | {email} | {learner_type}"
        labels = [label(r) for _, r in users.iterrows()]
        selected = st.sidebar.selectbox("Learner", labels)
        learner_row = users.iloc[labels.index(selected)].to_dict()
        learner_id = learner_row.get("learner_id") or learner_row.get("id")
        learner_label = selected
        st.sidebar.caption(f"Selected type: {learner_row.get('learner_type', 'Dataset / Evaluation Learner')}")
        st.sidebar.caption(f"Frontend learner ID: {learner_row.get('app_learner_code') or learner_id}")

    subject = st.sidebar.selectbox("Subject", list(SUBJECT_DBS.keys()))
    concepts = subject_concepts(subject)
    names = []
    if not concepts.empty:
        for c in ["topic", "name", "concept_name", "concept_id"]:
            if c in concepts.columns:
                names = concepts[c].dropna().astype(str).tolist()
                break
    concept = st.sidebar.selectbox("Concept", names or ["NOT AVAILABLE"])
    append_event(learner_id, subject, concept, page_name, "page opened", "developer_demo", "PASS", f"Viewed {page_name}")
    return {"learner_id": learner_id, "learner_label": learner_label, "learner": learner_summary(learner_id), "subject": subject, "concept": concept, "backend": health, "db": dbs}


def show_artifacts():
    st.subheader("Model/Artifact Status")
    st.dataframe(artifact_status(), use_container_width=True, hide_index=True)


def show_event_table():
    events = read_events()
    st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
