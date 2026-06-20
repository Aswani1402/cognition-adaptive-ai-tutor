import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ROOT_DIR = Path(__file__).resolve().parents[1]

ARTIFACTS_PATH = ROOT_DIR / "outputs" / "artifacts" / "generated_tutor_artifacts.json"
QUESTION_BANK_PATH = ROOT_DIR / "outputs" / "question_bank" / "assessment_question_bank.json"
OUTPUT_DIR = ROOT_DIR / "outputs" / "quality"
JSON_REPORT_PATH = OUTPUT_DIR / "generation_quality_report.json"
MD_REPORT_PATH = OUTPUT_DIR / "generation_quality_report.md"

DB_CONFIGS = [
    {"path": ROOT_DIR / "data" / "raw" / "python_learning.db", "domain": "Python"},
    {"path": ROOT_DIR / "data" / "raw" / "database_sql.db", "domain": "SQL"},
    {"path": ROOT_DIR / "data" / "raw" / "html_web_basics.db", "domain": "HTML"},
    {"path": ROOT_DIR / "data" / "raw" / "git_version_control.db", "domain": "Git"},
    {"path": ROOT_DIR / "data" / "raw" / "data_structures.db", "domain": "Data Structures"},
]

TEACHING_TYPES = [
    "definition_view",
    "simple_example_view",
    "step_by_step_view",
    "code_view",
    "analogy_view",
    "misconception_view",
    "debug_view",
    "output_prediction_view",
    "transfer_view",
    "challenge_view",
    "revision_summary_view",
    "flashcard_view",
    "mindmap_view",
]

QUESTION_TYPES = {
    "mcq",
    "debug_task",
    "output_prediction",
    "transfer_question",
    "challenge_question",
    "explanation_check",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "used",
    "uses",
    "when",
    "where",
    "which",
    "with",
    "you",
    "your",
}

GENERIC_PHRASES = [
    "main idea",
    "this concept",
    "the concept",
    "important concept",
    "in real-world problem solving",
    "use a simple example from the topic",
    "create a short code or command example",
    "explain what happens in your own words",
]

UNKNOWN_CONCEPT_PATTERNS = [
    "unknown concept",
    "unknown_concept",
    "concept name",
    "placeholder concept",
]

