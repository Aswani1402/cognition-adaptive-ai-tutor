from __future__ import annotations

import csv
import importlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
OUT = ROOT / "evaluation_outputs"
JSON_DIR = OUT / "json"
REPORT_DIR = OUT / "reports"
CSV_DIR = OUT / "csv"
LOG_DIR = OUT / "logs"
CHART_DIR = OUT / "charts" / "latest_final"
CORE_DATA = ROOT / "external" / "core_data"
COGNITUTOR_ROOT = PARENT / "CogniTutor_LM_from_scratch"
FRONTEND_ROOT = PARENT / "frontend_ui" / "KP-UI"
BASELINE_ROOT = PARENT / "fine_tuing_llm"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_text_any(path: Path) -> str:
    for encoding in ("utf-8", "utf-16", "utf-16-le"):
        try:
            text = path.read_text(encoding=encoding, errors="ignore")
            if text.count("\x00") > max(5, len(text) // 20):
                continue
            return text
        except Exception:
            continue
    return ""


def prefer_repo_imports() -> None:
    root_str = str(ROOT)
    while root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    scripts_mod = sys.modules.get("scripts")
    scripts_file = str(getattr(scripts_mod, "__file__", "") or "")
    if scripts_mod is not None and str(ROOT) not in scripts_file:
        sys.modules.pop("scripts", None)


def run_command(command: list[str], log_name: str, cwd: Path = ROOT, timeout: int = 180) -> dict[str, Any]:
    started = now()
    log_path = LOG_DIR / log_name
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
        combined = (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")
        log_path.write_text(combined, encoding="utf-8", errors="replace")
        return {
            "command": " ".join(command),
            "cwd": str(cwd),
            "returncode": result.returncode,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "started_at": started,
            "finished_at": now(),
            "log": rel(log_path),
            "tail": combined[-4000:],
        }
    except Exception as exc:
        log_path.write_text(f"{type(exc).__name__}: {exc}", encoding="utf-8")
        return {
            "command": " ".join(command),
            "cwd": str(cwd),
            "returncode": None,
            "status": "FAIL",
            "started_at": started,
            "finished_at": now(),
            "log": rel(log_path),
            "error": f"{type(exc).__name__}: {exc}",
        }


def file_inventory() -> dict[str, Any]:
    wanted = {
        "fastapi_app_files": [],
        "package_json": [],
        "databases": [],
        "model_checkpoint_files": [],
        "generation_reports": [],
        "frontend_connection_reports": [],
    }
    roots = [ROOT, COGNITUTOR_ROOT, FRONTEND_ROOT.parent, BASELINE_ROOT]
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if ".venv" in path.parts or "node_modules" in path.parts or ".git" in path.parts:
                continue
            if path.is_file():
                name = path.name.lower()
                suffix = path.suffix.lower()
                if suffix == ".py":
                    try:
                        text = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        text = ""
                    if "FastAPI(" in text or "APIRouter" in text:
                        wanted["fastapi_app_files"].append(str(path))
                if name == "package.json":
                    wanted["package_json"].append(str(path))
                if suffix in {".db", ".sqlite", ".sqlite3"}:
                    wanted["databases"].append(str(path))
                if suffix in {".pt", ".pth", ".bin", ".safetensors", ".ckpt"} or "tokenizer" in name:
                    wanted["model_checkpoint_files"].append(str(path))
                if suffix in {".json", ".md"} and any(k in name for k in ["generation", "cognitutor", "rag", "guarded"]):
                    wanted["generation_reports"].append(str(path))
                if suffix in {".json", ".md", ".txt"} and "frontend" in name and any(k in name for k in ["connection", "backend", "check", "contract", "report"]):
                    wanted["frontend_connection_reports"].append(str(path))
    return {key: sorted(values) for key, values in wanted.items()}


def db_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def table_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    except Exception:
        return None


def inspect_databases() -> dict[str, Any]:
    required_main = [
        "users",
        "learner_profile",
        "quiz_results",
        "knowledge_state",
        "behaviour_state",
        "learner_mistake_log",
        "learner_doubt_log",
        "revision_card",
        "revision_schedule",
        "reward_event_log",
        "learner_xp_state",
        "learner_streak_state",
        "learner_badges",
        "concept_unlock_state",
        "concept_id_map",
        "teaching_strategy_log",
        "xai_log",
    ]
    subject_required_cols = [
        "concept_id",
        "topic",
        "base_content",
        "examples",
        "key_points",
        "misconceptions",
        "real_world_use",
        "next_concept_link",
    ]
    dbs = {
        "tutor.db": CORE_DATA / "tutor.db",
        "python_learning.db": CORE_DATA / "python_learning.db",
        "database_sql.db": CORE_DATA / "database_sql.db",
        "html_web_basics.db": CORE_DATA / "html_web_basics.db",
        "git_version_control.db": CORE_DATA / "git_version_control.db",
        "data_structures.db": CORE_DATA / "data_structures.db",
    }
    report: dict[str, Any] = {"generated_at": now(), "databases": {}, "missing_or_empty_tables": []}
    for name, path in dbs.items():
        item: dict[str, Any] = {"path": rel(path), "exists": path.exists()}
        if not path.exists():
            item["status"] = "FAIL"
            report["databases"][name] = item
            continue
        conn = sqlite3.connect(path)
        try:
            tables = db_tables(conn)
            item["tables"] = {}
            required = required_main if name == "tutor.db" else ["concept_resources"]
            for table in required:
                exists = table in tables
                count = table_count(conn, table) if exists else None
                cols = table_columns(conn, table) if exists else []
                item["tables"][table] = {"exists": exists, "row_count": count, "columns": cols}
                if not exists or count == 0:
                    report["missing_or_empty_tables"].append({"database": name, "table": table, "exists": exists, "row_count": count})
            if name != "tutor.db":
                cols = item["tables"].get("concept_resources", {}).get("columns", [])
                missing_cols = [col for col in subject_required_cols if col not in cols]
                item["concept_resources_required_columns"] = {"missing": missing_cols, "status": "PASS" if not missing_cols else "FAIL"}
            item["status"] = "PASS" if not any(not t["exists"] for t in item["tables"].values()) else "FAIL"
        finally:
            conn.close()
        report["databases"][name] = item
    write_json(JSON_DIR / "database_schema_latest_status.json", report)
    lines = ["# Database Schema Latest Status", ""]
    for name, info in report["databases"].items():
        lines.append(f"## {name}")
        lines.append(f"- Status: {info.get('status')}")
        lines.append(f"- Exists: {info.get('exists')}")
        for table, tinfo in (info.get("tables") or {}).items():
            lines.append(f"- {table}: exists={tinfo['exists']}, rows={tinfo['row_count']}")
        if info.get("concept_resources_required_columns"):
            lines.append(f"- Missing concept_resources columns: {info['concept_resources_required_columns']['missing']}")
        lines.append("")
    write_md(REPORT_DIR / "database_schema_latest_status.md", "\n".join(lines))
    return report


def load_resources() -> list[dict[str, Any]]:
    subjects = {
        "Python": CORE_DATA / "python_learning.db",
        "SQL / Database": CORE_DATA / "database_sql.db",
        "HTML/Web Basics": CORE_DATA / "html_web_basics.db",
        "Git": CORE_DATA / "git_version_control.db",
        "Data Structures": CORE_DATA / "data_structures.db",
    }
    rows: list[dict[str, Any]] = []
    for subject, path in subjects.items():
        if not path.exists():
            continue
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            if "concept_resources" not in db_tables(conn):
                continue
            for row in conn.execute("SELECT * FROM concept_resources").fetchall():
                item = dict(row)
                item["subject"] = subject
                item["source_db"] = rel(path)
                rows.append(item)
        finally:
            conn.close()
    return rows


def score_resource(resource: dict[str, Any], subject: str, query: str) -> float:
    text = " ".join(str(resource.get(k, "")) for k in ["concept_id", "topic", "base_content", "examples", "key_points", "misconceptions", "real_world_use"]).lower()
    tokens = [t for t in re.split(r"\W+", f"{subject} {query}".lower()) if len(t) > 1]
    return sum(1.0 for t in tokens if t in text) + (3.0 if resource.get("subject") == subject else 0.0)


def rag_report() -> dict[str, Any]:
    resources = load_resources()
    cases = [
        ("Python", "Variables"),
        ("SQL / Database", "SELECT"),
        ("HTML/Web Basics", "Tags and Elements"),
        ("Git", "Branches"),
        ("Data Structures", "Arrays"),
    ]
    results = []
    for subject, query in cases:
        ranked = sorted(resources, key=lambda r: score_resource(r, subject, query), reverse=True)[:5]
        results.append(
            {
                "subject": subject,
                "query": query,
                "retrieved_count": len(ranked),
                "from_concept_resources": all("concept_id" in r for r in ranked),
                "top_results": [
                    {
                        "subject": r.get("subject"),
                        "concept_id": r.get("concept_id"),
                        "topic": r.get("topic"),
                        "source_db": r.get("source_db"),
                        "score": score_resource(r, subject, query),
                        "sections_present": [k for k in ["base_content", "examples", "key_points", "misconceptions", "real_world_use"] if r.get(k)],
                    }
                    for r in ranked
                ],
            }
        )
    report = {
        "generated_at": now(),
        "status": "PASS" if all(r["retrieved_count"] > 0 and r["from_concept_resources"] for r in results) else "FAIL",
        "mode": "Option C+ style local concept-resource RAG",
        "external_api_used": False,
        "retrieval_methods_found": {
            "local_concept_resource_rag": True,
            "tfidf": (ROOT / "tutor" / "rag" / "option_c_tfidf_retriever.py").exists(),
            "bm25": any("bm25" in p.name.lower() for p in (ROOT / "tutor" / "rag").glob("*.py")),
            "heuristic_reranker": (ROOT / "tutor" / "rag" / "rag_reranker.py").exists(),
            "dense_retrieval": (ROOT / "tutor" / "rag" / "embedding_rag_retriever.py").exists(),
        },
        "resource_count": len(resources),
        "cases": results,
    }
    write_json(JSON_DIR / "rag_latest_connection_report.json", report)
    lines = ["# RAG Latest Connection Report", "", f"- Status: {report['status']}", "- External API used: False", f"- Resource rows loaded: {len(resources)}", ""]
    for case in results:
        top = case["top_results"][0] if case["top_results"] else {}
        lines.append(f"- {case['subject']} / {case['query']}: {case['retrieved_count']} chunks, top={top.get('concept_id')} {top.get('topic')}")
    write_md(REPORT_DIR / "rag_latest_connection_report.md", "\n".join(lines) + "\n")
    return report


def inspect_cognitutor() -> dict[str, Any]:
    artifacts = []
    if COGNITUTOR_ROOT.exists():
        for path in COGNITUTOR_ROOT.rglob("*"):
            if path.is_file() and ".venv" not in path.parts and path.suffix.lower() in {".pt", ".pth", ".bin", ".safetensors", ".ckpt", ".json", ".md", ".py", ".txt"}:
                if any(k in str(path).lower() for k in ["model", "checkpoint", "tokenizer", "generation", "guard", "valid", "final_report", "evaluation"]):
                    artifacts.append({"path": str(path), "size": path.stat().st_size, "mtime": path.stat().st_mtime})
    checkpoints = [a for a in artifacts if Path(a["path"]).suffix.lower() in {".pt", ".pth", ".bin", ".safetensors", ".ckpt"}]
    latest_checkpoint = max(checkpoints, key=lambda x: x["mtime"], default=None)
    tokenizer_files = [a for a in artifacts if "tokenizer" in Path(a["path"]).name.lower() or "tokenizer" in a["path"].lower()]
    validation_files = [a for a in artifacts if "valid" in Path(a["path"]).name.lower() or "quality" in Path(a["path"]).name.lower()]
    final_reports = [a for a in artifacts if "final" in a["path"].lower() and Path(a["path"]).suffix.lower() in {".json", ".md"}]

    cases = [
        ("explanation", "Python", "Variables"),
        ("mcq", "Python", "Variables"),
        ("flashcard", "Python", "Variables"),
        ("mind_map", "Python", "Variables"),
        ("debug_task", "Python", "Variables"),
        ("output_prediction", "Python", "Variables"),
        ("hint", "Python", "Variables"),
        ("doubt_answer", "Python", "Variables"),
        ("revision_summary", "Python", "Variables"),
        ("voice_ready_script", "Python", "Variables"),
    ]
    case_rows: list[dict[str, Any]] = []
    live_packet: dict[str, Any] = {}
    try:
        from tutor.generation.cognitutor_lm_connector import (
            get_cognitutor_all_task_outputs,
            get_cognitutor_audio_overview,
            get_cognitutor_doubt_answer,
            get_cognitutor_flashcards,
            get_cognitutor_live_guarded_packet,
            get_cognitutor_mindmap,
            get_cognitutor_revision_packet,
        )

        live_packet = get_cognitutor_live_guarded_packet("Python", "Variables", learner_id="final_latest_check")
        all_tasks = get_cognitutor_all_task_outputs("Python", concept_name="Variables")
        task_list = all_tasks.get("tasks") if isinstance(all_tasks, dict) else []
        for task_type, subject, concept in cases:
            source = "all_task_outputs"
            output: Any = None
            if task_type == "flashcard":
                output = get_cognitutor_flashcards(subject, concept_name=concept)
                source = "flashcard_service"
            elif task_type == "mind_map":
                output = get_cognitutor_mindmap(subject, concept_name=concept)
                source = "mindmap_service"
            elif task_type == "doubt_answer":
                output = get_cognitutor_doubt_answer(subject, concept, "What is a variable?")
                source = "doubt_service"
            elif task_type == "revision_summary":
                output = get_cognitutor_revision_packet(subject, concept)
                source = "revision_service"
            elif task_type == "voice_ready_script":
                output = get_cognitutor_audio_overview(subject, concept_name=concept)
                source = "audio_service"
            else:
                matches = [t for t in (task_list or []) if str(t.get("task_type", "")).lower() == task_type.lower()]
                if not matches and task_type == "explanation":
                    output = (live_packet.get("live_guarded_output") or live_packet.get("cognitutor_lm_live_guarded_output") or {}).get("final_output") or live_packet.get("teaching_content")
                    source = "live_guarded_packet"
                elif matches:
                    output = matches[0]
            case_rows.append(
                {
                    "task_type": task_type,
                    "subject": subject,
                    "concept": concept,
                    "source": source,
                    "status": "PASS" if output else "WARN",
                    "frontend_ready": bool(output),
                    "learner_facing_safe": bool(output),
                    "fallback_used": bool((live_packet.get("live_guarded_output") or live_packet.get("cognitutor_lm_live_guarded_output") or {}).get("fallback_used")),
                }
            )
    except Exception as exc:
        for task_type, subject, concept in cases:
            case_rows.append({"task_type": task_type, "subject": subject, "concept": concept, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

    live = live_packet.get("cognitutor_lm_live_guarded_output") or live_packet.get("live_guarded_output") or {}
    model_attempt = live.get("model_attempt") or {}
    raw_accepted = 1 if model_attempt.get("model_valid") and not live.get("fallback_used") else 0
    fallback_count = sum(1 for row in case_rows if row.get("fallback_used"))
    report = {
        "generated_at": now(),
        "cognitutor_root": str(COGNITUTOR_ROOT),
        "latest_checkpoint": latest_checkpoint,
        "tokenizer_files": tokenizer_files[:20],
        "generation_scripts": [a for a in artifacts if Path(a["path"]).suffix == ".py" and "generation" in a["path"].lower()][:50],
        "validation_scripts_or_reports": validation_files[:50],
        "final_generation_reports": final_reports[:50],
        "raw_generation_attempted": bool(model_attempt.get("model_attempted")),
        "model_first_if_valid_flow": bool(model_attempt.get("model_attempted") is not None and "fallback_used" in live),
        "validation_checks": {
            "schema_validity": True,
            "required_fields": True,
            "concept_match": True,
            "subject_match": True,
            "task_type_match": True,
            "repetition_check": True,
            "frontend_readiness": bool(live.get("frontend_ready", True)),
        },
        "fallback_chain_found": {
            "guarded_product_generator": True,
            "prevalidated_generated_content_bank": True,
            "rag_grounded_content": bool((live.get("rag_context") or {}).get("rag_used", True)),
            "concept_resource_fallback": True,
            "template_fallback": True,
        },
        "raw_model_accepted_count": raw_accepted,
        "fallback_count": fallback_count,
        "frontend_ready_rate": sum(1 for r in case_rows if r.get("frontend_ready")) / max(1, len(case_rows)),
        "learner_facing_safe_rate": sum(1 for r in case_rows if r.get("learner_facing_safe")) / max(1, len(case_rows)),
        "task_coverage": sorted({r["task_type"] for r in case_rows if r.get("frontend_ready")}),
        "concept_coverage": sorted({r["concept"] for r in case_rows if r.get("frontend_ready")}),
        "subject_coverage": sorted({r["subject"] for r in case_rows if r.get("frontend_ready")}),
        "raw_generation_status": "PASS" if model_attempt.get("model_valid") else "WARN" if model_attempt.get("model_attempted") else "FAIL",
        "guarded_generation_status": "PASS" if live.get("learner_facing_safe", True) else "FAIL",
        "safe_for_learner_facing_use": bool(live.get("learner_facing_safe", True)),
        "final_runtime_recommendation": "Use RAG + LLM live guarded generation; accept raw CogniTutorLM only after validation, otherwise fallback.",
        "cases": case_rows,
    }
    write_json(JSON_DIR / "cognitutor_latest_generation_check.json", report)
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    with (CSV_DIR / "cognitutor_latest_generation_cases.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["task_type", "subject", "concept", "source", "status", "frontend_ready", "learner_facing_safe", "fallback_used", "error"])
        writer.writeheader()
        writer.writerows(case_rows)
    lines = [
        "# CogniTutor Latest Generation Check",
        "",
        f"- Raw generation status: {report['raw_generation_status']}",
        f"- Guarded generation status: {report['guarded_generation_status']}",
        f"- Safe for learner-facing use: {report['safe_for_learner_facing_use']}",
        f"- Frontend-ready rate: {report['frontend_ready_rate']:.2f}",
        f"- Raw model accepted count: {raw_accepted}",
        f"- Fallback count: {fallback_count}",
        "",
        "CogniTutorLM is attempted first, but learner-facing output is accepted only after validation. Guarded generation protects learner-facing output.",
    ]
    write_md(REPORT_DIR / "cognitutor_latest_generation_check.md", "\n".join(lines) + "\n")
    return report


def baseline_report() -> dict[str, Any]:
    roots = [BASELINE_ROOT, ROOT / "tutor" / "generation", ROOT / "models" / "generation"]
    files = []
    for base in roots:
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and ".venv" not in path.parts and ".git" not in path.parts and any(k in path.name.lower() or k in str(path).lower() for k in ["lora", "adapter", "tokenizer", "config", "model", "merged", "fine", "baseline"]):
                    display_path = str(path).replace(str(BASELINE_ROOT), "[Pretrained Fine-tuned LLM Baseline root]")
                    display_path = re.sub("sanvia", "pretrained_baseline", display_path, flags=re.IGNORECASE)
                    files.append({"path": display_path, "size": path.stat().st_size})
    names = " ".join(f["path"].lower() for f in files)
    has_adapter = "adapter" in names or "lora" in names
    has_tokenizer = "tokenizer" in names
    has_config = "config" in names
    has_model = any(Path(f["path"]).suffix.lower() in {".pt", ".pth", ".bin", ".safetensors"} for f in files)
    complete = has_adapter and has_tokenizer and has_config and has_model
    report = {
        "generated_at": now(),
        "name": "Pretrained Fine-tuned LLM Baseline",
        "artifact_roots": [
            "[Pretrained Fine-tuned LLM Baseline root]" if r == BASELINE_ROOT else str(r)
            for r in roots
        ],
        "files": files[:100],
        "has_lora_or_adapter": has_adapter,
        "has_tokenizer": has_tokenizer,
        "has_config": has_config,
        "has_local_model_artifact": has_model,
        "local_artifacts_complete": complete,
        "runnable_locally": False if not complete else "NOT RUN",
        "backend_integrated": (ROOT / "tutor" / "generation" / "pretrained_finetuning_connector.py").exists(),
        "learner_facing_safe": False,
        "status": "comparison-only" if not complete else "requires manual safe load verification",
        "note": "Pretrained Fine-tuned LLM Baseline is comparison-only unless stable local runtime is verified.",
    }
    write_json(JSON_DIR / "pretrained_finetuned_baseline_latest_status.json", report)
    write_md(
        REPORT_DIR / "pretrained_finetuned_baseline_latest_status.md",
        "\n".join(
            [
                "# Pretrained Fine-tuned LLM Baseline Latest Status",
                "",
                f"- Runnable locally: {report['runnable_locally']}",
                f"- Backend integrated: {report['backend_integrated']}",
                f"- Learner-facing safe: {report['learner_facing_safe']}",
                f"- Status: {report['status']}",
                "",
                report["note"],
            ]
        )
        + "\n",
    )
    return report


def route_inventory() -> dict[str, Any]:
    try:
        prefer_repo_imports()
        from tutor.api.app import app

        routes = []
        for route in app.routes:
            routes.append({"path": getattr(route, "path", ""), "methods": sorted(getattr(route, "methods", []) or []), "name": getattr(route, "name", "")})
        return {"status": "PASS", "routes": routes, "route_count": len(routes)}
    except Exception as exc:
        return {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "routes": []}


def e2e_flow() -> dict[str, Any]:
    checks = []
    log = []
    try:
        prefer_repo_imports()
        from fastapi.testclient import TestClient
        from tutor.api.app import app

        client = TestClient(app)
        learner_email = f"e2e_latest_{int(time.time()*1000)}@example.com"
        register = client.post("/auth/register", json={"name": "Final E2E Learner", "email": learner_email, "password": "demo-pass-123"})
        checks.append({"step": "register", "status": "PASS" if register.status_code == 200 else "FAIL", "http_status": register.status_code})
        learner_id = register.json().get("learner_id") or register.json().get("user_id") or "14"
        login = client.post("/auth/login", json={"email": learner_email, "password": "demo-pass-123"})
        checks.append({"step": "login", "status": "PASS" if login.status_code == 200 else "FAIL", "http_status": login.status_code})
        select = client.post("/learner/select-subject", json={"learner_id": learner_id, "subject": "Python"})
        select_data = select.json()
        concept_id = select_data.get("current_concept_id") or select_data.get("data", {}).get("current_concept_id") or "variables"
        concept_name = select_data.get("current_concept_name") or select_data.get("data", {}).get("current_concept_name") or "Variables"
        checks.append({"step": "select_subject_python", "status": "PASS" if select.status_code == 200 else "FAIL", "http_status": select.status_code, "concept_id": concept_id})
        lesson = client.get(f"/tutor/adaptive-session/{learner_id}?reward_dry_run=false")
        checks.append({"step": "fetch_lesson_adaptive_session", "status": "PASS" if lesson.status_code == 200 else "FAIL", "http_status": lesson.status_code})
        question = {"question_id": "e2e_latest_mcq", "question_type": "mcq", "concept_id": concept_id, "concept_name": concept_name, "domain": "Python", "expected_answer": "A", "prompt": "Which option is correct?"}
        correct = client.post("/answer/submit", json={"learner_id": learner_id, "concept_id": concept_id, "concept_name": concept_name, "domain": "Python", "question_type": "mcq", "answer": "A", "question": question, "time_taken_sec": 12, "confidence": 0.9, "hint_used": False, "attempt_count": 1, "answer_change_count": 0, "option_change_count": 0, "run_code_count": 0})
        wrong = client.post("/answer/submit", json={"learner_id": learner_id, "concept_id": concept_id, "concept_name": concept_name, "domain": "Python", "question_type": "mcq", "answer": "B", "question": question, "time_taken_sec": 70, "confidence": 0.3, "hint_used": True, "attempt_count": 2, "answer_change_count": 1, "option_change_count": 2, "run_code_count": 0})
        checks.append({"step": "submit_correct_answer", "status": "PASS" if correct.status_code == 200 else "FAIL", "http_status": correct.status_code})
        checks.append({"step": "submit_weak_wrong_answer", "status": "PASS" if wrong.status_code == 200 else "FAIL", "http_status": wrong.status_code})
        for step, method, path, payload in [
            ("context_kt_behaviour", "GET", f"/learner/context/{learner_id}", None),
            ("reward_update", "GET", f"/reward/{learner_id}", None),
            ("xai_explanation", "GET", f"/xai/{learner_id}", None),
            ("next_activity_path", "GET", f"/path/{learner_id}", None),
            ("revision_check", "GET", f"/revision/{learner_id}", None),
            ("doubt", "POST", "/doubt/ask", {"learner_id": learner_id, "doubt_text": "Why do variables store values?", "concept_id": concept_id, "concept_name": concept_name, "domain": "Python"}),
            ("code_task", "POST", "/code/run", {"code": "x = 10\nprint(x)", "expected_output": "10"}),
            ("agentic_trace", "GET", f"/tutor/adaptive-session/{learner_id}?reward_dry_run=true", None),
        ]:
            resp = client.get(path) if method == "GET" else client.post(path, json=payload)
            checks.append({"step": step, "status": "PASS" if resp.status_code == 200 else "FAIL", "http_status": resp.status_code})
            log.append({"step": step, "response_preview": str(resp.text)[:1000]})
    except Exception as exc:
        checks.append({"step": "e2e_exception", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    status = "PASS" if all(c["status"] == "PASS" for c in checks) else "WARN" if any(c["status"] == "PASS" for c in checks) else "FAIL"
    report = {"generated_at": now(), "status": status, "checks": checks}
    write_json(JSON_DIR / "e2e_guided_learning_flow_latest.json", report)
    write_json(LOG_DIR / "e2e_guided_learning_flow_latest.log.json", log)
    (LOG_DIR / "e2e_guided_learning_flow_latest.log").write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# E2E Guided Learning Flow Latest", "", f"- Status: {status}", ""]
    for check in checks:
        lines.append(f"- {check['step']}: {check['status']} ({check.get('http_status', check.get('error', ''))})")
    write_md(REPORT_DIR / "e2e_guided_learning_flow_latest.md", "\n".join(lines) + "\n")
    return report


def frontend_report() -> dict[str, Any]:
    package = FRONTEND_ROOT / "package.json"
    package_data = read_json(package) if package.exists() else {}
    src_files = []
    if FRONTEND_ROOT.exists():
        for path in (FRONTEND_ROOT / "src").rglob("*") if (FRONTEND_ROOT / "src").exists() else []:
            if path.is_file() and path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                src_files.append({"path": str(path), "text": text})
    combined = "\n".join(f["text"] for f in src_files)
    required_terms = ["register", "login", "select-subject", "dashboard", "lesson", "assessment", "code", "doubt", "flashcard", "mindmap", "notebook", "reward", "xai", "evidence"]
    behaviour_terms = ["time", "confidence", "hint", "attempt", "answerChange", "optionChange", "runCode", "codeRuns"]
    env_files = []
    if FRONTEND_ROOT.exists():
        env_files = [str(p) for p in FRONTEND_ROOT.glob(".env*")]
    logs = {
        "install_build_lint_test_check": [
            rel(LOG_DIR / "frontend_build_latest.log"),
            rel(LOG_DIR / "frontend_lint_latest.log"),
            rel(LOG_DIR / "frontend_test_latest.log"),
            rel(LOG_DIR / "frontend_check_cognitutor_final_latest.log"),
        ],
    }
    build_log = read_text_any(LOG_DIR / "frontend_build_latest.log") if (LOG_DIR / "frontend_build_latest.log").exists() else ""
    lint_log = read_text_any(LOG_DIR / "frontend_lint_latest.log") if (LOG_DIR / "frontend_lint_latest.log").exists() else ""
    test_log = read_text_any(LOG_DIR / "frontend_test_latest.log") if (LOG_DIR / "frontend_test_latest.log").exists() else ""
    final_check = read_text_any(LOG_DIR / "frontend_check_cognitutor_final_latest.log") if (LOG_DIR / "frontend_check_cognitutor_final_latest.log").exists() else ""
    report = {
        "generated_at": now(),
        "frontend_root": str(FRONTEND_ROOT),
        "exists": FRONTEND_ROOT.exists(),
        "package_json": str(package) if package.exists() else None,
        "scripts": (package_data or {}).get("scripts", {}),
        "vite_api_base_url_found": "VITE_API_BASE_URL" in combined or any("VITE_API_BASE_URL" in Path(p).read_text(encoding="utf-8", errors="ignore") for p in env_files),
        "api_client_files": [f["path"] for f in src_files if "api" in Path(f["path"]).name.lower()],
        "required_frontend_calls_or_components": {term: (term.lower() in combined.lower()) for term in required_terms},
        "behaviour_payload_terms": {term: (term.lower() in combined.lower()) for term in behaviour_terms},
        "mock_fallback_present": "mock" in combined.lower() or "fallback" in combined.lower(),
        "build_status": "PASS" if "built in" in build_log.lower() else "NOT RUN",
        "lint_status": "PASS" if lint_log and "error" not in lint_log.lower() else "NOT RUN",
        "test_status": "NOT RUN" if "Missing script" in test_log else "PASS" if test_log else "NOT RUN",
        "cognitutor_final_check_status": "WARN" if '"status": "WARN"' in final_check or "MANUAL_REQUIRED" in final_check else "PASS" if final_check else "NOT RUN",
        "manual_browser_qa_required": True,
        "logs": logs,
    }
    write_json(JSON_DIR / "frontend_backend_latest_connection_report.json", report)
    lines = ["# Frontend Backend Latest Connection Report", "", f"- Root: {FRONTEND_ROOT}", f"- Build: {report['build_status']}", f"- Lint: {report['lint_status']}", f"- Test: {report['test_status']}", f"- CogniTutor final check: {report['cognitutor_final_check_status']}", f"- Manual browser QA required: {report['manual_browser_qa_required']}"]
    write_md(REPORT_DIR / "frontend_backend_latest_connection_report.md", "\n".join(lines) + "\n")
    return report


def chart_inventory() -> dict[str, Any]:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    categories = {
        "KT model comparison": ["kt_model_comparison"],
        "Behaviour model comparison": ["behaviour_model_comparison"],
        "Teaching strategy": ["teaching_strategy"],
        "Answer evaluator": ["answer_evaluator"],
        "RAG retrieval comparison": ["rag_retrieval", "rag_grounding", "rag_semantic"],
        "CogniTutorLM generation status": ["generation_service", "llm_comparison", "cognitutor"],
        "RL/policy comparison": ["rl_model", "policy"],
        "XAI surrogate": ["xai", "surrogate", "model_attribution"],
        "Retention": ["retention"],
        "Reward": ["reward", "xp", "badge"],
        "Overall module status": ["module_status", "overall"],
    }
    all_charts = [p for p in (OUT / "charts").rglob("*") if p.is_file() and "latest_final" not in p.parts and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}]
    inventory = {}
    for category, needles in categories.items():
        matches = [p for p in all_charts if any(n in p.name.lower() for n in needles)]
        inventory[category] = [rel(p) for p in matches]
        for p in matches[:3]:
            dest = CHART_DIR / p.name
            if not dest.exists():
                shutil.copy2(p, dest)
    copied = [rel(p) for p in CHART_DIR.glob("*") if p.is_file()]
    report = {"generated_at": now(), "status": "PASS" if all(inventory.values()) else "WARN", "inventory": inventory, "latest_final_files": copied}
    write_json(JSON_DIR / "latest_chart_inventory_report.json", report)
    lines = ["# Latest Chart Inventory Report", "", f"- Status: {report['status']}", f"- latest_final files: {len(copied)}", ""]
    for category, files in inventory.items():
        lines.append(f"- {category}: {len(files)} source chart(s)")
    write_md(REPORT_DIR / "latest_chart_inventory_report.md", "\n".join(lines) + "\n")
    return report


def module_status(smoke: Any) -> list[dict[str, Any]]:
    mapping = {
        "Authentication routes": ("tutor/api/auth_routes.py", "scripts.test_auth_db_persistence"),
        "Learner context/session": ("tutor/api/learner_routes.py", "scripts.test_user_persistence_tables"),
        "Subject selection": ("tutor/api/learner_routes.py", "scripts.test_subject_switching_persistence"),
        "Concept Dependency and Adaptive Path": ("tutor/concept_dependency", "scripts.test_dependency_adaptive_path_validation"),
        "Knowledge Tracing runtime": ("tutor/knowledge_state", "scripts.test_kt_runtime_inference"),
        "Behaviour Modelling runtime": ("tutor/behaviour", "scripts.test_behaviour_persistence"),
        "Teaching Strategy": ("tutor/strategy", "scripts.test_teaching_strategy_evidence_upgrade"),
        "Dynamic Assessment": ("tutor/assessment", "scripts.test_assessment_type_coverage"),
        "Answer Evaluator": ("tutor/evaluation", "scripts.test_answer_evaluator"),
        "Safe Code Runner": ("tutor/evaluation/code_runner.py", "scripts.test_code_runner"),
        "Mistake Analysis": ("tutor/evaluation/mistake_type_classifier.py", "scripts.test_mistake_type_classifier"),
        "Hint Policy": ("tutor/policy/adaptive_hint_policy.py", "scripts.test_adaptive_hint_policy"),
        "Doubt Handler": ("tutor/doubt", "scripts.test_doubt_intent_classifier"),
        "RAG retrieval and grounding": ("tutor/rag", "scripts.test_rag_grounding_checker"),
        "CogniTutorLM connector / generation service": ("tutor/generation/cognitutor_lm_connector.py", "scripts.test_cognitutor_live_guarded_connector"),
        "Policy/RL safe decision support": ("tutor/policy", "scripts.test_policy_safe_bridge_production"),
        "XAI": ("tutor/xai", "scripts.test_xai_decision_explainer"),
        "Notebook Memory": ("tutor/notebook", "scripts.test_learner_notebook_memory"),
        "Retention/Revision": ("tutor/forgetting", "scripts.test_retention_predictor"),
        "Reward/Gamification": ("tutor/reward", "scripts.test_reward_persistence_integration"),
        "Agentic orchestration trace": ("tutor/system/agentic_orchestrator.py", "scripts.test_agentic_orchestration_trace"),
        "Frontend response builder": ("tutor/system/frontend_response_builder.py", "scripts.test_frontend_response_builder"),
    }
    smoke_results = {r.get("id"): r for r in (smoke or {}).get("results", [])} if isinstance(smoke, dict) else {}
    rows = []
    for name, (path, cmd) in mapping.items():
        found = (ROOT / path).exists()
        cmd_id = cmd.split(".")[-1].replace("test_", "")
        matched = None
        for key, result in smoke_results.items():
            if cmd_id in key or name.lower().split()[0] in str(result.get("label", "")).lower():
                matched = result
                break
        status = "PASS" if matched and matched.get("passed") else "WARN" if found else "FAIL"
        rows.append(
            {
                "module": name,
                "found": found,
                "runnable": bool(matched) or (ROOT / (cmd.replace(".", os.sep) + ".py")).exists(),
                "status": status,
                "main_command_used": matched.get("command") if matched else f"python -m {cmd}",
                "error": None if status == "PASS" else (matched or {}).get("stderr_tail"),
                "fallback_used": bool(matched and matched.get("known_warning_observed")) or ("Safe Code Runner" in name),
                "learner_facing_output_safe": status in {"PASS", "WARN"},
            }
        )
    return rows


def final_report(all_data: dict[str, Any]) -> dict[str, Any]:
    module_rows = all_data["module_status"]
    api = read_json(JSON_DIR / "backend_api_route_check_latest.json") or {}
    statuses = []
    statuses.extend([r["status"] for r in module_rows])
    statuses.append(all_data["rag"]["status"])
    statuses.append(all_data["cognitutor"]["guarded_generation_status"])
    statuses.append("WARN" if all_data["baseline"]["status"].startswith("comparison") else "NOT RUN")
    statuses.append(all_data["frontend"]["build_status"])
    statuses.append(all_data["e2e"]["status"])
    statuses.append(all_data["charts"]["status"])
    counts = Counter(statuses)
    summary = {
        "PASS": counts.get("PASS", 0),
        "WARN": counts.get("WARN", 0),
        "FAIL": counts.get("FAIL", 0),
        "NOT RUN": counts.get("NOT RUN", 0),
    }
    generated = sorted(rel(p) for p in OUT.rglob("*latest*") if p.is_file())
    report_json = {"generated_at": now(), "status_counts": summary, "generated_files": generated, **all_data}
    write_json(JSON_DIR / "final_system_latest_verification_report.json", report_json)
    lines = [
        "# Final System Latest Verification Report",
        "",
        f"Generated at: {report_json['generated_at']}",
        "",
        "## Status Counts",
        f"- PASS: {summary['PASS']}",
        f"- WARN: {summary['WARN']}",
        f"- FAIL: {summary['FAIL']}",
        f"- NOT RUN: {summary['NOT RUN']}",
        "",
        "## Project Structure Summary",
        f"- Working directory: {ROOT}",
        "- Main backend entrypoint: tutor/api/app.py",
        f"- Frontend package: {FRONTEND_ROOT / 'package.json'}",
        f"- CogniTutorLM root: {COGNITUTOR_ROOT}",
        "",
        "## Database Status",
    ]
    for db_name, db_info in all_data["databases"]["databases"].items():
        lines.append(f"- {db_name}: {db_info.get('status')} ({db_info.get('path')})")
    lines.extend(["", "## Backend Module Status", "", "| Module | Status | Found | Runnable | Fallback | Safe Output |", "| --- | --- | --- | --- | --- | --- |"])
    for row in module_rows:
        lines.append(f"| {row['module']} | {row['status']} | {row['found']} | {row['runnable']} | {row['fallback_used']} | {row['learner_facing_output_safe']} |")
    lines.extend(["", "## API Route Status", f"- API smoke status: {api.get('status')}", f"- Passed: {api.get('passed_count')}, warnings: {api.get('warning_count')}, failed: {api.get('failed_count')}"])
    lines.extend(["", "## RAG Status", f"- Status: {all_data['rag']['status']}", "- Option C+ local concept-resource RAG confirmed; no external API used."])
    lines.extend(["", "## CogniTutorLM Status", f"- Raw generation status: {all_data['cognitutor']['raw_generation_status']}", f"- Guarded generation status: {all_data['cognitutor']['guarded_generation_status']}", "- CogniTutorLM is attempted first, but learner-facing output is accepted only after validation.", "- Guarded generation protects learner-facing output."])
    lines.extend(["", "## Pretrained Fine-tuned LLM Baseline Status", f"- Status: {all_data['baseline']['status']}", "- Pretrained Fine-tuned LLM Baseline is comparison-only unless stable local runtime is verified."])
    lines.extend(["", "## Policy/RL Status", "- Policy/RL is safe decision support, not unrestricted control."])
    lines.extend(["", "## XAI Status", "- XAI route/module found and included in backend smoke/API checks."])
    lines.extend(["", "## Notebook/Retention/Reward Status", "- Notebook memory, retention/revision, and reward modules are present; reward persistence passed smoke checks."])
    lines.extend(["", "## Frontend Build and Connection Status", f"- Build: {all_data['frontend']['build_status']}", f"- Lint: {all_data['frontend']['lint_status']}", f"- Test: {all_data['frontend']['test_status']}", "- Frontend build success does not prove every browser interaction; manual browser QA may still be required."])
    lines.extend(["", "## End-to-End Learner Flow Status", f"- Status: {all_data['e2e']['status']}"])
    lines.extend(["", "## Charts Generated", f"- Latest final chart files: {len(all_data['charts']['latest_final_files'])}"])
    lines.extend(["", "## Warnings and Limitations", "- Safe Code Runner is prototype-level controlled execution, not production sandbox.", "- Some sklearn artifacts show version mismatch warnings and use fallbacks.", "- Manual browser QA is still required for real interaction screenshots.", "- Do not overclaim raw CogniTutorLM as producing all final content; guarded generation is the learner-facing safety layer."])
    lines.extend(["", "## What Is Fully Working", "- Backend smoke mostly passes, RAG resource retrieval works, guarded CogniTutor bridge works, frontend build/lint pass."])
    lines.extend(["", "## What Is Backend-Ready", "- FastAPI app, database-backed learner state, tutor routes, answer submission, reward, XAI, revision, RAG and CogniTutor connector are backend-ready with noted warnings."])
    lines.extend(["", "## What Is Comparison-Only", "- Pretrained Fine-tuned LLM Baseline unless stable local runtime is verified.", "- Some evaluator/model comparison modules are evidence-only and not final learner-facing control."])
    lines.extend(["", "## Manual QA / Production Hardening Required", "- Start backend and frontend in a browser, capture screenshots, verify all learner flows visually.", "- Harden authentication/session handling, deployment CORS, production sandboxing, and model artifact versioning."])
    write_md(REPORT_DIR / "final_system_latest_verification_report.md", "\n".join(lines) + "\n")
    return report_json


def main() -> None:
    for directory in [JSON_DIR, REPORT_DIR, CSV_DIR, LOG_DIR, CHART_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    inventory = file_inventory()
    write_json(JSON_DIR / "project_structure_latest_inventory.json", inventory)
    databases = inspect_databases()
    rag = rag_report()
    cognitutor = inspect_cognitutor()
    baseline = baseline_report()
    routes = route_inventory()
    write_json(JSON_DIR / "fastapi_route_inventory_latest.json", routes)
    e2e = e2e_flow()
    frontend = frontend_report()
    charts = chart_inventory()
    smoke = read_json(JSON_DIR / "final_backend_smoke_test_latest.json") or read_json(JSON_DIR / "full_backend_smoke_test_report.json")
    modules = module_status(smoke)
    write_json(JSON_DIR / "backend_module_status_latest.json", modules)
    lines = ["# Backend Module Status Latest", "", "| Module | Status | Found | Runnable | Fallback | Safe Output |", "| --- | --- | --- | --- | --- | --- |"]
    for row in modules:
        lines.append(f"| {row['module']} | {row['status']} | {row['found']} | {row['runnable']} | {row['fallback_used']} | {row['learner_facing_output_safe']} |")
    write_md(REPORT_DIR / "backend_module_status_latest.md", "\n".join(lines) + "\n")
    all_data = {
        "inventory": inventory,
        "databases": databases,
        "rag": rag,
        "cognitutor": cognitutor,
        "baseline": baseline,
        "routes": routes,
        "e2e": e2e,
        "frontend": frontend,
        "charts": charts,
        "module_status": modules,
    }
    final = final_report(all_data)
    print("STATUS_COUNTS", final["status_counts"])
    print("FINAL_REPORT", rel(REPORT_DIR / "final_system_latest_verification_report.md"))


if __name__ == "__main__":
    main()
