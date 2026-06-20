from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from tutor.generation.cognitutor_lm_connector import get_cognitutor_service
from tutor.generation.sanvia_finetuned_connector import SanviaFinetunedConnector


TASK_TYPES = [
    "explanation",
    "revision",
    "flashcard",
    "mindmap",
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "hint",
    "feedback",
    "doubt_answer",
]

SAMPLE_CONCEPTS = [
    {"concept_id": "P1", "concept_name": "Variables", "domain": "Python", "context": "Variables store values and names cannot start with digits."},
    {"concept_id": "SQL1", "concept_name": "SELECT", "domain": "SQL", "context": "SELECT retrieves columns and rows from database tables."},
    {"concept_id": "HTML1", "concept_name": "Tags and Elements", "domain": "HTML", "context": "HTML tags mark elements such as headings, paragraphs, and links."},
    {"concept_id": "G1", "concept_name": "Commits", "domain": "Git", "context": "A commit records a snapshot of staged project changes."},
    {"concept_id": "DS1", "concept_name": "Arrays", "domain": "Data Structures", "context": "Arrays store indexed values in contiguous positions conceptually."},
]

STRUCTURED_TASKS = {"mcq", "flashcard", "mindmap", "debug_task", "output_prediction", "challenge_question"}


def _words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(w) > 2]


def _json_valid(text: str) -> bool:
    try:
        json.loads(str(text or "").strip())
        return True
    except Exception:
        return False


def _flatten_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _repetition_rate(text: str) -> float:
    lines = [line.strip().lower() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) <= 1:
        tokens = _words(text)
        if not tokens:
            return 1.0
        counts = Counter(tokens)
        repeated = sum(count - 1 for count in counts.values() if count > 1)
        return round(min(repeated / max(len(tokens), 1), 1.0), 4)
    counts = Counter(lines)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return round(repeated / len(lines), 4)


def _format_validity(task_type: str, output: str) -> float:
    text = str(output or "").strip()
    if not text:
        return 0.0
    if task_type in {"mcq", "flashcard", "mindmap", "debug_task", "output_prediction", "challenge_question"}:
        if _json_valid(text):
            return 1.0
        expected = {
            "mcq": ["question", "options", "answer"],
            "flashcard": ["front", "back"],
            "mindmap": ["central", "branches"],
            "debug_task": ["buggy", "fix", "hint"],
            "output_prediction": ["code", "output", "answer"],
            "challenge_question": ["challenge", "solution"],
        }[task_type]
        hits = sum(1 for key in expected if key in text.lower())
        return round(hits / len(expected), 4)
    return 1.0 if len(text) >= 30 else 0.5


def _keyword_score(output: str, concept: dict) -> float:
    out_words = set(_words(output))
    expected = set(_words(f"{concept.get('concept_name')} {concept.get('domain')} {concept.get('context')}"))
    if not expected:
        return 0.0
    return round(len(out_words & expected) / min(len(expected), 12), 4)


def _fallback_detected(result: Dict[str, Any], output: str) -> bool:
    markers = ["fallback", "not available", "unavailable", "template_baseline"]
    return bool(result.get("fallback_used")) or any(marker in str(output or "").lower() for marker in markers)


