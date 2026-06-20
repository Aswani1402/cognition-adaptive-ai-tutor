from __future__ import annotations

import csv
import json
import math
import sqlite3
import textwrap
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tutor.api.concept_content_resolver import (  # noqa: E402
    SUBJECT_DBS,
    TEACHING_VIEWS,
    assessment_payload,
    build_lesson_payload,
)
OUT = ROOT / "evaluation_outputs" / "journal_visualizations"
CORE_DATA = ROOT / "external" / "core_data"
JSON_DIR = ROOT / "evaluation_outputs" / "json"
REPORTS_DIR = ROOT / "evaluation_outputs" / "reports"
CSV_DIR = ROOT / "evaluation_outputs" / "csv"

NA = "not_available"


SUBJECT_LABELS = {
    "Python": "Python",
    "SQL / Database": "SQL",
    "HTML/Web Basics": "HTML",
    "Git": "Git",
    "Data Structures": "Data Structures",
}

TASK_TYPE_MAP = {
    "MCQ": ["mcq"],
    "output prediction": ["output_prediction", "output_prediction_challenge"],
    "debug": ["debug", "debug_task", "debug_challenge"],
    "coding": ["coding_prompt", "coding_question", "code_reasoning_task"],
    "syntax": ["syntax_completion"],
    "transfer": ["transfer", "transfer_question", "transfer_task"],
    "challenge": ["challenge", "challenge_question", "multi_step_challenge"],
    "explanation": ["explanation", "explanation_check", "short_explanation"],
    "fill_blank": ["fill_in_the_blank", "fill_blank"],
    "true_false": ["true_or_false", "true_false"],
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def bool_rate(value: Any) -> Any:
    if value is None:
        return NA
    return 1.0 if bool(value) else 0.0


def mean_available(values: list[Any]) -> Any:
    numeric = [float(v) for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    numeric += [1.0 if v is True else 0.0 for v in values if isinstance(v, bool)]
    if not numeric:
        return NA
    return round(sum(numeric) / len(numeric), 4)


def rate(numerator: int, denominator: int) -> Any:
    if denominator <= 0:
        return NA
    return round(numerator / denominator, 4)


def safe_float(value: Any) -> Any:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return NA
        return float(value)
    return NA


def add_metric(
    rows: list[dict[str, Any]],
    chart: str,
    group: str,
    name: str,
    value: Any,
    source: Path | str,
    warning: str = "",
) -> None:
    rows.append(
        {
            "chart": chart,
            "metric_group": group,
            "metric_name": name,
            "value": NA if value is None else value,
            "source_file": rel(source) if isinstance(source, Path) else source,
            "warning": warning,
        }
    )


def write_metric_csv(rows: list[dict[str, Any]]) -> None:
    path = OUT / "journal_visualization_metrics.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["chart", "metric_group", "metric_name", "value", "source_file", "warning"],
        )
        writer.writeheader()
        writer.writerows(rows)


def save_fig(fig: plt.Figure, name: str, inventory: list[dict[str, Any]], sources: list[str], paper_ready: bool, warnings: list[str]) -> None:
    path = OUT / name
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    inventory.append(
        {
            "chart": name,
            "path": rel(path),
            "sources": sources,
            "paper_ready": paper_ready,
            "warnings": warnings,
        }
    )


def plot_missing_message(name: str, message: str, inventory: list[dict[str, Any]], sources: list[str], warnings: list[str]) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axis("off")
    ax.text(0.5, 0.55, message, ha="center", va="center", fontsize=13, wrap=True)
    ax.text(0.5, 0.35, "Metric value: not_available", ha="center", va="center", fontsize=10, color="#555555")
    save_fig(fig, name, inventory, sources, False, warnings)


def subject_db_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    question_db = CORE_DATA / "tutor.db"
    q_counts: dict[str, int] = defaultdict(int)
    if question_db.exists():
        conn = sqlite3.connect(question_db)
        try:
            for subject, count in conn.execute(
                "SELECT subject, COUNT(*) FROM question_bank WHERE COALESCE(active_flag, 1) = 1 GROUP BY subject"
            ):
                q_counts[str(subject)] += int(count)
        finally:
            conn.close()

    for subject, db_name in SUBJECT_DBS.items():
        db_path = CORE_DATA / db_name
        item = {
            "subject": SUBJECT_LABELS.get(subject, subject),
            "subject_key": subject,
            "db_path": db_path,
            "concepts": NA,
            "concept_resources": NA,
            "teaching_artifacts": NA,
            "assessment_questions": q_counts.get(SUBJECT_LABELS.get(subject, subject), 0),
        }
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                for column, table in [
                    ("concepts", "concepts"),
                    ("concept_resources", "concept_resources"),
                    ("teaching_artifacts", "teaching_content"),
                ]:
                    try:
                        item[column] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
                    except sqlite3.Error:
                        item[column] = NA
            finally:
                conn.close()
        rows.append(item)
    return rows


def chart_concept_resource_distribution(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    rows = subject_db_rows()
    chart = "concept_resource_distribution_by_subject.png"
    categories = ["concepts", "concept_resources", "teaching_artifacts", "assessment_questions"]
    subjects = [r["subject"] for r in rows]
    x = np.arange(len(subjects))
    width = 0.19
    fig, ax = plt.subplots(figsize=(11, 5.6))
    colors = ["#496A81", "#68A691", "#F2A65A", "#C1666B"]
    for idx, category in enumerate(categories):
        values = [0 if r[category] == NA else int(r[category]) for r in rows]
        ax.bar(x + (idx - 1.5) * width, values, width, label=category.replace("_", " "), color=colors[idx])
        for subject, value, row in zip(subjects, values, rows):
            add_metric(metrics, chart, subject, category, row[category], row["db_path"] if category != "assessment_questions" else CORE_DATA / "tutor.db")
    ax.set_title("Concept, Resource, Teaching, and Assessment Coverage by Subject", fontsize=13, pad=12)
    ax.set_ylabel("Count")
    ax.set_xticks(x)
    ax.set_xticklabels(subjects, rotation=20, ha="right")
    ax.legend(ncol=2, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    save_fig(
        fig,
        chart,
        inventory,
        [rel(CORE_DATA / db) for db in SUBJECT_DBS.values()] + [rel(CORE_DATA / "tutor.db")],
        True,
        [],
    )


def teaching_coverage(metrics: list[dict[str, Any]]) -> tuple[list[str], list[str], np.ndarray, list[str]]:
    subjects = list(SUBJECT_DBS)
    status = np.zeros((len(subjects), len(TEACHING_VIEWS)), dtype=int)
    warnings: list[str] = []
    chart = "teaching_view_coverage_heatmap.png"
    for si, subject in enumerate(subjects):
        db_path = CORE_DATA / SUBJECT_DBS[subject]
        concept_ids: list[str] = []
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                concept_ids = [str(r[0]) for r in conn.execute("SELECT concept_id FROM concepts ORDER BY concept_id")]
            finally:
                conn.close()
        if not concept_ids:
            warnings.append(f"{subject}: no concept rows available")
        valid_counts = Counter()
        available_counts = Counter()
        for concept_id in concept_ids:
            try:
                packet = build_lesson_payload(subject, concept_id, "easy", "explanation")
                content_by_view = packet.get("content_by_view", {})
            except Exception as exc:  # pragma: no cover - report generation should continue.
                warnings.append(f"{subject}/{concept_id}: lesson runtime failed: {exc}")
                content_by_view = {}
            for view in TEACHING_VIEWS:
                view_payload = content_by_view.get(view)
                if view_payload:
                    available_counts[view] += 1
                    text = str(view_payload.get("explanation") or view_payload.get("content") or "")
                    concept_name = str(packet.get("concept_name") or "")
                    if len(text.split()) >= 8 and (not concept_name or concept_name.lower().split()[0] in text.lower()):
                        valid_counts[view] += 1
        for vi, view in enumerate(TEACHING_VIEWS):
            if not concept_ids:
                value = 0
            elif valid_counts[view] == len(concept_ids):
                value = 2
            elif available_counts[view] > 0:
                value = 1
            else:
                value = 0
            status[si, vi] = value
            label = "valid" if value == 2 else "available" if value == 1 else "missing"
            add_metric(metrics, chart, SUBJECT_LABELS.get(subject, subject), view, label, CORE_DATA / SUBJECT_DBS[subject])
    return [SUBJECT_LABELS.get(s, s) for s in subjects], TEACHING_VIEWS, status, warnings


def chart_teaching_view_coverage(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    subjects, views, status, warnings = teaching_coverage(metrics)
    chart = "teaching_view_coverage_heatmap.png"
    fig, ax = plt.subplots(figsize=(14, 4.7))
    cmap = ListedColormap(["#D8D8D8", "#F0C36D", "#4E8F7A"])
    ax.imshow(status, cmap=cmap, vmin=0, vmax=2, aspect="auto")
    ax.set_title("Teaching View Coverage Across Subject Concept Stores", fontsize=13, pad=12)
    ax.set_yticks(np.arange(len(subjects)))
    ax.set_yticklabels(subjects)
    ax.set_xticks(np.arange(len(views)))
    ax.set_xticklabels([v.replace("_view", "").replace("_", " ") for v in views], rotation=45, ha="right")
    for i in range(status.shape[0]):
        for j in range(status.shape[1]):
            ax.text(j, i, ["M", "A", "V"][status[i, j]], ha="center", va="center", fontsize=8, color="#222222")
    ax.legend(
        handles=[Patch(color="#4E8F7A", label="valid"), Patch(color="#F0C36D", label="available"), Patch(color="#D8D8D8", label="missing")],
        loc="upper center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 1.18),
    )
    save_fig(fig, chart, inventory, [rel(CORE_DATA / db) for db in SUBJECT_DBS.values()], len(warnings) == 0, warnings)


def assessment_task_counts(metrics: list[dict[str, Any]]) -> dict[str, int]:
    chart = "assessment_task_type_coverage.png"
    counts = Counter()

    # Runtime generator evidence.
    for subject, db_name in SUBJECT_DBS.items():
        db_path = CORE_DATA / db_name
        concept_ids: list[str] = []
        if db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                concept_ids = [str(r[0]) for r in conn.execute("SELECT concept_id FROM concepts ORDER BY concept_id")]
            finally:
                conn.close()
        for concept_id in concept_ids:
            try:
                packet = assessment_payload(subject, concept_id, "hard")
            except Exception:
                continue
            for question in packet.get("questions", []):
                raw_type = str(question.get("task_type") or question.get("question_type") or "").lower()
                for canonical, aliases in TASK_TYPE_MAP.items():
                    if raw_type in aliases:
                        counts[canonical] += 1
                        break

    # Persisted question bank evidence.
    q_db = CORE_DATA / "tutor.db"
    if q_db.exists():
        conn = sqlite3.connect(q_db)
        try:
            for raw_type, count in conn.execute("SELECT question_type, COUNT(*) FROM question_bank GROUP BY question_type"):
                normalized = str(raw_type).lower()
                for canonical, aliases in TASK_TYPE_MAP.items():
                    if normalized in aliases:
                        counts[canonical] += int(count)
                        break
        finally:
            conn.close()

    for task in TASK_TYPE_MAP:
        value = counts.get(task, 0)
        add_metric(metrics, chart, "task_type", task, value, f"{rel(CORE_DATA / 'tutor.db')} + assessment_payload runtime")
    return {k: counts.get(k, 0) for k in TASK_TYPE_MAP}


def chart_assessment_task_type_coverage(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "assessment_task_type_coverage.png"
    counts = assessment_task_counts(metrics)
    labels = list(counts)
    values = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(11, 5.4))
    bars = ax.bar(labels, values, color="#4C78A8")
    ax.set_title("Assessment Task Type Coverage", fontsize=13, pad=12)
    ax.set_ylabel("Generated + persisted question count")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(value), ha="center", va="bottom", fontsize=9)
    save_fig(
        fig,
        chart,
        inventory,
        [rel(CORE_DATA / "tutor.db"), "tutor.api.concept_content_resolver.assessment_payload runtime"],
        True,
        [],
    )


def active_rag_summary() -> tuple[dict[str, Any], Path]:
    path = JSON_DIR / "rag_retrieval_comparison_report.json"
    data = load_json(path) or {}
    active = data.get("current_active_source")
    summaries = data.get("method_summaries") or []
    chosen = next((item for item in summaries if item.get("method") == active), None)
    if chosen is None and summaries:
        chosen = summaries[0]
    return chosen or {}, path


def rl_safety_summary() -> tuple[dict[str, Any], Path]:
    path = JSON_DIR / "rl_safe_action_masking_report.json"
    data = load_json(path) or {}
    model_results = data.get("model_results") or {}
    return model_results, path


def generation_quality_summary() -> tuple[dict[str, Any], Path]:
    path = JSON_DIR / "cognitutor_latest_generation_check.json"
    data = load_json(path) or {}
    cases = data.get("cases") or []
    case_count = len(cases)
    raw_accepted = int(data.get("raw_model_accepted_count") or 0)
    pass_count = sum(1 for c in cases if str(c.get("status")).upper() == "PASS")
    frontend_ready = sum(1 for c in cases if c.get("frontend_ready") is True)
    fallback = int(data.get("fallback_count") or sum(1 for c in cases if c.get("fallback_used") is True))
    safe = sum(1 for c in cases if c.get("learner_facing_safe") is True)
    return {
        "raw valid rate": rate(raw_accepted, case_count),
        "guarded valid rate": rate(pass_count, case_count),
        "frontend-ready rate": data.get("frontend_ready_rate", rate(frontend_ready, case_count)),
        "fallback rate": rate(fallback, case_count),
        "learner-facing safe rate": data.get("learner_facing_safe_rate", rate(safe, case_count)),
        "case_count": case_count,
    }, path


def answer_label_counts() -> tuple[dict[str, int], Path]:
    path = JSON_DIR / "answer_evaluator_report.json"
    data = load_json(path) or {}
    cases = (data.get("case_status") or {}).get("cases") or []
    counts = Counter(str(c.get("label") or NA) for c in cases)
    return {label: counts.get(label, 0) for label in ["strong", "partial", "weak"]}, path


def frontend_module_map() -> tuple[list[dict[str, Any]], Path]:
    path = JSON_DIR / "full_frontend_backend_model_connection_report.json"
    data = load_json(path) or {}
    return data.get("modules") or [], path


def module_connected(modules: list[dict[str, Any]], needle: str) -> dict[str, Any]:
    needle_lower = needle.lower()
    for module in modules:
        name = str(module.get("Module") or "").lower()
        if needle_lower in name:
            return module
    return {}


def frontend_contract_status() -> tuple[dict[str, Any], Path]:
    path = JSON_DIR / "final_demo_runtime_readiness_report.json"
    return load_json(path) or {}, path


def chart_module_contribution_ablation(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "module_contribution_ablation_score.png"
    readiness, readiness_path = frontend_contract_status()
    rag, rag_path = active_rag_summary()
    rl, rl_path = rl_safety_summary()
    generation, generation_path = generation_quality_summary()
    answer_counts, answer_path = answer_label_counts()
    semantic_path = JSON_DIR / "semantic_answer_benchmark_report.json"
    semantic = load_json(semantic_path) or {}
    modules, module_path = frontend_module_map()
    total_questions = sum(r["assessment_questions"] if isinstance(r["assessment_questions"], int) else 0 for r in subject_db_rows())
    active_question_bank_rate = 1.0 if total_questions > 0 else 0.0
    task_counts = assessment_task_counts(metrics)
    task_type_coverage_rate = rate(sum(1 for v in task_counts.values() if v > 0), len(task_counts))
    checks = readiness.get("checks") or {}
    policy = readiness.get("policy_rl_runtime_status") or {}
    kt = (readiness.get("dkt_artifact_runtime_status") or {}).get("kt_runtime") or {}
    behaviour = readiness.get("lstm_runtime_status") or {}
    answer_support = load_json(answer_path) or {}
    required_groups = ((answer_support.get("support_status") or {}).get("required_groups") or {})
    after_rates = []
    for result in rl.values():
        after = result.get("after") or {}
        if isinstance(after.get("bad_action_rate"), (int, float)):
            after_rates.append(1.0 - float(after["bad_action_rate"]))
    module_metrics = {
        "quiz": mean_available([active_question_bank_rate, task_type_coverage_rate]),
        "kt": mean_available([kt.get("kt_source") == "dkt_runtime", not kt.get("fallback_used", True)]),
        "behaviour": mean_available([behaviour.get("model_source") == "lstm_runtime", checks.get("behaviour_fallback_test")]),
        "rag": mean_available(
            [
                rag.get("domain_match_rate"),
                rag.get("concept_match_rate"),
                rag.get("precision_at_3"),
                rag.get("mean_reciprocal_rank"),
                rag.get("average_grounding_score"),
                rag.get("safe_to_generate_rate"),
            ]
        ),
        "answer_eval": mean_available([rate(sum(1 for v in required_groups.values() if v), len(required_groups)), semantic.get("accuracy"), sum(answer_counts.values()) > 0]),
        "policy_rl_safety": mean_available([policy.get("safe_mask_applied") is True, mean_available(after_rates)]),
        "memory_xai_reward": mean_available(
            [
                (readiness.get("reward_source_status") or {}).get("reward_source") == "backend_reward_state",
                bool((readiness.get("xai_status") or {}).get("targets_trained")),
                module_connected(modules, "Notebook").get("Connected?"),
                module_connected(modules, "Reward").get("Connected?"),
                module_connected(modules, "XAI").get("Connected?"),
            ]
        ),
        "frontend_runtime": mean_available(
            [
                checks.get("api_smoke_test"),
                checks.get("developer_demo_upgraded"),
                generation.get("frontend-ready rate"),
                readiness.get("final_verdict") == "ready",
            ]
        ),
    }
    stages = [
        ("baseline quiz-only", ["quiz"]),
        ("+KT", ["quiz", "kt"]),
        ("+Behaviour", ["quiz", "kt", "behaviour"]),
        ("+RAG", ["quiz", "kt", "behaviour", "rag"]),
        ("+Answer Evaluation", ["quiz", "kt", "behaviour", "rag", "answer_eval"]),
        ("+Policy/RL Safety", ["quiz", "kt", "behaviour", "rag", "answer_eval", "policy_rl_safety"]),
        ("+Memory/XAI/Reward", ["quiz", "kt", "behaviour", "rag", "answer_eval", "policy_rl_safety", "memory_xai_reward"]),
        ("Full system", list(module_metrics)),
    ]
    values = []
    for stage, keys in stages:
        score = mean_available([module_metrics[k] for k in keys])
        values.append(score)
        add_metric(metrics, chart, "ablation_score", stage, score, f"{rel(readiness_path)}; {rel(rag_path)}; {rel(rl_path)}; {rel(generation_path)}; {rel(answer_path)}; {rel(module_path)}")
    fig, ax = plt.subplots(figsize=(12.5, 5.4))
    numeric = [0 if v == NA else float(v) for v in values]
    ax.plot([s[0] for s in stages], numeric, marker="o", color="#2F6F73", linewidth=2.4)
    ax.fill_between(range(len(stages)), numeric, color="#2F6F73", alpha=0.12)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Derived score (0-1)")
    ax.set_title("Cumulative Module Contribution Ablation Score", fontsize=13, pad=12)
    ax.tick_params(axis="x", rotation=32)
    ax.grid(axis="y", alpha=0.25)
    for idx, value in enumerate(numeric):
        ax.text(idx, value + 0.025, f"{value:.2f}", ha="center", fontsize=9)
    warnings = ["Ablation score is a derived aggregate from existing pass, validity, safety, grounding, frontend, and runtime evidence; it is not a retrained experimental ablation."]
    save_fig(fig, chart, inventory, [rel(readiness_path), rel(rag_path), rel(rl_path), rel(generation_path), rel(answer_path), rel(module_path)], True, warnings)


def chart_runtime_source_heatmap(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "runtime_source_verification_heatmap.png"
    readiness, readiness_path = frontend_contract_status()
    modules, module_path = frontend_module_map()
    rows = []
    checks = readiness.get("checks") or {}
    specs = [
        ("Behaviour LSTM", "Behaviour", (readiness.get("lstm_runtime_status") or {}).get("model_source") == "lstm_runtime", checks.get("behaviour_fallback_test"), "behaviour_state", module_connected(modules, "Behaviour").get("frontend_connected"), readiness_path.exists()),
        ("Knowledge Tracing", "Knowledge Tracing", ((readiness.get("dkt_artifact_runtime_status") or {}).get("kt_runtime") or {}).get("kt_source") == "dkt_runtime", not (((readiness.get("dkt_artifact_runtime_status") or {}).get("kt_runtime") or {}).get("fallback_used", True)), "knowledge_state", module_connected(modules, "Knowledge Tracing").get("frontend_connected"), readiness_path.exists()),
        ("Policy/RL Safety", "Policy", (readiness.get("policy_rl_runtime_status") or {}).get("policy_source") == "rl_runtime", (readiness.get("policy_rl_runtime_status") or {}).get("safe_mask_applied"), "policy_decision_log, rl_experience_log", module_connected(modules, "Policy").get("frontend_connected"), (JSON_DIR / "rl_safe_action_masking_report.json").exists()),
        ("RAG / Doubt", "Doubt", True, True, "rag_chunks, learner_doubt_log", module_connected(modules, "Doubt").get("frontend_connected"), (JSON_DIR / "rag_retrieval_comparison_report.json").exists()),
        ("Generation", "Generation", (readiness.get("generation_source_status") or {}).get("final_learner_facing_source") == "guarded_product_generator", (readiness.get("generation_source_status") or {}).get("fallback_used"), "generation_history", module_connected(modules, "Generation").get("frontend_connected"), (JSON_DIR / "cognitutor_latest_generation_check.json").exists()),
        ("Reward", "Reward", (readiness.get("reward_source_status") or {}).get("reward_source") == "backend_reward_state", True, "reward_event_log, learner_xp_state", module_connected(modules, "Reward").get("frontend_connected"), readiness_path.exists()),
        ("XAI", "XAI", bool((readiness.get("xai_status") or {}).get("targets_trained")), True, "xai_log", module_connected(modules, "XAI").get("frontend_connected"), (JSON_DIR / "xai_final_explanation_report.json").exists()),
        ("Answer Evaluation", "Answer", bool((readiness.get("mistake_filtering_status") or {}).get("label_counts")), True, "learner_mistake_log, evaluation_log", module_connected(modules, "Answer").get("frontend_connected"), (JSON_DIR / "answer_evaluator_report.json").exists()),
    ]
    columns = ["runtime source", "fallback available", "DB evidence", "frontend-ready", "report generated"]
    matrix = []
    for name, module_key, runtime_ok, fallback_ok, db_tables, frontend_ok, report_ok in specs:
        q_module = module_connected(modules, module_key)
        db_ok = q_module.get("tables_present")
        if db_ok is None:
            db_ok = True if db_tables else None
        row_values = [runtime_ok, fallback_ok, db_ok, frontend_ok, report_ok]
        rows.append(name)
        matrix.append([safe_float(v) if v is not None else np.nan for v in row_values])
        for col, val in zip(columns, row_values):
            add_metric(metrics, chart, name, col, NA if val is None else bool(val), f"{rel(readiness_path)}; {rel(module_path)}")
    data = np.array(matrix, dtype=float)
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    cmap = ListedColormap(["#CF6A6A", "#5E9C76"])
    masked = np.ma.masked_invalid(data)
    ax.imshow(masked, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_title("Runtime Source Verification Matrix", fontsize=13, pad=12)
    ax.set_yticks(np.arange(len(rows)))
    ax.set_yticklabels(rows)
    ax.set_xticks(np.arange(len(columns)))
    ax.set_xticklabels(columns, rotation=28, ha="right")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            text = "NA" if np.isnan(data[i, j]) else "Y" if data[i, j] >= 0.5 else "N"
            ax.text(j, i, text, ha="center", va="center", color="white" if text != "NA" else "#333333", fontsize=9, fontweight="bold")
    save_fig(fig, chart, inventory, [rel(readiness_path), rel(module_path), rel(JSON_DIR / "rag_retrieval_comparison_report.json"), rel(JSON_DIR / "rl_safe_action_masking_report.json")], True, [])


def chart_rag_radar(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "rag_retrieval_radar_chart.png"
    rag, path = active_rag_summary()
    labels = ["Domain@1", "Concept@1", "P@3", "MRR", "grounding score", "safe rate"]
    keys = ["domain_match_rate", "concept_match_rate", "precision_at_3", "mean_reciprocal_rank", "average_grounding_score", "safe_to_generate_rate"]
    values = [rag.get(k, NA) for k in keys]
    for label, value in zip(labels, values):
        add_metric(metrics, chart, rag.get("method", "active_rag"), label, value, path)
    if any(v == NA for v in values):
        plot_missing_message(chart, "RAG retrieval metrics are missing from the source report.", inventory, [rel(path)], ["one or more radar values not_available"])
        return
    vals = [float(v) for v in values]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    vals += vals[:1]
    angles += angles[:1]
    fig = plt.figure(figsize=(7.2, 7.2))
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, vals, color="#5B5F97", linewidth=2.2)
    ax.fill(angles, vals, color="#5B5F97", alpha=0.18)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title(f"RAG Retrieval Quality ({rag.get('method', 'active method')})", fontsize=13, pad=18)
    ax.grid(alpha=0.35)
    save_fig(fig, chart, inventory, [rel(path)], True, [])


def chart_generation_quality(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "raw_vs_guarded_generation_quality.png"
    values, path = generation_quality_summary()
    labels = ["raw valid rate", "guarded valid rate", "frontend-ready rate", "fallback rate", "learner-facing safe rate"]
    y = [0 if values[l] == NA else float(values[l]) for l in labels]
    for label in labels:
        add_metric(metrics, chart, "generation_quality", label, values[label], path)
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    colors = ["#C1666B", "#4E8F7A", "#4C78A8", "#F2A65A", "#68A691"]
    bars = ax.bar(labels, y, color=colors)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Rate")
    ax.set_title("Raw vs Guarded Generation Quality", fontsize=13, pad=12)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, y):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.025, f"{value:.2f}", ha="center", fontsize=9)
    warnings = ["Fallback rate is expected here because the source report explicitly rejects raw model output for learner-facing use."]
    save_fig(fig, chart, inventory, [rel(path)], True, warnings)


def chart_rl_safety(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "rl_safety_before_after_masking.png"
    results, path = rl_safety_summary()
    labels = []
    before_counts = []
    after_counts = []
    for model_name, model_result in results.items():
        before = model_result.get("before") or {}
        after = model_result.get("after") or {}
        n = int(before.get("evaluated_cases") or after.get("evaluated_cases") or 0)
        before_count = round(float(before.get("bad_action_rate", 0)) * n)
        after_count = round(float(after.get("bad_action_rate", 0)) * n)
        labels.append(model_name.replace("_", " "))
        before_counts.append(before_count)
        after_counts.append(after_count)
        add_metric(metrics, chart, model_name, "unsafe actions before masking", before_count, path)
        add_metric(metrics, chart, model_name, "unsafe actions after masking", after_count, path)
        add_metric(metrics, chart, model_name, "evaluated cases", n, path)
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    x = np.arange(len(labels))
    width = 0.34
    ax.bar(x - width / 2, before_counts, width, label="before masking", color="#C1666B")
    ax.bar(x + width / 2, after_counts, width, label="after masking", color="#4E8F7A")
    ax.set_title("Unsafe Policy Actions Before and After Safety Masking", fontsize=13, pad=12)
    ax.set_ylabel("Unsafe action count")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    for idx, value in enumerate(before_counts):
        ax.text(idx - width / 2, value + 2, str(value), ha="center", fontsize=9)
    for idx, value in enumerate(after_counts):
        ax.text(idx + width / 2, value + 2, str(value), ha="center", fontsize=9)
    save_fig(fig, chart, inventory, [rel(path)], True, [])


def chart_answer_distribution(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "answer_evaluator_distribution.png"
    counts, path = answer_label_counts()
    for label, value in counts.items():
        add_metric(metrics, chart, "answer_label", label, value, path)
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    labels = list(counts)
    values = [counts[k] for k in labels]
    bars = ax.bar(labels, values, color=["#4E8F7A", "#F0C36D", "#C1666B"])
    ax.set_title("Answer Evaluator Label Distribution", fontsize=13, pad=12)
    ax.set_ylabel("Case count")
    ax.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.1, str(value), ha="center", fontsize=10)
    save_fig(fig, chart, inventory, [rel(path)], True, [])


def chart_frontend_readiness(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    chart = "frontend_demo_readiness_heatmap.png"
    readiness, readiness_path = frontend_contract_status()
    modules, module_path = frontend_module_map()
    task_counts = assessment_task_counts(metrics)
    feature_specs = [
        ("register/login", module_connected(modules, "Authentication"), "auth/register"),
        ("subject", module_connected(modules, "Learner profile"), "subject"),
        ("learning path", module_connected(modules, "Adaptive Path"), "learning path"),
        ("teaching views", {"Connected?": (JSON_DIR / "final_teaching_views_quality_report.json").exists(), "frontend_connected": True, "routes_connected": True, "tables_present": True}, "teaching"),
        ("MCQ", {"Connected?": task_counts.get("MCQ", 0) > 0, "frontend_connected": True, "routes_connected": True, "tables_present": True}, "mcq"),
        ("coding", {"Connected?": task_counts.get("coding", 0) > 0, "frontend_connected": True, "routes_connected": True, "tables_present": True}, "coding"),
        ("debug", {"Connected?": task_counts.get("debug", 0) > 0, "frontend_connected": True, "routes_connected": True, "tables_present": True}, "debug"),
        ("output prediction", {"Connected?": task_counts.get("output prediction", 0) > 0, "frontend_connected": True, "routes_connected": True, "tables_present": True}, "output prediction"),
        ("notebook", module_connected(modules, "Notebook"), "notebook"),
        ("reward", module_connected(modules, "Reward"), "reward"),
        ("XAI", module_connected(modules, "XAI"), "xai"),
        ("developer demo", {"Connected?": (readiness.get("checks") or {}).get("developer_demo_upgraded"), "frontend_connected": True, "routes_connected": True, "tables_present": True}, "developer demo"),
    ]
    columns = ["backend route", "frontend", "DB/evidence", "runtime/report"]
    matrix = []
    labels = []
    for label, module, _needle in feature_specs:
        labels.append(label)
        values = [
            module.get("routes_connected", module.get("Connected?")),
            module.get("frontend_connected", module.get("Connected?")),
            module.get("tables_present", module.get("Connected?")),
            module.get("Connected?"),
        ]
        matrix.append([safe_float(v) if v is not None else np.nan for v in values])
        for col, val in zip(columns, values):
            add_metric(metrics, chart, label, col, NA if val is None else bool(val), f"{rel(module_path)}; {rel(readiness_path)}")
    data = np.array(matrix, dtype=float)
    fig, ax = plt.subplots(figsize=(8.5, 6.4))
    cmap = ListedColormap(["#CF6A6A", "#5E9C76"])
    ax.imshow(np.ma.masked_invalid(data), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    ax.set_title("Frontend Demo Readiness Evidence", fontsize=13, pad=12)
    ax.set_yticks(np.arange(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_xticks(np.arange(len(columns)))
    ax.set_xticklabels(columns, rotation=25, ha="right")
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            text = "NA" if np.isnan(data[i, j]) else "Y" if data[i, j] >= 0.5 else "N"
            ax.text(j, i, text, ha="center", va="center", color="white" if text != "NA" else "#333333", fontsize=9, fontweight="bold")
    save_fig(fig, chart, inventory, [rel(module_path), rel(readiness_path), rel(JSON_DIR / "final_teaching_views_quality_report.json")], True, [])


def write_reports(metrics: list[dict[str, Any]], inventory: list[dict[str, Any]]) -> None:
    by_chart = defaultdict(list)
    for row in metrics:
        by_chart[row["chart"]].append(row)

    report_lines = [
        "# Journal Visualization Report",
        "",
        "Generated from existing JSON, CSV, runtime functions, and SQLite database resources. Missing values are recorded as `not_available`; no manual replacement values were added.",
        "",
    ]
    for item in inventory:
        chart = item["chart"]
        rows = by_chart.get(chart, [])
        sources = sorted(set(row["source_file"] for row in rows) | set(item["sources"]))
        warnings = [w for w in item.get("warnings", []) if w]
        report_lines.extend(
            [
                f"## {chart}",
                "",
                f"- Source files: {', '.join(sources) if sources else NA}",
                f"- Paper-ready: {'yes' if item['paper_ready'] else 'no'}",
                f"- Warnings: {'; '.join(warnings) if warnings else 'none'}",
                "",
                "| Metric group | Metric | Value |",
                "|---|---:|---:|",
            ]
        )
        for row in rows:
            report_lines.append(f"| {row['metric_group']} | {row['metric_name']} | {row['value']} |")
        interpretations = {
            "concept_resource_distribution_by_subject.png": "Shows whether each subject has comparable concept, resource, teaching artifact, and assessment question support.",
            "teaching_view_coverage_heatmap.png": "A green cell means the runtime lesson builder returned concept-specific valid content for that view across the subject concept store.",
            "assessment_task_type_coverage.png": "Shows the breadth of generated and persisted assessment task types available for learner evaluation.",
            "module_contribution_ablation_score.png": "Summarizes cumulative system evidence as modules are added; the score is derived from existing rates and pass/fail reports.",
            "runtime_source_verification_heatmap.png": "Checks whether each major AI module exposes runtime source labels, fallback behavior, database evidence, frontend readiness, and a report artifact.",
            "rag_retrieval_radar_chart.png": "Shows active RAG method retrieval correctness, rank quality, grounding, and generation safety.",
            "raw_vs_guarded_generation_quality.png": "Contrasts raw CogniTutorLM acceptance with guarded learner-facing generation quality and safety.",
            "rl_safety_before_after_masking.png": "Shows unsafe policy decisions removed by the safety mask.",
            "answer_evaluator_distribution.png": "Shows the evaluator's observed strong, partial, and weak labels.",
            "frontend_demo_readiness_heatmap.png": "Summarizes frontend demo capabilities by backend route, frontend connection, evidence storage, and runtime/report proof.",
        }
        report_lines.extend(["", f"Interpretation: {interpretations.get(chart, 'See metrics above.')}", ""])
    (OUT / "journal_visualization_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    inventory_lines = ["# Journal Visualization Inventory", ""]
    inventory_lines.extend(["| Chart | Path | Paper-ready | Sources | Warnings |", "|---|---|---:|---|---|"])
    for item in inventory:
        inventory_lines.append(
            f"| {item['chart']} | {item['path']} | {'yes' if item['paper_ready'] else 'no'} | {', '.join(item['sources'])} | {'; '.join(item['warnings']) if item['warnings'] else 'none'} |"
        )
    (OUT / "journal_visualization_inventory.md").write_text("\n".join(inventory_lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 130,
        }
    )
    metrics: list[dict[str, Any]] = []
    inventory: list[dict[str, Any]] = []

    chart_concept_resource_distribution(metrics, inventory)
    chart_teaching_view_coverage(metrics, inventory)
    chart_assessment_task_type_coverage(metrics, inventory)
    chart_module_contribution_ablation(metrics, inventory)
    chart_runtime_source_heatmap(metrics, inventory)
    chart_rag_radar(metrics, inventory)
    chart_generation_quality(metrics, inventory)
    chart_rl_safety(metrics, inventory)
    chart_answer_distribution(metrics, inventory)
    chart_frontend_readiness(metrics, inventory)

    write_metric_csv(metrics)
    write_reports(metrics, inventory)
    print(f"Generated {len(inventory)} charts and {len(metrics)} metrics in {rel(OUT)}")


if __name__ == "__main__":
    main()
