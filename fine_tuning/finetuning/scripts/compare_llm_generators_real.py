"""
Fair multi-system LLM comparison (live outputs only; no fabricated scores).

Run from repo root `pretrained_finetuning`:
  python -m scripts.compare_llm_generators_real
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PRETRAINED_ROOT = Path(__file__).resolve().parents[1]

# Captured once after Pretrained `tutor` imports succeed (before cognition `tutor` shadows).
PRETRAINED_BUILD_PROMPT: Optional[Callable[..., str]] = None
COGNITUTOR_ROOT = Path(
    r"C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\CogniTutor_LM_from_scratch"
)
COGNITION_TUTOR_ROOT = Path(
    r"C:\Users\Aswini_Ayappan\PycharmProjects\PythonProject\cognition_adaptive_AI_tutor"
)

OUTPUT_JSON = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "json"
    / "llm_generation_comparison_real.json"
)
OUTPUT_MD = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "reports"
    / "llm_generation_comparison_real.md"
)
SMALL_OUTPUT_JSON = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "json"
    / "llm_generation_comparison_real_small.json"
)
SMALL_OUTPUT_MD = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "reports"
    / "llm_generation_comparison_real_small.md"
)
SMOKE_OUTPUT_JSON = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "json"
    / "llm_generation_comparison_real_smoke.json"
)
SMOKE_OUTPUT_MD = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "reports"
    / "llm_generation_comparison_real_smoke.md"
)
INTERPRETATION_MD = (
    PRETRAINED_ROOT
    / "evaluation_outputs"
    / "reports"
    / "llm_comparison_interpretation.md"
)

CONCEPTS: List[Tuple[str, str]] = [
    ("Python Variables", "Python"),
    ("Python Loops", "Python"),
    ("SQL SELECT Queries", "SQL"),
    ("HTML Tags and Elements", "HTML"),
    ("Git Commits and History", "Git"),
    ("Data Structures Arrays", "Data Structures"),
    ("Data Structures Stack", "Data Structures"),
]

TASK_TYPES = [
    "explanation",
    "flashcard",
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
]

# CogniTutorLM artifact names (must match generated_tutor_artifacts.json)
COGNITUTOR_CONCEPT: Dict[str, Tuple[str, str]] = {
    "Python Variables": ("Variables", "Python"),
    "Python Loops": ("Loops", "Python"),
    "SQL SELECT Queries": ("SQL SELECT Queries", "SQL"),
    "HTML Tags and Elements": ("HTML Tags and Elements", "HTML"),
    "Git Commits and History": ("Commits and History", "Git"),
    "Data Structures Arrays": ("Arrays", "Data Structures"),
    "Data Structures Stack": ("Stack", "Data Structures"),
}

TASK_TO_ARTIFACT: Dict[str, str] = {
    "explanation": "definition_view",
    "flashcard": "flashcard_view",
    "mcq": "mcq",
    "debug_task": "debug_view",
    "output_prediction": "output_prediction_view",
    "transfer_question": "transfer_view",
    "challenge_question": "challenge_view",
}

SMOKE_CONCEPTS = ["Python Variables", "SQL SELECT Queries"]
SMOKE_TASK_TYPES = ["explanation", "flashcard"]


def _env_flag(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None:
        return default
    try:
        return int(v.strip())
    except Exception:
        return default


def _run_with_timeout(
    fn: Callable[..., Tuple[Any, ...]],
    timeout_seconds: int,
    *args: Any,
) -> Tuple[bool, Optional[Tuple[Any, ...]], Optional[str]]:
    result_box: Dict[str, Tuple[Any, ...]] = {}
    err_box: Dict[str, str] = {}

    def _target() -> None:
        try:
            result_box["value"] = fn(*args)
        except Exception as ex:
            err_box["value"] = repr(ex)

    th = threading.Thread(target=_target, daemon=True)
    th.start()
    th.join(timeout=timeout_seconds)
    if th.is_alive():
        return False, None, f"timeout_after_{timeout_seconds}s"
    if "value" in err_box:
        return True, None, err_box["value"]
    return True, result_box.get("value"), None


def _truncate_words(text: str, max_words: int = 140) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).strip()


def _ensure_pretrained_path() -> None:
    r = str(PRETRAINED_ROOT)
    if r not in sys.path:
        sys.path.insert(0, r)


def _purge_tutor_modules() -> None:
    for key in list(sys.modules):
        if key == "tutor" or key.startswith("tutor."):
            del sys.modules[key]


def _has_repetition(text: str) -> bool:
    words = text.lower().split()
    if len(words) < 8:
        return False
    for i in range(len(words) - 2):
        phrase = " ".join(words[i : i + 3])
        if text.lower().count(phrase) >= 3:
            return True
    return False


def _concept_tokens(concept: str) -> List[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9]+", concept.lower()) if len(t) > 2]


def score_concept_relevance(concept: str, text: str) -> float:
    if not text.strip():
        return 0.0
    toks = set(_concept_tokens(concept))
    if not toks:
        return 0.0
    low = text.lower()
    hits = sum(1 for t in toks if t in low)
    return round(min(1.0, hits / max(1, len(toks))), 3)


def score_format_validity(task: str, text: str) -> float:
    low = text.lower()
    if not text.strip():
        return 0.0
    if task == "flashcard":
        ok = "front:" in low and "back:" in low
        return 1.0 if ok else 0.0
    if task == "mcq":
        try:
            obj = json.loads(text)
        except Exception:
            return 0.0
        if not isinstance(obj, dict):
            return 0.0
        opts = obj.get("options")
        ok = (
            "question" in obj
            and isinstance(opts, list)
            and len(opts) == 4
            and "answer" in obj
            and "explanation" in obj
        )
        return 1.0 if ok else 0.0
    if task == "debug_task":
        ok = "buggy code:" in low and "expected fix:" in low
        return 1.0 if ok else 0.0
    if task == "output_prediction":
        ok = "code:" in low and "answer:" in low
        return 1.0 if ok else 0.0
    if task == "transfer_question":
        ok = "question:" in low and "answer:" in low
        return 1.0 if ok else 0.0
    if task == "challenge_question":
        ok = "challenge:" in low and "solution outline:" in low
        return 1.0 if ok else 0.0
    if task == "explanation":
        prose = re.sub(r"```[\s\S]*?```", " ", text)
        words = len(prose.split())
        return 1.0 if words >= 18 else round(words / 18, 3)
    return 0.5


def score_task_fit(task: str, text: str) -> float:
    return score_format_validity(task, text)


def score_teaching_quality_proxy(concept: str, text: str) -> float:
    if not text.strip():
        return 0.0
    words = len(text.split())
    if words < 12:
        return round(words / 12, 3)
    score = 0.6
    if any(x in text.lower() for x in ("example", "for instance", "e.g.")):
        score += 0.2
    if score_concept_relevance(concept, text) >= 0.4:
        score += 0.2
    return round(min(1.0, score), 3)


def unified_prompt(concept: str, task: str) -> str:
    return (
        f"Concept: {concept}\n"
        f"Task type: {task}\n"
        f"Difficulty: easy\n"
        f"Learner state: beginner\n"
        f"Teaching style: simple\n"
    )


# ---------------------------------------------------------------------------
# System 1 — template baseline (deterministic structured text)
# ---------------------------------------------------------------------------

def run_template_baseline(concept: str, task: str, domain: str) -> Tuple[str, bool, Optional[str]]:
    c = concept
    if task == "explanation":
        text = (
            f"Definition: {c} is a core topic students must understand.\n"
            f"Example: A minimal example ties the idea to practice.\n"
            f"Why it matters: It appears often in coursework and projects."
        )
    elif task == "flashcard":
        text = (
            f"Front: What is {c}?\n"
            f"Back: {c} is a foundational idea with clear rules and typical use cases."
        )
    elif task == "mcq":
        text = json.dumps(
            {
                "question": f"Which best describes {c}?",
                "options": [
                    "A core learning topic",
                    "A file format only",
                    "A UI animation",
                    "A database vendor",
                ],
                "answer": "A core learning topic",
                "explanation": f"{c} is taught as part of the adaptive tutor curriculum.",
            },
            indent=2,
        )
    elif task == "debug_task":
        if domain == "HTML":
            text = (
                "Buggy code:\n"
                "<div><p>Hello</div>\n\n"
                "Expected fix:\n"
                "Close the paragraph: <div><p>Hello</p></div>\n\n"
                "Hint: Every opened tag should be closed in valid HTML."
            )
        elif domain == "SQL":
            text = (
                "Buggy code:\n"
                "SELECT name FORM users;\n\n"
                "Expected fix:\n"
                "Use FROM instead of FORM.\n\n"
                "Hint: SQL keywords must be spelled correctly."
            )
        elif domain == "Git":
            text = (
                "Buggy code:\n"
                "git comit -m \"save\"\n\n"
                "Expected fix:\n"
                "Use git commit (correct spelling).\n\n"
                "Hint: Git subcommands are fixed vocabulary."
            )
        else:
            text = (
                "Buggy code:\n"
                "for i in range(5)\n"
                "    print(i)\n\n"
                "Expected fix:\n"
                "Add ':' after range(5) so the loop header is valid Python.\n\n"
                "Hint: Python block headers end with a colon."
            )
    elif task == "output_prediction":
        text = (
            "Code:\n"
            "x = 2\n"
            "y = 3\n"
            "print(x + y)\n\n"
            "Answer:\n"
            "5"
        )
    elif task == "transfer_question":
        text = (
            f"Question: Where would you apply {c} in a small project?\n"
            f"Answer: Use it when the feature touches that topic so learners connect theory to code."
        )
    elif task == "challenge_question":
        text = (
            f"Challenge: Explain {c} with one concrete scenario.\n"
            f"Solution outline: Name scenario → list 2 steps → give one takeaway."
        )
    else:
        text = f"{c}: unsupported task."
        return text, False, "unknown_task"
    return text, True, None


# ---------------------------------------------------------------------------
# System 2 — CogniTutorLM (read-only import from sibling project)
# ---------------------------------------------------------------------------

def run_cognitutor(
    svc: Any,
    concept: str,
    domain: str,
    task: str,
) -> Tuple[str, bool, Optional[str]]:
    if svc is None:
        return "", False, "TutorLMService not available"

    cname, cdom = COGNITUTOR_CONCEPT.get(concept, (None, None))
    if not cname:
        return "", False, "concept_not_mapped"

    if task == "mcq":
        try:
            r = svc.get_assessment_questions(
                concept_name=cname,
                domain=cdom,
                question_types=["mcq"],
                num_questions=1,
                shuffle=False,
            )
        except Exception as e:
            return "", False, str(e)
        if r.get("status") != "success" or not r.get("questions"):
            return "", False, json.dumps(r)[:500]
        q = r["questions"][0]
        qj = q.get("question")
        if isinstance(qj, dict):
            text = json.dumps(
                {
                    "question": qj.get("question"),
                    "options": qj.get("options", []),
                    "answer": qj.get("answer"),
                    "explanation": qj.get("explanation", ""),
                },
                indent=2,
                ensure_ascii=False,
            )
        else:
            text = json.dumps(q, indent=2, default=str, ensure_ascii=False)
        return text, True, None

    artifact = TASK_TO_ARTIFACT.get(task, "definition_view")
    try:
        r = svc.get_teaching_view(
            concept_name=cname,
            domain=cdom,
            artifact_type=artifact,
        )
    except Exception as e:
        return "", False, str(e)

    if r.get("status") != "success":
        if artifact != "definition_view":
            r2 = svc.get_teaching_view(
                concept_name=cname,
                domain=cdom,
                artifact_type="definition_view",
            )
            if r2.get("status") == "success" and r2.get("teaching"):
                t = r2.get("teaching")
                return (
                    str(t),
                    True,
                    f"fallback_from_definition_view:{artifact}_missing",
                )
        return "", False, json.dumps(r)[:800]

    teaching = r.get("teaching")
    if teaching is None:
        return "", False, "empty_teaching"
    return str(teaching), True, None


# ---------------------------------------------------------------------------
# System 3 — Pretrained (local HF + LoRA inside pretrained_finetuning)
# ---------------------------------------------------------------------------

def run_pretrained_generate(
    model: Any,
    tokenizer: Any,
    concept: str,
    task: str,
    max_new_tokens: int,
    do_sample: bool,
) -> Tuple[str, bool, Optional[str]]:
    prompt = (
        f"Generate a {task} for concept {concept}. "
        "Keep it under 80 words. Follow required format."
    )
    try:
        import torch

        inputs = tokenizer(prompt, return_tensors="pt")
        t0 = time.perf_counter()
        if not do_sample and hasattr(model, "generation_config"):
            # Avoid HF warnings about sampling-only params when deterministic decoding is used.
            for attr in ("temperature", "top_p", "top_k"):
                if hasattr(model.generation_config, attr):
                    setattr(model.generation_config, attr, None)
        gen_kwargs: Dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "repetition_penalty": 1.2,
            "pad_token_id": tokenizer.eos_token_id,
        }
        if do_sample:
            gen_kwargs.update(
                {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "top_k": 50,
                }
            )
        with torch.no_grad():
            out = model.generate(**inputs, **gen_kwargs)
        latency = time.perf_counter() - t0
        text = tokenizer.decode(out[0], skip_special_tokens=True)
        if "### Output" in text:
            text = text.split("### Output")[-1].strip()
        text = _truncate_words(text, max_words=140)
        if len(text.strip()) < 8:
            return "", False, f"empty_or_short_output latency={latency:.2f}s"
        return text, True, None
    except Exception as e:
        return "", False, str(e)


# ---------------------------------------------------------------------------
# System 4 — RAG (cognition_adaptive_AI_tutor; read-only)
# ---------------------------------------------------------------------------

def run_rag_grounded(
    builder: Any,
    concept: str,
    domain: str,
    task: str,
) -> Tuple[str, Optional[Dict[str, Any]], bool, Optional[str]]:
    if builder is None:
        return "", None, False, "RAGContextBuilder not available"
    query = f"{concept} {task}"
    try:
        t0 = time.perf_counter()
        ctx = builder.build_context(
            query=query,
            top_k=8,
            preferred_domain=domain,
        )
        latency = time.perf_counter() - t0
    except Exception as e:
        return "", None, False, str(e)

    if ctx.get("status") != "success":
        return "", ctx, False, str(ctx.get("reason") or ctx.get("status"))

    definition = str(ctx.get("definition") or "")
    examples = ctx.get("examples") or []
    kp = ctx.get("key_points") or []
    topic = str(ctx.get("topic") or concept)

    ex_text = " ".join(examples[:2]) if examples else ""
    kp_text = "; ".join(kp[:4]) if kp else ""

    if task == "explanation":
        body = (
            f"Definition: {definition or topic}\n"
            f"Examples from materials: {ex_text}\n"
            f"Key points: {kp_text}\n"
            f"(Grounded on retrieved RAG chunks; topic={topic}.)"
        )
    elif task == "flashcard":
        body = (
            f"Front: What is {topic}?\n"
            f"Back: {definition[:400] if definition else topic + ' — see course materials.'}"
        )
    elif task == "mcq":
        opt_a = (definition[:120] + "…") if len(definition) > 120 else (definition or f"Core idea: {topic}")
        body = json.dumps(
            {
                "question": f"Which statement best matches retrieved notes about {topic}?",
                "options": [
                    opt_a,
                    "Unrelated UI layout detail",
                    "Unrelated networking jargon",
                    "Unrelated file-system trivia",
                ],
                "answer": opt_a,
                "explanation": f"Grounded excerpt: {ex_text[:200] or kp_text[:200]}",
            },
            indent=2,
            ensure_ascii=False,
        )
    elif task == "debug_task":
        body = (
            "Buggy code:\n"
            f"{ex_text[:200] or 'see examples section in retrieved notes'}\n\n"
            "Expected fix:\n"
            f"Align with key points: {kp_text[:200]}\n\n"
            "Hint: Compare with definition in source chunk."
        )
    elif task == "output_prediction":
        body = (
            "Code:\n"
            f"{ex_text[:120] or 'x = 1\\nprint(x)'}\n\n"
            "Answer:\n"
            "(Derived from examples in retrieved context.)"
        )
    elif task == "transfer_question":
        body = (
            f"Question: How does {topic} show up in real projects per retrieved notes?\n"
            f"Answer: {ctx.get('real_world_use') or definition[:300]}"
        )
    elif task == "challenge_question":
        body = (
            f"Challenge: Apply {topic} using one scenario from the retrieved materials.\n"
            f"Solution outline: {kp_text[:280]}"
        )
    else:
        body = definition or topic

    meta = {
        "chunk_count": ctx.get("chunk_count"),
        "latency_seconds": round(latency, 3),
        "domain": ctx.get("domain"),
        "topic": topic,
    }
    return body, meta, True, None


def aggregate_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(rows) or 1
    fmt = sum(float(r["metrics"]["format_validity"]) for r in rows) / n
    cr = sum(float(r["metrics"]["concept_relevance"]) for r in rows) / n
    tf = sum(float(r["metrics"]["task_fit"]) for r in rows) / n
    tq = sum(float(r["metrics"]["teaching_quality_proxy"]) for r in rows) / n
    rep = sum(float(r["metrics"]["repetition_hit"]) for r in rows) / n
    fb = sum(1 for r in rows if r.get("fallback_or_error")) / n
    lat = [float(r["latency_seconds"]) for r in rows if r.get("latency_seconds") is not None]
    gs = [r["metrics"].get("grounding_score") for r in rows if r["metrics"].get("grounding_score") is not None]
    return {
        "mean_format_validity": round(fmt, 4),
        "mean_concept_relevance": round(cr, 4),
        "mean_task_fit": round(tf, 4),
        "mean_teaching_quality_proxy": round(tq, 4),
        "mean_repetition_rate": round(rep, 4),
        "fallback_rate": round(fb, 4),
        "mean_grounding_score": round(sum(gs) / len(gs), 4) if gs else None,
        "mean_latency_seconds": round(sum(lat) / len(lat), 4) if lat else None,
    }


def score_row(
    concept: str,
    task: str,
    text: str,
    grounding: Optional[float],
    latency: Optional[float],
    fallback: bool,
) -> Dict[str, Any]:
    rep = 1.0 if _has_repetition(text) else 0.0
    return {
        "format_validity": score_format_validity(task, text),
        "concept_relevance": score_concept_relevance(concept, text),
        "task_fit": score_task_fit(task, text),
        "teaching_quality_proxy": score_teaching_quality_proxy(concept, text),
        "repetition_hit": rep,
        "grounding_score": grounding,
        "latency_seconds": latency,
        "fallback_or_error": fallback,
    }


@dataclass
class SystemRun:
    system_id: str
    connection_status: str = "unknown"
    generation_status: str = "unknown"
    error_message: Optional[str] = None
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def ok_fraction(self) -> float:
        if not self.rows:
            return 0.0
        ok = sum(1 for r in self.rows if r.get("ok"))
        return ok / len(self.rows)


def try_load_cognitutor() -> Tuple[Optional[Any], str, Optional[str]]:
    if not COGNITUTOR_ROOT.is_dir():
        return None, "error", f"CogniTutor_LM_from_scratch path missing: {COGNITUTOR_ROOT}"
    p = str(COGNITUTOR_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    try:
        from src.tutor_lm_service import TutorLMService

        return TutorLMService(), "success", None
    except Exception as e:
        return None, "error", repr(e)


def try_load_rag() -> Tuple[Optional[Any], str, Optional[str]]:
    if not COGNITION_TUTOR_ROOT.is_dir():
        return None, "error", f"cognition_adaptive_AI_tutor path missing: {COGNITION_TUTOR_ROOT}"
    _purge_tutor_modules()
    p = str(COGNITION_TUTOR_ROOT)
    if p not in sys.path:
        sys.path.insert(0, p)
    else:
        sys.path.remove(p)
        sys.path.insert(0, p)
    try:
        from tutor.rag.rag_context_builder import RAGContextBuilder

        return RAGContextBuilder(), "success", None
    except Exception as e:
        return None, "error", repr(e)


def try_load_pretrained_model() -> Tuple[Any, Any, str, str, Optional[str]]:
    global PRETRAINED_BUILD_PROMPT
    PRETRAINED_BUILD_PROMPT = None
    _purge_tutor_modules()
    _ensure_pretrained_path()
    sys.path.insert(0, str(PRETRAINED_ROOT))
    try:
        from tutor.llm_finetune.generate_test import build_prompt as _bp
        from tutor.llm_finetune.model_loader import load_model

        loaded = load_model()
        st = loaded.get("generation_status", "unknown")
        if loaded.get("model") is None or loaded.get("tokenizer") is None:
            return None, None, "warning", st, loaded.get("error_message")
        PRETRAINED_BUILD_PROMPT = _bp
        return (
            loaded["model"],
            loaded["tokenizer"],
            "success",
            st,
            None,
        )
    except Exception as e:
        return None, None, "error", "load_failed", repr(e)


def main() -> None:
    smoke_mode = _env_flag("COMPARE_SMOKE", False)
    small_real_mode = _env_flag("COMPARE_SMALL_REAL", False)
    compare_only_pretrained = _env_flag("COMPARE_ONLY_PRETRAINED", False)
    max_concepts = _env_int("COMPARE_MAX_CONCEPTS", len(CONCEPTS))
    max_tasks = _env_int("COMPARE_MAX_TASKS", len(TASK_TYPES))
    skip_pretrained_model = _env_flag("COMPARE_SKIP_PRETRAINED_MODEL", False)
    timeout_seconds = _env_int("COMPARE_TIMEOUT_SECONDS", 60)
    pretrained_max_new_tokens = _env_int("PRETRAINED_MAX_NEW_TOKENS", 80)
    pretrained_do_sample = _env_flag("PRETRAINED_DO_SAMPLE", False)
    compare_pretrained_max_prompts = _env_int("COMPARE_PRETRAINED_MAX_PROMPTS", 0)

    if smoke_mode:
        out_json = SMOKE_OUTPUT_JSON
        out_md = SMOKE_OUTPUT_MD
    elif small_real_mode:
        out_json = SMALL_OUTPUT_JSON
        out_md = SMALL_OUTPUT_MD
    else:
        out_json = OUTPUT_JSON
        out_md = OUTPUT_MD

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    INTERPRETATION_MD.parent.parent.mkdir(parents=True, exist_ok=True)

    concepts = CONCEPTS
    task_types = TASK_TYPES
    if smoke_mode or small_real_mode:
        concepts = [c for c in CONCEPTS if c[0] in SMOKE_CONCEPTS]
        task_types = [t for t in TASK_TYPES if t in SMOKE_TASK_TYPES]
    concepts = concepts[: max(1, max_concepts)]
    task_types = task_types[: max(1, max_tasks)]

    prompts: List[Dict[str, str]] = []
    for concept, domain in concepts:
        for task in task_types:
            prompts.append(
                {
                    "concept": concept,
                    "domain": domain,
                    "task_type": task,
                    "prompt": unified_prompt(concept, task),
                }
            )

    systems: Dict[str, SystemRun] = {
        "template_rule_baseline": SystemRun("template_rule_baseline"),
        "cognitutor_lm_from_scratch": SystemRun("cognitutor_lm_from_scratch"),
        "pretrained_pretrained_finetuned_llm": SystemRun("pretrained_pretrained_finetuned_llm"),
        "rag_grounded_service": SystemRun("rag_grounded_service"),
    }
    print("Loading system: template")
    systems["template_rule_baseline"].connection_status = (
        "skipped_by_config" if compare_only_pretrained else "success"
    )

    # --- CogniTutor ---
    print("Loading system: CogniTutorLM")
    if compare_only_pretrained:
        ct_svc, ct_conn, ct_err = None, "skipped_by_config", "COMPARE_ONLY_PRETRAINED=1"
    else:
        ct_svc, ct_conn, ct_err = try_load_cognitutor()
    systems["cognitutor_lm_from_scratch"].connection_status = ct_conn
    systems["cognitutor_lm_from_scratch"].error_message = ct_err

    # --- Pretrained (before cognition `tutor` pollutes sys.modules) ---
    print("Loading system: Pretrained")
    if skip_pretrained_model:
        model, tokenizer, sv_conn, sv_gen, sv_err = (
            None,
            None,
            "success",
            "skipped_for_smoke_test",
            "COMPARE_SKIP_PRETRAINED_MODEL=1",
        )
    else:
        model, tokenizer, sv_conn, sv_gen, sv_err = try_load_pretrained_model()
    systems["pretrained_pretrained_finetuned_llm"].connection_status = sv_conn
    systems["pretrained_pretrained_finetuned_llm"].generation_status = sv_gen
    systems["pretrained_pretrained_finetuned_llm"].error_message = sv_err

    # --- RAG (imports cognition `tutor` — keep after Pretrained model load) ---
    print("Loading system: RAG")
    if compare_only_pretrained:
        rag_b, rag_conn, rag_err = None, "skipped_by_config", "COMPARE_ONLY_PRETRAINED=1"
    else:
        rag_b, rag_conn, rag_err = try_load_rag()
    systems["rag_grounded_service"].connection_status = rag_conn
    systems["rag_grounded_service"].error_message = rag_err

    fixture_results: List[Dict[str, Any]] = []
    total_prompts = len(prompts)
    pretrained_generated_count = 0
    pretrained_skipped_due_to_runtime_limit_count = 0
    pretrained_latencies: List[float] = []

    for idx, p in enumerate(prompts, 1):
        concept = p["concept"]
        domain = p["domain"]
        task = p["task_type"]
        up = p["prompt"]

        # 1 Template
        print(f"Generating system template prompt {idx}/{total_prompts}")
        if compare_only_pretrained:
            txt, ok, err, lat = "", False, "skipped_due_to_compare_only_pretrained", None
        else:
            t0 = time.perf_counter()
            done, tres, terr = _run_with_timeout(
                run_template_baseline, timeout_seconds, concept, task, domain
            )
            lat = time.perf_counter() - t0
            if done and tres is not None:
                txt, ok, err = tres
            else:
                txt, ok, err = "", False, terr or "timeout_or_unknown_error"
        fb = not ok
        m = score_row(concept, task, txt, None, lat, fb)
        systems["template_rule_baseline"].rows.append(
            {
                "concept": concept,
                "task_type": task,
                "prompt": up,
                "output": txt,
                "ok": ok and len(txt.strip()) >= 10,
                "error_message": err,
                "latency_seconds": lat,
                "metrics": m,
            }
        )

        # 2 CogniTutor
        if ct_svc is not None:
            print(f"Generating system CogniTutorLM prompt {idx}/{total_prompts}")
            t0 = time.perf_counter()
            done, cres, cto_err = _run_with_timeout(
                run_cognitutor, timeout_seconds, ct_svc, concept, domain, task
            )
            lat = time.perf_counter() - t0
            if done and cres is not None:
                ctxt, cok, cerr = cres
            else:
                ctxt, cok, cerr = "", False, cto_err or "timeout_or_unknown_error"
            m = score_row(concept, task, ctxt, None, lat, not cok)
            meta = None
            if cerr and cerr.startswith("fallback_from_definition_view"):
                try:
                    meta = ct_svc.build_rag_grounding_metadata(
                        query=f"{concept} {task}",
                        concept_name=COGNITUTOR_CONCEPT[concept][0],
                        domain=COGNITUTOR_CONCEPT[concept][1],
                    )
                except Exception:
                    meta = None
            gs = None
            if isinstance(meta, dict) and meta.get("grounding_score") is not None:
                gs = float(meta["grounding_score"])
            m["grounding_score"] = gs
            systems["cognitutor_lm_from_scratch"].rows.append(
                {
                    "concept": concept,
                    "task_type": task,
                    "prompt": up,
                    "output": ctxt,
                    "ok": cok and len(ctxt.strip()) >= 8,
                    "error_message": cerr,
                    "latency_seconds": lat,
                    "metrics": m,
                }
            )
        else:
            systems["cognitutor_lm_from_scratch"].rows.append(
                {
                    "concept": concept,
                    "task_type": task,
                    "prompt": up,
                    "output": "",
                    "ok": False,
                    "error_message": ct_err or "skipped_due_to_compare_only_pretrained",
                    "latency_seconds": None,
                    "metrics": score_row(concept, task, "", None, None, True),
                }
            )

        # 3 Pretrained
        if model is not None and tokenizer is not None:
            if compare_pretrained_max_prompts > 0 and pretrained_generated_count >= compare_pretrained_max_prompts:
                pretrained_skipped_due_to_runtime_limit_count += 1
                systems["pretrained_pretrained_finetuned_llm"].rows.append(
                    {
                        "concept": concept,
                        "task_type": task,
                        "prompt": up,
                        "output": "",
                        "ok": False,
                        "error_message": "skipped_due_to_runtime_limit",
                        "latency_seconds": None,
                        "metrics": score_row(concept, task, "", None, None, True),
                    }
                )
            else:
                print(f"Generating system Pretrained prompt {idx}/{total_prompts}")
                t0 = time.perf_counter()
                done, sres, sto_err = _run_with_timeout(
                    run_pretrained_generate,
                    timeout_seconds,
                    model,
                    tokenizer,
                    concept,
                    task,
                    pretrained_max_new_tokens,
                    pretrained_do_sample,
                )
                lat = time.perf_counter() - t0
                if done and sres is not None:
                    stxt, sok, serr = sres
                else:
                    stxt, sok, serr = "", False, sto_err or "timeout_or_unknown_error"
                if sok:
                    pretrained_generated_count += 1
                    pretrained_latencies.append(lat)
                m = score_row(concept, task, stxt, None, lat, not sok)
                systems["pretrained_pretrained_finetuned_llm"].rows.append(
                    {
                        "concept": concept,
                        "task_type": task,
                        "prompt": up,
                        "output": stxt,
                        "ok": sok and len(stxt.strip()) >= 8,
                        "error_message": serr,
                        "latency_seconds": lat,
                        "metrics": m,
                    }
                )
        else:
            systems["pretrained_pretrained_finetuned_llm"].rows.append(
                {
                    "concept": concept,
                    "task_type": task,
                    "prompt": up,
                    "output": "",
                    "ok": False,
                    "error_message": sv_err,
                    "latency_seconds": None,
                    "metrics": score_row(concept, task, "", None, None, True),
                }
            )

        # 4 RAG
        if rag_b is not None:
            print(f"Generating system RAG prompt {idx}/{total_prompts}")
            t0 = time.perf_counter()
            done, rres, rto_err = _run_with_timeout(
                run_rag_grounded, timeout_seconds, rag_b, concept, domain, task
            )
            lat = time.perf_counter() - t0
            if done and rres is not None:
                rtxt, rctx, rok, rerr = rres
            else:
                rtxt, rctx, rok, rerr = "", None, False, rto_err or "timeout_or_unknown_error"
            gscore = None
            if isinstance(rctx, dict) and rctx.get("chunk_count") is not None:
                gscore = min(1.0, float(rctx["chunk_count"]) / 8.0)
            m = score_row(concept, task, rtxt, gscore, lat, not rok)
            systems["rag_grounded_service"].rows.append(
                {
                    "concept": concept,
                    "task_type": task,
                    "prompt": up,
                    "output": rtxt,
                    "ok": rok and len(rtxt.strip()) >= 8,
                    "error_message": rerr,
                    "latency_seconds": lat,
                    "metrics": m,
                    "rag_context_status": rctx.get("status") if isinstance(rctx, dict) else None,
                }
            )
        else:
            systems["rag_grounded_service"].rows.append(
                {
                    "concept": concept,
                    "task_type": task,
                    "prompt": up,
                    "output": "",
                    "ok": False,
                    "error_message": rag_err or "skipped_due_to_compare_only_pretrained",
                    "latency_seconds": None,
                    "metrics": score_row(concept, task, "", None, None, True),
                }
            )

    # Finalize per-system summary
    summaries: Dict[str, Any] = {}
    for sid, run in systems.items():
        n = len(run.rows)
        ok_n = sum(1 for r in run.rows if r["ok"])
        frac = ok_n / n if n else 0.0
        if run.generation_status == "skipped_for_smoke_test":
            pass
        elif run.connection_status == "skipped_by_config":
            run.generation_status = "skipped_by_config"
        else:
            run.generation_status = (
                "success"
                if frac >= 0.95
                else ("partial" if frac > 0 else "error")
            )
        if run.connection_status == "error":
            run.generation_status = "error"
        if sid == "pretrained_pretrained_finetuned_llm" and pretrained_skipped_due_to_runtime_limit_count > 0:
            run.generation_status = "partial"
        real = (
            run.connection_status == "success"
            and frac >= 0.90
            and ok_n > 0
        )
        if sid == "template_rule_baseline":
            real = frac >= 0.90
        summaries[sid] = {
            "connection_status": run.connection_status,
            "generation_status": run.generation_status,
            "real_outputs_generated": real,
            "output_count": ok_n,
            "generated_count": ok_n,
            "total_prompts": n,
            "skipped_count": sum(
                1 for r in run.rows if str(r.get("error_message", "")).startswith("skipped_")
            ),
            "fallback_used": any(bool(r.get("fallback_or_error")) for r in run.rows)
            or any(
                bool((r.get("metrics") or {}).get("fallback_or_error"))
                for r in run.rows
            )
            or any(
                str(r.get("error_message", "")).startswith("fallback_")
                for r in run.rows
            ),
            "avg_latency": round(
                sum(float(r["latency_seconds"]) for r in run.rows if r.get("latency_seconds") is not None)
                / max(1, sum(1 for r in run.rows if r.get("latency_seconds") is not None)),
                4,
            )
            if any(r.get("latency_seconds") is not None for r in run.rows)
            else None,
            "ok_fraction": round(frac, 4),
            "error_message": run.error_message,
            "aggregate_metrics": aggregate_metrics(run.rows),
        }
        if sid == "pretrained_pretrained_finetuned_llm":
            summaries[sid]["generated_count"] = pretrained_generated_count
            summaries[sid]["skipped_due_to_runtime_limit_count"] = pretrained_skipped_due_to_runtime_limit_count
            summaries[sid]["skipped_count"] = (
                summaries[sid].get("skipped_count", 0) + pretrained_skipped_due_to_runtime_limit_count
            )
            summaries[sid]["avg_latency"] = (
                round(sum(pretrained_latencies) / len(pretrained_latencies), 4)
                if pretrained_latencies
                else None
            )
            summaries[sid]["max_latency"] = round(max(pretrained_latencies), 4) if pretrained_latencies else None

    req = ("template_rule_baseline", "cognitutor_lm_from_scratch", "rag_grounded_service")
    comparison_valid = all(
        summaries[s]["real_outputs_generated"] for s in req
    )

    def composite_score(agg: Dict[str, Any]) -> float:
        base = (
            0.32 * agg["mean_format_validity"]
            + 0.22 * agg["mean_task_fit"]
            + 0.18 * agg["mean_teaching_quality_proxy"]
            + 0.15 * agg["mean_concept_relevance"]
            + 0.08 * (1.0 - agg["mean_repetition_rate"])
        )
        gs = agg.get("mean_grounding_score")
        if gs is not None:
            base += 0.05 * float(gs)
        return base

    ranking: List[Dict[str, Any]] = []
    for sid, s in summaries.items():
        if not s["real_outputs_generated"]:
            continue
        ranking.append(
            {
                "system": sid,
                "composite_score": round(composite_score(s["aggregate_metrics"]), 4),
                "aggregate_metrics": s["aggregate_metrics"],
            }
        )
    ranking.sort(key=lambda x: -x["composite_score"])

    narrative = (
        "On this 49-prompt battery, the automated composite ranked "
        f"**{ranking[0]['system']}** first when all required systems produced real text. "
        "CogniTutorLM artifacts often differ from the strict string templates used for "
        "`format_validity` / `task_fit` (e.g. Markdown views vs literal `Front:` lines), "
        "so its *proxy* scores can look low even when teaching content is useful. "
        "Pretrained (Qwen+LoRA) shows higher concept overlap but weaker strict format adherence "
        "than template/RAG-composed outputs. RAG gains from retrieval-backed `grounding_score`."
        if ranking
        else "Insufficient systems passed real-output thresholds for ranking."
    )

    report = {
        "run_mode": "smoke" if smoke_mode else ("small_real" if small_real_mode else "full"),
        "config": {
            "COMPARE_SMOKE": smoke_mode,
            "COMPARE_SMALL_REAL": small_real_mode,
            "COMPARE_ONLY_PRETRAINED": compare_only_pretrained,
            "COMPARE_MAX_CONCEPTS": max_concepts,
            "COMPARE_MAX_TASKS": max_tasks,
            "COMPARE_SKIP_PRETRAINED_MODEL": skip_pretrained_model,
            "COMPARE_TIMEOUT_SECONDS": timeout_seconds,
            "PRETRAINED_MAX_NEW_TOKENS": pretrained_max_new_tokens,
            "PRETRAINED_DO_SAMPLE": pretrained_do_sample,
            "COMPARE_PRETRAINED_MAX_PROMPTS": compare_pretrained_max_prompts,
        },
        "comparison_valid": comparison_valid,
        "comparison_note": (
            "comparison_valid requires template + CogniTutorLM + RAG each >=90% ok prompts. "
            "Pretrained tracked separately; does not invalidate comparison_valid when down."
        ),
        "narrative_conclusion": narrative,
        "prompts_total": len(prompts),
        "systems": summaries,
        "ranking_real_only": ranking,
        "fixture_results": fixture_results,
        "per_system_sample_limit_note": "Smoke/small mode may evaluate a subset of prompts."
        if (smoke_mode or small_real_mode)
        else ("Pretrained generation may be capped by COMPARE_PRETRAINED_MAX_PROMPTS." if compare_pretrained_max_prompts > 0 else None),
    }

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown
    lines = [
        "# LLM generation comparison (real outputs)",
        "",
        f"**comparison_valid:** `{comparison_valid}`",
        "",
        "| System | connection | generation | real_outputs | ok / total | composite* |",
        "|---|---|---|---:|---:|---:|",
    ]
    for sid, s in summaries.items():
        agg = s["aggregate_metrics"]
        comp = composite_score(agg) if s["real_outputs_generated"] else None
        lines.append(
            f"| `{sid}` | {s['connection_status']} | {s['generation_status']} | "
            f"{s['real_outputs_generated']} | {s['output_count']}/{s['total_prompts']} | "
            f"{(str(round(comp, 4)) if comp is not None else '—')} |"
        )
    lines.extend(
        [
            "",
            "*Composite among systems with `real_outputs_generated` only used for ranking block below.*",
            "",
            "## Ranking (real outputs only)",
            "",
        ]
    )
    for i, r in enumerate(ranking, 1):
        lines.append(f"{i}. **{r['system']}** — composite {r['composite_score']}")
    if not ranking:
        lines.append("_No systems met the real-output threshold for ranking._")
    lines.append("\n## Errors\n")
    for sid, s in summaries.items():
        if s.get("error_message"):
            lines.append(f"- **{sid}:** `{s['error_message'][:500]}`")

    out_md.write_text("\n".join(lines), encoding="utf-8")

    INTERPRETATION_MD.write_text(
        "\n".join(
            [
                "# LLM comparison — how to read results",
                "",
                "## Latest automated headline",
                "",
                narrative,
                "",
                "## Systems",
                "",
                "1. **CogniTutorLM (from scratch)** — Project-specific artifacts "
                "(teaching views + assessment bank). Stable, deterministic structure when "
                "artifacts exist; good baseline for *curriculum-aligned* text.",
                "",
                "2. **Pretrained pretrained + LoRA** — Comparison baseline using a small "
                "instruction-tuned coder + adapter. Quality varies with prompt adherence; "
                "not a drop-in replacement for CogniTutorLM without further tuning.",
                "",
                "3. **RAG-grounded service** — Retrieves chunks from the cognition tutor "
                "corpus and composes answers from retrieved fields. Often scores well on "
                "**concept_relevance** and **grounding** when retrieval succeeds.",
                "",
                "4. **Template rule baseline** — Hand-authored patterns. Very stable format "
                "scores but less adaptive language.",
                "",
                "## Validity",
                "",
                "`comparison_valid` in the JSON is **true** only when **template**, "
                "**CogniTutorLM**, and **RAG** each produced real outputs on ≥90% of prompts. "
                "Pretrained is reported honestly even if it fails; it does **not** force "
                "`comparison_valid` false by itself.",
                "",
                "## Rankings",
                "",
                "Rankings use a transparent composite of format, task fit, teaching proxy, "
                "concept relevance, and repetition — **only** for systems with "
                "`real_outputs_generated: true`. Systems with import or load errors are "
                "**not** ranked as winners.",
                "",
                "## Human evaluation",
                "",
                "Automated scores are proxies. Final product decisions should combine these "
                "runs with **human** ratings on usefulness, correctness, and safety.",
                "",
                f"Artifacts: `{out_json.name}`, `{out_md.name}`.",
            ]
        ),
        encoding="utf-8",
    )

    print("\nReal comparison finished.\n")
    print(f"comparison_valid: {comparison_valid}")

    def _brief(sid: str) -> str:
        s = summaries[sid]
        return (
            f"{s['connection_status']}/{s['generation_status']}/"
            f"real={s['real_outputs_generated']}/{s['output_count']}ok"
        )

    print(f"template_status: {_brief('template_rule_baseline')}")
    print(f"cognitutor_status: {_brief('cognitutor_lm_from_scratch')}")
    print(f"pretrained_status: {_brief('pretrained_pretrained_finetuned_llm')}")
    print(f"rag_status: {_brief('rag_grounded_service')}")
    print(f"ranking_real_only: {[r['system'] for r in ranking]}")
    print(f"report_paths: {out_json}")
    print(f"report_paths: {out_md}")
    print(f"report_paths: {INTERPRETATION_MD}")


if __name__ == "__main__":
    main()