class LLMGenerationComparator:
    def __init__(self):
        self.sanvia = SanviaFinetunedConnector()
        self._cognitutor_service = None

    def compare_all(self) -> Dict[str, Any]:
        results = []
        for concept in SAMPLE_CONCEPTS:
            for task_type in TASK_TYPES:
                for service_name in self.service_names():
                    results.append(self._evaluate_service(service_name, task_type, concept))
        averages = self._service_averages(results)
        return {
            "status": "success",
            "module": "cognitutor_vs_sanvia_comparison",
            "evaluation_wording": (
                "The generation module was evaluated by comparing multiple generation services: deterministic/template generation, "
                "RAG-grounded generation, CogniTutorLM from scratch, and Sanvia's pretrained fine-tuned LLM as an inspected comparison-only candidate when a safe local inference path was available. "
                "The comparison used automatic proxy metrics including output availability, format validity, grounding, relevance, task success, fallback rate, "
                "repetition, and latency across tutor tasks such as explanations, MCQs, debugging tasks, output prediction, flashcards, mindmaps, hints, feedback, "
                "and doubt answers. Since automatic metrics cannot fully replace human judgement, the results are interpreted as model/service comparison evidence "
                "rather than final human quality evaluation."
            ),
            "services": self.service_statuses(),
            "sanvia_inspection": self.sanvia.inspect_artifacts(),
            "task_types": TASK_TYPES,
            "sample_concepts": SAMPLE_CONCEPTS,
            "results": results,
            "service_averages": averages,
            "best_service_by_task_type": self._best_by_task(results),
            "limitations": [
                "Automatic metrics are proxy metrics and should be supplemented by human evaluation.",
                "No external API calls or model downloads were used.",
                "Unavailable services are scored as unavailable rather than supplied with fake outputs.",
                "Sanvia is not connected to live tutor runtime; it remains comparison-only and pending until a matching local base model or merged model exists.",
            ],
            "final_recommendation": self._recommendation(averages),
        }

    def service_names(self) -> List[str]:
        return [
            "template_rule_generator",
            "rag_grounded_service",
            "cognitutor_lm_from_scratch",
            "sanvia_pretrained_finetuned_llm",
        ]

    def service_statuses(self) -> Dict[str, Any]:
        cog = self._cognitutor_status()
        sanvia = self.sanvia.is_available()
        return {
            "template_rule_generator": {"status": "success", "available": True, "connector_mode": "template"},
            "rag_grounded_service": {"status": "success", "available": True, "connector_mode": "service_or_template_with_rag_metadata"},
            "cognitutor_lm_from_scratch": cog,
            "sanvia_pretrained_finetuned_llm": sanvia,
        }

    def _cognitutor_status(self) -> Dict[str, Any]:
        try:
            service = self._get_cognitutor_service()
            content_mode = getattr(service, "content_mode", "unknown")
            structured_ready = bool(getattr(service, "structured_model_items", []))
            return {
                "status": "success",
                "available": True,
                "content_mode": content_mode,
                "model_generated": bool(content_mode == "structured_model_generated" and structured_ready),
                "connector_mode": "model" if content_mode == "structured_model_generated" and structured_ready else "template/service",
                "limitations": [] if structured_ready else ["Current main connector is serving packet/template artifacts unless TUTOR_CONTENT_MODE=structured_model_generated passes gates."],
            }
        except Exception as exc:
            return {"status": "warning", "available": False, "model_generated": "unknown", "connector_mode": "unavailable", "reason": f"{type(exc).__name__}: {exc}"}

    def _get_cognitutor_service(self):
        if self._cognitutor_service is None:
            self._cognitutor_service = get_cognitutor_service()
        return self._cognitutor_service

    def _evaluate_service(self, service_name: str, task_type: str, concept: dict) -> Dict[str, Any]:
        started = time.time()
        result = self._generate(service_name, task_type, concept)
        latency_ms = result.get("latency_ms")
        if latency_ms is None:
            latency_ms = (time.time() - started) * 1000
        output = _flatten_output(result.get("output"))
        available = bool(result.get("available", result.get("status") == "success"))
        fallback = _fallback_detected(result, output)
        relevance = _keyword_score(output, concept) if available else 0.0
        grounding = _keyword_score(output, {"concept_name": concept.get("concept_name"), "domain": concept.get("domain"), "context": concept.get("context")}) if available else 0.0
        fmt = _format_validity(task_type, output) if available else 0.0
        repetition = _repetition_rate(output) if output else 1.0
        output_rate = 1.0 if output else 0.0
        task_success = 1.0 if output and fmt >= 0.5 and relevance > 0 else 0.0
        quality = max(0.0, min(1.0, (0.25 * fmt) + (0.25 * task_success) + (0.25 * relevance) + (0.15 * grounding) + (0.10 * (1.0 - repetition))))
        return {
            "service": service_name,
            "task_type": task_type,
            "concept_name": concept["concept_name"],
            "domain": concept["domain"],
            "status": result.get("status", "warning"),
            "available": available,
            "reason": result.get("reason"),
            "output_preview": output[:500],
            "metrics": {
                "availability": 1.0 if available else 0.0,
                "output_rate": output_rate,
                "format_validity": round(fmt, 4),
                "task_success": task_success,
                "grounding_score": round(grounding, 4),
                "relevance_score": round(relevance, 4),
                "quality_score": round(quality, 4),
                "repetition_rate": repetition,
                "fallback_rate": 1.0 if fallback else 0.0,
                "latency_ms": round(float(latency_ms), 3),
                "json_validity": 1.0 if task_type in STRUCTURED_TASKS and _json_valid(output) else (0.0 if task_type in STRUCTURED_TASKS else None),
                "answer_usefulness_proxy": round((task_success + relevance + fmt) / 3.0, 4),
            },
            "raw_status": {k: v for k, v in result.items() if k != "output"},
        }

    def _generate(self, service_name: str, task_type: str, concept: dict) -> Dict[str, Any]:
        if service_name == "template_rule_generator":
            return {"status": "success", "available": True, "output": self._template_output(task_type, concept), "latency_ms": 0.1, "fallback_used": False}
        if service_name == "rag_grounded_service":
            return self._rag_output(task_type, concept)
        if service_name == "cognitutor_lm_from_scratch":
            return self._cognitutor_output(task_type, concept)
        if service_name == "sanvia_pretrained_finetuned_llm":
            return self.sanvia.generate_task(task_type, concept["concept_name"], concept["domain"], "easy", "simple", concept["context"])
        return {"status": "warning", "available": False, "output": "", "reason": "unknown_service"}

    def _template_output(self, task_type: str, concept: dict) -> str:
        name, domain, ctx = concept["concept_name"], concept["domain"], concept["context"]
        if task_type == "mcq":
            return json.dumps({"question": f"What is {name} used for in {domain}?", "options": ["Store or retrieve relevant information", "Delete all work", "Change the browser", "Ignore syntax"], "answer": "Store or retrieve relevant information", "explanation": ctx})
        if task_type == "flashcard":
            return json.dumps({"front": f"What is {name}?", "back": ctx})
        if task_type == "mindmap":
            return json.dumps({"central": name, "branches": [domain, "definition", "example", "common mistake"]})
        if task_type == "debug_task":
            return json.dumps({"buggy_code": "2score = 10", "expected_fix": "score2 = 10", "hint": f"Apply the rule for {name}.", "explanation": ctx})
        if task_type == "output_prediction":
            return json.dumps({"code": "x = 2\nprint(x)", "question": "What is the output?", "answer": "2", "explanation": f"The code uses {name} in {domain}."})
        if task_type == "challenge_question":
            return json.dumps({"challenge": f"Create a small example using {name} in {domain}.", "solution_outline": ctx})
        return f"{name} in {domain}: {ctx} This {task_type} is concise, relevant, and suitable for an adaptive tutor."

    def _rag_output(self, task_type: str, concept: dict) -> Dict[str, Any]:
        started = time.time()
        output = self._template_output(task_type, concept)
        try:
            service = self._get_cognitutor_service()
            rag = service.build_rag_grounding_metadata(
                query=f"{concept['concept_name']} {task_type}",
                concept_id=concept.get("concept_id"),
                concept_name=concept.get("concept_name"),
                domain=concept.get("domain"),
            )
            previews = " ".join(chunk.get("preview", "") for chunk in rag.get("source_chunks_preview", []))
            if previews:
                output = f"{output}\nGrounding: {previews[:300]}"
            return {"status": "success", "available": True, "output": output, "latency_ms": (time.time() - started) * 1000, "fallback_used": bool(rag.get("fallback_used"))}
        except Exception as exc:
            return {"status": "warning", "available": True, "output": output, "latency_ms": (time.time() - started) * 1000, "fallback_used": True, "reason": f"rag_unavailable: {exc}"}

    def _cognitutor_output(self, task_type: str, concept: dict) -> Dict[str, Any]:
        started = time.time()
        try:
            service = self._get_cognitutor_service()
            model_task = "revision_summary" if task_type == "revision" else task_type
            structured = service.get_structured_model_output(
                concept_name=concept.get("concept_name"),
                domain=concept.get("domain"),
                task_type=model_task,
            )
            if structured.get("status") == "success":
                return {"status": "success", "available": True, "output": structured.get("output"), "latency_ms": (time.time() - started) * 1000, "fallback_used": False, "model_generated": True}
            view = "revision_summary_view" if task_type == "revision" else "definition_view"
            teaching = service.get_teaching_view(concept_name=concept.get("concept_name"), domain=concept.get("domain"), artifact_type=view)
            output = teaching.get("teaching") if teaching.get("status") == "success" else self._template_output(task_type, concept)
            return {"status": "success", "available": True, "output": output, "latency_ms": (time.time() - started) * 1000, "fallback_used": teaching.get("status") != "success", "model_generated": False, "connector_mode": "template/service"}
        except Exception as exc:
            return {"status": "warning", "available": False, "output": "", "latency_ms": (time.time() - started) * 1000, "fallback_used": True, "reason": f"{type(exc).__name__}: {exc}", "model_generated": "unknown"}

    def _service_averages(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        buckets: Dict[str, List[Dict[str, float]]] = defaultdict(list)
        for row in results:
            buckets[row["service"]].append(row["metrics"])
        averages = {}
        for service, metrics_rows in buckets.items():
            keys = [k for k in metrics_rows[0].keys() if metrics_rows[0].get(k) is not None]
            averages[service] = {key: round(sum(float(row.get(key) or 0.0) for row in metrics_rows) / len(metrics_rows), 4) for key in keys}
        return averages

    def _best_by_task(self, results: List[Dict[str, Any]]) -> Dict[str, str]:
        best = {}
        for task in TASK_TYPES:
            rows = [r for r in results if r["task_type"] == task and r["available"]]
            if not rows:
                best[task] = "none_available"
                continue
            rows.sort(key=lambda r: (r["metrics"]["quality_score"], -r["metrics"]["fallback_rate"], -r["metrics"]["latency_ms"]), reverse=True)
            best[task] = rows[0]["service"]
        return best

    def _recommendation(self, averages: Dict[str, Any]) -> str:
        sanvia_available = self.sanvia.is_available().get("available")
        cog_quality = averages.get("cognitutor_lm_from_scratch", {}).get("quality_score", 0.0)
        sanvia_quality = averages.get("sanvia_pretrained_finetuned_llm", {}).get("quality_score", 0.0)
        if not sanvia_available:
            return "Sanvia is not connected to live tutor runtime. Keep it as a comparison-only pending candidate until a safe local base model or merged model artifact exists. Continue using CogniTutorLM/template/RAG paths for live backend support, with deterministic/RAG-grounded fallback for safety."
        if sanvia_quality > cog_quality:
            return "Sanvia is locally runnable and scored higher on proxy metrics; use it only in comparison mode behind validation checks. Always keep deterministic/RAG-grounded template fallback for safety."
        return "CogniTutorLM from scratch provides project-specific controlled generation and should be used as the local tutor generation/comparison service. Always keep deterministic/RAG-grounded template fallback for safety."