DOMAIN_KEYWORDS = {
    "Python": {
        "python",
        "variable",
        "list",
        "dict",
        "function",
        "class",
        "loop",
        "print",
        "def",
        "object",
        "decorator",
        "generator",
        "file",
    },
    "SQL": {
        "sql",
        "database",
        "table",
        "row",
        "column",
        "select",
        "where",
        "join",
        "index",
        "query",
        "cte",
        "primary",
        "foreign",
    },
    "HTML": {
        "html",
        "tag",
        "element",
        "attribute",
        "browser",
        "web",
        "doctype",
        "form",
        "input",
        "link",
        "accessibility",
        "dom",
    },
    "Git": {
        "git",
        "commit",
        "branch",
        "merge",
        "repository",
        "repo",
        "rebase",
        "clone",
        "push",
        "pull",
        "conflict",
        "submodule",
    },
    "Data Structures": {
        "data",
        "structure",
        "array",
        "linked",
        "list",
        "stack",
        "queue",
        "tree",
        "graph",
        "set",
        "node",
        "edge",
        "complexity",
    },
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def text_from(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(text_from(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(text_from(v) for v in value)
    return str(value)


def json_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value or "")


def normalize_space(text: Any) -> str:
    return " ".join(str(text or "").replace("\r", "\n").split()).strip()


def normalize_for_duplicate(value: Any) -> str:
    text = json_text(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def tokens(value: Any) -> List[str]:
    raw = text_from(value).lower()
    found = re.findall(r"[a-z][a-z0-9_]{2,}", raw)
    return [token for token in found if token not in STOPWORDS]


def keyword_set(value: Any) -> Set[str]:
    return set(tokens(value))


def token_overlap_score(text_value: Any, reference_value: Any) -> float:
    text_tokens = keyword_set(text_value)
    ref_tokens = keyword_set(reference_value)
    if not text_tokens or not ref_tokens:
        return 0.0

    overlap = len(text_tokens & ref_tokens)
    score = overlap / max(6, min(len(text_tokens), len(ref_tokens)))
    return clamp(score)


def jaccard(value_a: Any, value_b: Any) -> float:
    set_a = keyword_set(value_a)
    set_b = keyword_set(value_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def has_code_like_content(text: str, domain: str) -> bool:
    code_markers = [
        "```",
        "=",
        "()",
        "print(",
        "def ",
        "class ",
        "for ",
        "while ",
        "if ",
        "select ",
        "insert ",
        "create table",
        "<",
        "</",
        "git ",
        "->",
    ]
    lowered = text.lower()
    if re.search(r"\b[a-zA-Z_][a-zA-Z0-9_\.]*\s*\(", text):
        return True
    if domain == "Git":
        return "git " in lowered or lowered.startswith("git")
    if domain in {"Python", "SQL", "HTML"}:
        return any(marker in lowered for marker in code_markers)
    return any(marker in lowered for marker in ["=", "push", "pop", "enqueue", "dequeue", "node", "edge"])


def has_ordered_steps(text: str) -> bool:
    lowered = text.lower()
    if len(re.findall(r"\bstep\s+\d+\b", lowered)) >= 2:
        return True
    if len(re.findall(r"(^|\n)\s*\d+[\.)]", text)) >= 2:
        return True
    return False


def has_example_signal(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in [
            "example",
            "for instance",
            "such as",
            "like ",
            "suppose",
            "e.g.",
            "try",
            "input",
            "output",
        ]
    )


def has_analogy_signal(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in [
            "like a",
            "like an",
            "similar to",
            "imagine",
            "think of",
            "as if",
            "analogy",
        ]
    )


def has_bug_fix_signal(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ["bug", "fix", "error", "wrong", "incorrect", "hint"])


def has_correction_signal(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in ["misconception", "mistake", "wrong", "actually", "correction", "instead"])


def load_grounding_resources() -> Dict[Tuple[str, str], Dict[str, str]]:
    resources: Dict[Tuple[str, str], Dict[str, str]] = {}

    for config in DB_CONFIGS:
        db_path = config["path"]
        domain = config["domain"]
        if not db_path.exists():
            continue

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT concept_id, topic, base_content, examples, key_points,
                       misconceptions, real_world_use, next_concept_link
                FROM concept_resources
                """
            ).fetchall()
        finally:
            conn.close()

        for row in rows:
            resources[(domain, str(row["concept_id"]))] = {
                "concept_name": str(row["topic"] or ""),
                "grounding_text": " ".join(
                    str(row[field] or "")
                    for field in [
                        "topic",
                        "base_content",
                        "examples",
                        "key_points",
                        "misconceptions",
                        "real_world_use",
                        "next_concept_link",
                    ]
                ),
            }

    return resources


def concept_reference(item: Dict[str, Any], resources: Dict[Tuple[str, str], Dict[str, str]]) -> str:
    resource = resources.get((item.get("domain"), item.get("concept_id")), {})
    return " ".join(
        [
            str(item.get("concept_name") or ""),
            str(item.get("domain") or ""),
            resource.get("grounding_text", ""),
        ]
    )


def domain_match_score(text_value: Any, expected_domain: str) -> Tuple[float, Optional[str]]:
    item_tokens = keyword_set(text_value)
    if not item_tokens:
        return 0.0, None

    expected_hits = len(item_tokens & DOMAIN_KEYWORDS.get(expected_domain, set()))
    other_hits = {
        domain: len(item_tokens & words)
        for domain, words in DOMAIN_KEYWORDS.items()
        if domain != expected_domain
    }
    strongest_other_domain, strongest_other_hits = max(other_hits.items(), key=lambda pair: pair[1])

    if expected_hits == 0 and strongest_other_hits >= 2:
        return 0.2, strongest_other_domain
    if strongest_other_hits >= expected_hits + 4 and strongest_other_hits >= 5:
        return 0.35, strongest_other_domain
    if expected_hits >= 2:
        return 1.0, None
    if expected_hits == 1:
        return 0.8, None
    return 0.65, None


def clarity_score(text_value: Any, min_chars: int) -> Tuple[float, List[str]]:
    text = normalize_space(text_from(text_value))
    lowered = text.lower()
    issues = []
    score = 1.0

    if len(text) < min_chars:
        issues.append("too_short")
        score -= 0.35
    if any(phrase in lowered for phrase in GENERIC_PHRASES):
        issues.append("too_generic")
        score -= 0.25
    if any(pattern in lowered for pattern in UNKNOWN_CONCEPT_PATTERNS):
        issues.append("unknown_concept_leak")
        score -= 0.65
    if len(set(tokens(text))) < 8:
        issues.append("too_generic")
        score -= 0.15

    return clamp(score), sorted(set(issues))


def style_expectation_score(artifact: Dict[str, Any]) -> Tuple[float, List[str]]:
    artifact_type = artifact.get("artifact_type")
    domain = str(artifact.get("domain") or "")
    output = artifact.get("output")
    text = text_from(output)
    lowered = text.lower()
    issues = []
    score = 1.0

    if artifact_type == "definition_view":
        if not any(marker in lowered for marker in ["definition", "is ", "means", "refers to"]):
            score -= 0.35
            issues.append("style_mismatch")
    elif artifact_type == "simple_example_view":
        if not has_example_signal(text):
            score -= 0.45
            issues.append("missing_example")
    elif artifact_type == "step_by_step_view":
        if not has_ordered_steps(text):
            score -= 0.45
            issues.append("style_mismatch")
    elif artifact_type == "code_view":
        if domain in {"Python", "SQL", "HTML", "Git"} and not has_code_like_content(text, domain):
            score -= 0.5
            issues.append("style_mismatch")
    elif artifact_type == "analogy_view":
        if not has_analogy_signal(text):
            score -= 0.55
            issues.append("weak_analogy")
    elif artifact_type == "misconception_view":
        if not has_correction_signal(text):
            score -= 0.5
            issues.append("style_mismatch")
    elif artifact_type == "debug_view":
        if not isinstance(output, dict) or not has_bug_fix_signal(text):
            score -= 0.5
            issues.append("style_mismatch")
    elif artifact_type == "output_prediction_view":
        if not isinstance(output, dict) or not output.get("code") or not output.get("answer"):
            score -= 0.55
            issues.append("style_mismatch")
    elif artifact_type == "transfer_view":
        if not any(marker in lowered for marker in ["real", "apply", "new", "scenario", "project", "system"]):
            score -= 0.35
            issues.append("style_mismatch")
    elif artifact_type == "challenge_view":
        if not any(marker in lowered for marker in ["challenge", "harder", "complex", "edge", "design", "why"]):
            score -= 0.35
            issues.append("difficulty_mismatch")
    elif artifact_type == "revision_summary_view":
        if len(text) > 900 or not any(marker in lowered for marker in ["summary", "recap", "remember", "key"]):
            score -= 0.3
            issues.append("style_mismatch")
    elif artifact_type == "flashcard_view":
        if not isinstance(output, dict) or not output.get("front") or not output.get("back"):
            score -= 0.55
            issues.append("style_mismatch")
        elif len(text) > 500:
            score -= 0.25
            issues.append("too_generic")
    elif artifact_type == "mindmap_view":
        branches = output.get("branches") if isinstance(output, dict) else None
        if not isinstance(branches, list) or len(branches) < 2:
            score -= 0.55
            issues.append("style_mismatch")

    return clamp(score), sorted(set(issues))


def example_quality_score(artifact: Dict[str, Any]) -> Tuple[float, List[str]]:
    artifact_type = artifact.get("artifact_type")
    domain = str(artifact.get("domain") or "")
    output = artifact.get("output")
    text = text_from(output)
    lowered = text.lower()
    issues = []
    score = 1.0

    if artifact_type in {"simple_example_view", "analogy_view", "transfer_view"}:
        if not has_example_signal(text) and artifact_type != "analogy_view":
            score -= 0.45
            issues.append("missing_example")
        if artifact_type == "analogy_view" and not has_analogy_signal(text):
            score -= 0.55
            issues.append("weak_analogy")
        relatable_hits = sum(
            marker in lowered
            for marker in [
                "box",
                "plate",
                "checkpoint",
                "table",
                "student",
                "shop",
                "browser",
                "project",
                "file",
                "order",
                "queue",
                "contact",
                "website",
            ]
        )
        if relatable_hits == 0:
            score -= 0.2
    elif artifact_type in {"code_view", "debug_view", "output_prediction_view"}:
        if not has_code_like_content(text, domain):
            score -= 0.45
            issues.append("missing_example")

    return clamp(score), sorted(set(issues))


def difficulty_match_score(item: Dict[str, Any], text_value: Any, is_question: bool = False) -> Tuple[float, List[str]]:
    difficulty = str(item.get("difficulty") or "").lower()
    text = normalize_space(text_from(text_value))
    issues = []

    if not difficulty or difficulty == "adaptive":
        return 0.9, issues

    length = len(text)
    advanced_signals = len(
        re.findall(
            r"\b(edge|optimi[sz]e|complex|tradeoff|design|analy[sz]e|debug|apply|compare|why|explain|identify|justify|modify|predict)\b",
            text.lower(),
        )
    )

    if difficulty == "easy":
        score = 1.0 if length <= 700 and advanced_signals <= 2 else 0.7
    elif difficulty == "medium":
        score = 1.0 if 80 <= length <= 1200 else 0.75
    elif difficulty in {"hard", "challenge"}:
        score = 1.0 if length >= 120 or advanced_signals >= 1 else 0.55
    else:
        score = 0.85

    if is_question and item.get("question_type") == "challenge_question" and advanced_signals == 0:
        score -= 0.25
    if score < 0.7:
        issues.append("difficulty_mismatch")

    return clamp(score), issues


def inspect_teaching_artifacts(
    artifacts: List[Dict[str, Any]],
    resources: Dict[Tuple[str, str], Dict[str, str]],
) -> Dict[str, Any]:
    by_concept: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    exact_seen: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for artifact in artifacts:
        by_concept[
            (
                str(artifact.get("domain") or ""),
                str(artifact.get("concept_id") or ""),
                str(artifact.get("concept_name") or ""),
            )
        ].append(artifact)
        exact_seen[normalize_for_duplicate(artifact.get("output"))].append(artifact)

    variation_by_id: Dict[int, Tuple[float, List[str]]] = {}
    concept_variation_reports = []

    for concept_key, items in by_concept.items():
        items_by_type = {item.get("artifact_type"): item for item in items}
        similarities = []
        duplicate_issues = defaultdict(list)

        for index, item_a in enumerate(items):
            max_similarity = 0.0
            for item_b in items[index + 1 :]:
                sim = jaccard(item_a.get("output"), item_b.get("output"))
                similarities.append(sim)
                max_similarity = max(max_similarity, sim)
                if sim >= 0.82:
                    duplicate_issues[id(item_a)].append("duplicate_content")
                    duplicate_issues[id(item_b)].append("duplicate_content")
            if id(item_a) not in duplicate_issues:
                duplicate_issues[id(item_a)] = []

        expected_pairs = [
            ("definition_view", "code_view"),
            ("code_view", "debug_view"),
            ("debug_view", "output_prediction_view"),
            ("revision_summary_view", "flashcard_view"),
        ]
        for left, right in expected_pairs:
            if left in items_by_type and right in items_by_type:
                sim = jaccard(items_by_type[left].get("output"), items_by_type[right].get("output"))
                if sim >= 0.7:
                    duplicate_issues[id(items_by_type[left])].append("duplicate_content")
                    duplicate_issues[id(items_by_type[right])].append("duplicate_content")

        for item in items:
            max_sim = max(
                [
                    jaccard(item.get("output"), other.get("output"))
                    for other in items
                    if other is not item
                ]
                or [0.0]
            )
            score = clamp(1.0 - max(0.0, max_sim - 0.45) / 0.45)
            if duplicate_issues[id(item)]:
                score = min(score, 0.45)
            variation_by_id[id(item)] = (score, sorted(set(duplicate_issues[id(item)])))

        concept_variation_reports.append(
            {
                "domain": concept_key[0],
                "concept_id": concept_key[1],
                "concept_name": concept_key[2],
                "average_pair_similarity": round(sum(similarities) / len(similarities), 3)
                if similarities
                else 0.0,
                "max_pair_similarity": round(max(similarities), 3) if similarities else 0.0,
            }
        )

    item_reports = []
    all_issues = []

    for artifact in artifacts:
        output = artifact.get("output")
        text = text_from(output)
        reference = concept_reference(artifact, resources)

        concept_score = max(
            token_overlap_score(text, reference),
            0.85 if str(artifact.get("concept_name") or "").lower() in text.lower() else 0.0,
        )
        if concept_score < 0.35:
            concept_score = 0.35

        domain_score, wrong_domain = domain_match_score(text, str(artifact.get("domain") or ""))
        style_score, style_issues = style_expectation_score(artifact)
        clarity, clarity_issues = clarity_score(output, 50 if artifact.get("artifact_type") != "flashcard_view" else 20)
        example_score, example_issues = example_quality_score(artifact)
        difficulty_score, difficulty_issues = difficulty_match_score(artifact, output)
        variation_score, variation_issues = variation_by_id.get(id(artifact), (0.8, []))
        grounding_score = max(token_overlap_score(text, reference), 0.4 if reference else 0.65)

        issues = sorted(
            set(style_issues + clarity_issues + example_issues + difficulty_issues + variation_issues)
        )
        if domain_score < 0.5:
            issues.append("wrong_domain")
        if grounding_score < 0.35:
            issues.append("not_grounded")

        scores = {
            "concept_relevance_score": round(clamp(concept_score), 3),
            "domain_match_score": round(domain_score, 3),
            "view_style_match_score": round(style_score, 3),
            "clarity_score": round(clarity, 3),
            "example_quality_score": round(example_score, 3),
            "difficulty_match_score": round(difficulty_score, 3),
            "variation_score": round(variation_score, 3),
            "grounding_score": round(grounding_score, 3),
        }
        overall = (
            scores["concept_relevance_score"] * 0.18
            + scores["domain_match_score"] * 0.12
            + scores["view_style_match_score"] * 0.18
            + scores["clarity_score"] * 0.14
            + scores["example_quality_score"] * 0.1
            + scores["difficulty_match_score"] * 0.08
            + scores["variation_score"] * 0.12
            + scores["grounding_score"] * 0.08
        )
        scores["overall_quality_score"] = round(clamp(overall), 3)

        report_item = {
            "domain": artifact.get("domain"),
            "concept_id": artifact.get("concept_id"),
            "concept_name": artifact.get("concept_name"),
            "artifact_type": artifact.get("artifact_type"),
            "scores": scores,
            "issues": sorted(set(issues)),
            "critical": "unknown_concept_leak" in issues or "wrong_domain" in issues,
            "preview": normalize_space(text)[:260],
        }
        if wrong_domain:
            report_item["suspected_wrong_domain"] = wrong_domain
        item_reports.append(report_item)

        for issue in report_item["issues"]:
            all_issues.append(
                {
                    "scope": "teaching",
                    "issue": issue,
                    "domain": artifact.get("domain"),
                    "concept_id": artifact.get("concept_id"),
                    "concept_name": artifact.get("concept_name"),
                    "artifact_type": artifact.get("artifact_type"),
                    "score": scores["overall_quality_score"],
                    "preview": report_item["preview"],
                }
            )

    average = round(
        sum(item["scores"]["overall_quality_score"] for item in item_reports) / max(1, len(item_reports)),
        3,
    )

    return {
        "total_artifacts_checked": len(artifacts),
        "average_teaching_quality_score": average,
        "issue_count": len(all_issues),
        "issue_type_counts": dict(Counter(issue["issue"] for issue in all_issues)),
        "issues": all_issues,
        "lowest_quality_items": sorted(
            item_reports,
            key=lambda item: item["scores"]["overall_quality_score"],
        )[:20],
        "items": item_reports,
        "concept_variation_reports": sorted(
            concept_variation_reports,
            key=lambda item: item["max_pair_similarity"],
            reverse=True,
        )[:30],
    }


def question_payload(item: Dict[str, Any]) -> Any:
    return item.get("question_json") if item.get("question_json") is not None else item.get("question_text")


def answer_text(item: Dict[str, Any]) -> str:
    answer_key = item.get("answer_key_json")
    if isinstance(answer_key, dict):
        for field in ["answer", "expected_fix", "expected_output", "output", "expected_key_points"]:
            if answer_key.get(field) is not None:
                return text_from(answer_key.get(field))
    qjson = item.get("question_json")
    if isinstance(qjson, dict):
        for field in ["answer", "expected_fix", "expected_output", "output", "expected_key_points"]:
            if qjson.get(field) is not None:
                return text_from(qjson.get(field))
    return ""


def mcq_distractor_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
    options = qjson.get("options")
    answer = qjson.get("answer")
    issues = []

    if not isinstance(options, list) or len(options) != 4 or answer not in options:
        return 0.1, ["answer_mismatch", "weak_distractors"]
    if len(set(options)) != len(options):
        return 0.25, ["weak_distractors"]

    distractors = [option for option in options if option != answer]
    score = 1.0
    answer_tokens = keyword_set(answer)
    similarities = []

    for distractor in distractors:
        lowered = str(distractor).lower()
        if len(str(distractor).strip()) < 8:
            score -= 0.2
        if any(marker in lowered for marker in ["obviously", "always never", "none of the above", "all of the above"]):
            score -= 0.25
        sim = jaccard(answer, distractor)
        similarities.append(sim)
        if str(distractor).strip().lower() == str(answer).strip().lower():
            score -= 0.5
        if answer_tokens and not keyword_set(distractor):
            score -= 0.15

    if all(sim < 0.05 for sim in similarities):
        score -= 0.2
    if all(sim > 0.75 for sim in similarities):
        score -= 0.25

    if score < 0.75:
        issues.append("weak_distractors")

    return clamp(score), issues


def question_type_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    qtype = item.get("question_type")
    payload = question_payload(item)
    text = text_from(payload)
    lowered = text.lower()
    issues = []
    score = 1.0

    if qtype not in QUESTION_TYPES:
        return 0.1, ["style_mismatch"]

    if qtype == "mcq":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        if not qjson.get("question") or not qjson.get("options") or not qjson.get("answer"):
            score -= 0.6
            issues.append("answer_mismatch")
    elif qtype == "debug_task":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        has_buggy_code = bool(qjson.get("buggy_code"))
        has_expected_fix = bool(qjson.get("expected_fix"))
        if not has_buggy_code or not has_expected_fix or not has_code_like_content(text, str(item.get("domain") or "")):
            score -= 0.55
            issues.append("style_mismatch")
    elif qtype == "output_prediction":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        if not qjson.get("code") or not qjson.get("answer"):
            score -= 0.6
            issues.append("answer_mismatch")
    elif qtype == "transfer_question":
        if not any(marker in lowered for marker in ["apply", "scenario", "project", "real", "use", "choose", "design"]):
            score -= 0.35
            issues.append("style_mismatch")
    elif qtype == "challenge_question":
        if not any(marker in lowered for marker in ["why", "how", "design", "debug", "edge", "tradeoff", "complex"]):
            score -= 0.45
            issues.append("difficulty_mismatch")
    elif qtype == "explanation_check":
        if not any(marker in lowered for marker in ["explain", "why", "describe", "reason"]):
            score -= 0.35
            issues.append("style_mismatch")

    return clamp(score), sorted(set(issues))


def answer_correctness_signal_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    qtype = item.get("question_type")
    payload = question_payload(item)
    answer = answer_text(item)
    issues = []
    score = 1.0

    if not answer:
        return 0.2, ["answer_mismatch"]

    if qtype == "mcq":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        options = qjson.get("options")
        if not isinstance(options, list) or qjson.get("answer") not in options:
            score -= 0.65
            issues.append("answer_mismatch")
        if isinstance(item.get("answer_key_json"), dict) and item["answer_key_json"].get("answer") != qjson.get("answer"):
            score -= 0.45
            issues.append("answer_mismatch")
    elif qtype == "output_prediction":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        if not qjson.get("code") or qjson.get("answer") is None:
            score -= 0.6
            issues.append("answer_mismatch")
    elif qtype == "debug_task":
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        if not qjson.get("expected_fix"):
            score -= 0.35
            issues.append("answer_mismatch")

    return clamp(score), sorted(set(issues))


def anti_guessing_score(item: Dict[str, Any]) -> Tuple[float, List[str]]:
    qtype = item.get("question_type")
    payload_text = text_from(question_payload(item))
    score = 1.0
    issues = []

    if len(payload_text.strip()) < 35:
        score -= 0.25
    if qtype == "mcq":
        distractor_score, distractor_issues = mcq_distractor_score(item)
        score = min(score, distractor_score)
        issues.extend(distractor_issues)
        question = ""
        qjson = item.get("question_json") if isinstance(item.get("question_json"), dict) else {}
        question = str(qjson.get("question") or "").lower()
        if "best describes" in question and len(question.split()) <= 6:
            score -= 0.15
    else:
        if answer_text(item).lower() in payload_text.lower() and len(answer_text(item)) > 15:
            score -= 0.2

    if score < 0.7:
        issues.append("too_generic")

    return clamp(score), sorted(set(issues))


def inspect_question_bank(
    questions: List[Dict[str, Any]],
    resources: Dict[Tuple[str, str], Dict[str, str]],
) -> Dict[str, Any]:
    duplicates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in questions:
        duplicates[normalize_for_duplicate(question_payload(item))].append(item)

    duplicate_ids = set()
    for norm, group in duplicates.items():
        if len(group) > 1 and len(norm) > 40:
            duplicate_ids.update(id(item) for item in group)

    item_reports = []
    all_issues = []

    for item in questions:
        payload = question_payload(item)
        payload_text = text_from(payload)
        combined_text = " ".join([payload_text, answer_text(item)])
        reference = concept_reference(item, resources)

        concept_score = max(
            token_overlap_score(combined_text, reference),
            0.85 if str(item.get("concept_name") or "").lower() in combined_text.lower() else 0.0,
        )
        if concept_score < 0.35:
            concept_score = 0.35

        clarity, clarity_issues = clarity_score(payload, 35)
        answer_score, answer_issues = answer_correctness_signal_score(item)
        distractor_score, distractor_issues = (
            mcq_distractor_score(item) if item.get("question_type") == "mcq" else (0.9, [])
        )
        difficulty_score, difficulty_issues = difficulty_match_score(item, payload, is_question=True)
        type_score, type_issues = question_type_score(item)
        anti_guess_score, anti_guess_issues = anti_guessing_score(item)

        issues = sorted(
            set(
                clarity_issues
                + answer_issues
                + distractor_issues
                + difficulty_issues
                + type_issues
                + anti_guess_issues
            )
        )
        if id(item) in duplicate_ids:
            issues.append("duplicate_content")

        scores = {
            "concept_relevance_score": round(clamp(concept_score), 3),
            "answer_correctness_score": round(answer_score, 3),
            "distractor_quality_score": round(distractor_score, 3),
            "difficulty_match_score": round(difficulty_score, 3),
            "question_type_match_score": round(type_score, 3),
            "clarity_score": round(clarity, 3),
            "anti_guessing_score": round(anti_guess_score, 3),
        }
        overall = (
            scores["concept_relevance_score"] * 0.18
            + scores["answer_correctness_score"] * 0.2
            + scores["distractor_quality_score"] * 0.13
            + scores["difficulty_match_score"] * 0.1
            + scores["question_type_match_score"] * 0.16
            + scores["clarity_score"] * 0.12
            + scores["anti_guessing_score"] * 0.11
        )
        scores["overall_quality_score"] = round(clamp(overall), 3)

        report_item = {
            "domain": item.get("domain"),
            "concept_id": item.get("concept_id"),
            "concept_name": item.get("concept_name"),
            "question_type": item.get("question_type"),
            "difficulty": item.get("difficulty"),
            "variant_id": item.get("variant_id"),
            "scores": scores,
            "issues": sorted(set(issues)),
            "critical": "answer_mismatch" in issues,
            "preview": normalize_space(payload_text)[:260],
        }
        item_reports.append(report_item)

        for issue in report_item["issues"]:
            all_issues.append(
                {
                    "scope": "question",
                    "issue": issue,
                    "domain": item.get("domain"),
                    "concept_id": item.get("concept_id"),
                    "concept_name": item.get("concept_name"),
                    "question_type": item.get("question_type"),
                    "variant_id": item.get("variant_id"),
                    "score": scores["overall_quality_score"],
                    "preview": report_item["preview"],
                }
            )

    average = round(
        sum(item["scores"]["overall_quality_score"] for item in item_reports) / max(1, len(item_reports)),
        3,
    )

    return {
        "total_questions_checked": len(questions),
        "average_question_quality_score": average,
        "issue_count": len(all_issues),
        "issue_type_counts": dict(Counter(issue["issue"] for issue in all_issues)),
        "issues": all_issues,
        "lowest_quality_items": sorted(
            item_reports,
            key=lambda item: item["scores"]["overall_quality_score"],
        )[:20],
        "items": item_reports,
    }


def overall_status(teaching: Dict[str, Any], questions: Dict[str, Any]) -> str:
    issue_counts = Counter()
    issue_counts.update(teaching["issue_type_counts"])
    issue_counts.update(questions["issue_type_counts"])

    critical_wrong_domain = sum(
        1 for issue in teaching["issues"] if issue["issue"] == "wrong_domain"
    )
    unknown_leaks = issue_counts.get("unknown_concept_leak", 0)

    pass_rules_met = (
        teaching["average_teaching_quality_score"] >= 0.75
        and questions["average_question_quality_score"] >= 0.75
        and unknown_leaks == 0
        and critical_wrong_domain == 0
    )

    if pass_rules_met:
        return "PASS"
    if (
        teaching["average_teaching_quality_score"] >= 0.65
        and questions["average_question_quality_score"] >= 0.65
        and unknown_leaks == 0
    ):
        return "WARN"
    return "FAIL"


def build_report(teaching: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, Any]:
    issue_counts = Counter()
    issue_counts.update(teaching["issue_type_counts"])
    issue_counts.update(questions["issue_type_counts"])
    status = overall_status(teaching, questions)

    return {
        "summary": {
            "total_artifacts_checked": teaching["total_artifacts_checked"],
            "total_questions_checked": questions["total_questions_checked"],
            "average_teaching_quality_score": teaching["average_teaching_quality_score"],
            "average_question_quality_score": questions["average_question_quality_score"],
            "issue_count": teaching["issue_count"] + questions["issue_count"],
            "issue_type_counts": dict(issue_counts),
            "status": status,
            "pass_rules": {
                "average_teaching_quality_score_min": 0.75,
                "average_question_quality_score_min": 0.75,
                "unknown_concept_leak_required": 0,
                "critical_wrong_domain_required": 0,
            },
        },
        "teaching": teaching,
        "questions": questions,
        "lowest_quality_items": {
            "teaching": teaching["lowest_quality_items"][:10],
            "questions": questions["lowest_quality_items"][:10],
        },
    }


def build_markdown_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Generation Quality Report",
        "",
        "## Summary",
        "",
        f"- Status: **{summary['status']}**",
        f"- Total artifacts checked: **{summary['total_artifacts_checked']}**",
        f"- Total questions checked: **{summary['total_questions_checked']}**",
        f"- Average teaching quality score: **{summary['average_teaching_quality_score']}**",
        f"- Average question quality score: **{summary['average_question_quality_score']}**",
        f"- Issue count: **{summary['issue_count']}**",
        "",
        "## Issue Type Counts",
        "",
    ]

    if summary["issue_type_counts"]:
        for issue, count in sorted(summary["issue_type_counts"].items(), key=lambda pair: (-pair[1], pair[0])):
            lines.append(f"- `{issue}`: {count}")
    else:
        lines.append("No quality issues found.")

    lines.extend(["", "## Lowest Quality Teaching Items", ""])
    for item in report["lowest_quality_items"]["teaching"]:
        lines.append(
            f"- **{item['scores']['overall_quality_score']}** | "
            f"{item['domain']} {item['concept_id']} {item['concept_name']} | "
            f"`{item['artifact_type']}` | issues: {', '.join(item['issues']) or 'none'}"
        )
        lines.append(f"  Preview: {item['preview']}")

    lines.extend(["", "## Lowest Quality Questions", ""])
    for item in report["lowest_quality_items"]["questions"]:
        lines.append(
            f"- **{item['scores']['overall_quality_score']}** | "
            f"{item['domain']} {item['concept_id']} {item['concept_name']} | "
            f"`{item['question_type']}` v{item.get('variant_id')} | "
            f"issues: {', '.join(item['issues']) or 'none'}"
        )
        lines.append(f"  Preview: {item['preview']}")

    lines.extend(["", "## Teaching Variation Watchlist", ""])
    for item in report["teaching"]["concept_variation_reports"][:15]:
        lines.append(
            f"- {item['domain']} {item['concept_id']} {item['concept_name']}: "
            f"avg similarity {item['average_pair_similarity']}, "
            f"max similarity {item['max_pair_similarity']}"
        )

    lines.extend(["", "## PASS Rules", ""])
    lines.append("- Average teaching quality score must be >= 0.75")
    lines.append("- Average question quality score must be >= 0.75")
    lines.append("- No `unknown_concept_leak` issues")
    lines.append("- No critical `wrong_domain` issues")

    return "\n".join(lines) + "\n"


def load_json_list(path: Path, label: str) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if not isinstance(data, list):
        raise TypeError(f"{label} must be a JSON list: {path}")

    return data


def main() -> None:
    artifacts = load_json_list(ARTIFACTS_PATH, "Generated tutor artifacts")
    questions = load_json_list(QUESTION_BANK_PATH, "Assessment question bank")
    resources = load_grounding_resources()

    teaching_report = inspect_teaching_artifacts(artifacts, resources)
    question_report = inspect_question_bank(questions, resources)
    report = build_report(teaching_report, question_report)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with JSON_REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)

    with MD_REPORT_PATH.open("w", encoding="utf-8") as handle:
        handle.write(build_markdown_report(report))

    summary = report["summary"]
    print("\nGeneration quality inspection complete.")
    print(f"Total artifacts checked: {summary['total_artifacts_checked']}")
    print(f"Total questions checked: {summary['total_questions_checked']}")
    print(f"Average teaching quality score: {summary['average_teaching_quality_score']}")
    print(f"Average question quality score: {summary['average_question_quality_score']}")
    print(f"Issue count: {summary['issue_count']}")
    print(f"Status: {summary['status']}")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {MD_REPORT_PATH}")


if __name__ == "__main__":
    main()
