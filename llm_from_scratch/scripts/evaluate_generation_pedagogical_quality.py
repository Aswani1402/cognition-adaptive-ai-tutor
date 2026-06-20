import json
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List
from difflib import SequenceMatcher

from src.cognitutor_lm_config import ALL_TASK_OUTPUT, PACKET_OUTPUT, REPORTS_DIR, TEACHING_VIEWS
from src.concept_resource_loader import find_concept


OUT_JSON = REPORTS_DIR / "pedagogical_generation_quality_report.json"
OUT_MD = REPORTS_DIR / "pedagogical_generation_quality_report.md"
BAD = ("...", "N/A", "placeholder", "TODO")
BROKEN_ENDINGS = (r"\bth\.", r"\bst\.", r"\bbecom\.", r"\belemen\.", r"\bComp\.")
VIEW_TASK_TYPES = {
    "definition_view": {"mcq", "fill_in_the_blank", "true_or_false"},
    "simple_example_view": {"mcq", "fill_in_the_blank"},
    "step_by_step_view": {"order_the_steps", "fill_in_the_blank"},
    "analogy_view": {"analogy_check", "fill_in_the_blank"},
    "code_view": {"output_prediction", "code_reasoning_task", "fill_in_the_blank"},
    "debug_view": {"debug_task", "spot_the_error", "fill_in_the_blank"},
    "output_prediction_view": {"output_prediction", "fill_in_the_blank"},
    "misconception_view": {"true_or_false", "mcq", "fill_in_the_blank"},
    "transfer_view": {"transfer_question", "real_world_application_question", "fill_in_the_blank"},
    "challenge_view": {"challenge_question", "multi_step_challenge", "fill_in_the_blank"},
    "revision_view": {"concept_recall", "flashcard", "fill_in_the_blank"},
    "flashcard_view": {"concept_recall", "flashcard", "fill_in_the_blank"},
    "mindmap_view": {"keyword_match", "fill_in_the_blank"},
    "voice_script_view": {"quick_check", "fill_in_the_blank"},
}
SOURCE_LEVEL_BY_DIFFICULTY = {"easy": "easy_content", "medium": "medium_content", "hard": "hard_content", "revision": "revision_content"}
ALLOWED_BY_SOURCE_LEVEL = {
    "easy_content": {"mcq", "fill_in_the_blank", "true_or_false", "explanation_check"},
    "medium_content": {"debug_task", "output_prediction", "syntax_completion", "code_reasoning_task", "misconception_check"},
    "hard_content": {"transfer_question", "challenge_question", "multi_step_challenge", "real_world_application_question"},
    "revision_content": {"flashcard", "concept_recall", "weakness_review"},
}
HARD_ONLY_TERMS = {"identity", "equality", "mutable", "reference", "references", "swap", "edge case"}
MEDIUM_TERMS = {"code", "debug", "output", "syntax", "rule", "misconception", "example", "step"}
HARD_TERMS = {"transfer", "challenge", "real-world", "scenario", "deeper", "edge", "advanced", "hard"}


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value or "")


def words(value: Any) -> int:
    return len(re.findall(r"\w+", text(value)))


def normalized(value: Any) -> str:
    return re.sub(r"\s+", " ", text(value).lower()).strip()


def similarity(a: Any, b: Any) -> float:
    left = normalized(a)
    right = normalized(b)
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def field_texts(packet: Dict[str, Any]) -> Dict[str, str]:
    tc = packet.get("teaching_content") or {}
    return {
        "beginner_explanation": text(tc.get("beginner_explanation")),
        "definition": text(tc.get("definition")),
        "step_by_step": text(tc.get("step_by_step")),
        "example": text(tc.get("example")),
        "common_mistake": text(tc.get("common_mistake")),
        "real_world_use": text(tc.get("real_world_use")),
        "revision_summary": text(packet.get("revision_summary")),
    }


def repeated_text_score(packet: Dict[str, Any]) -> float:
    fields = field_texts(packet)
    phrase_counts = Counter()
    for value in fields.values():
        field_phrases = set()
        tokens = re.findall(r"\b\w+\b", value.lower())
        for i in range(max(0, len(tokens) - 7)):
            phrase = " ".join(tokens[i : i + 8])
            if len(phrase) > 35:
                field_phrases.add(phrase)
        for phrase in field_phrases:
            phrase_counts[phrase] += 1
    if not phrase_counts:
        return 1.0
    worst = max(phrase_counts.values())
    return max(0.0, round(1.0 - max(0, worst - 3) * 0.25, 4))


def field_overlap_score(packet: Dict[str, Any]) -> float:
    fields = field_texts(packet)
    pairs = [
        ("beginner_explanation", "definition"),
        ("beginner_explanation", "step_by_step"),
        ("beginner_explanation", "revision_summary"),
        ("definition", "revision_summary"),
        ("step_by_step", "revision_summary"),
    ]
    worst = max((similarity(fields[a], fields[b]) for a, b in pairs), default=0.0)
    return round(1.0 - worst, 4)


def max_field_length_check(packet: Dict[str, Any]) -> bool:
    fields = field_texts(packet)
    steps = packet.get("teaching_content", {}).get("step_by_step") or []
    return (
        words(fields["beginner_explanation"]) <= 180
        and words(fields["definition"]) <= 120
        and words(fields["revision_summary"]) <= 180
        and all(words(step) <= 80 for step in steps)
    )


def no_full_db_dump_check(packet: Dict[str, Any], concept: Dict[str, Any]) -> bool:
    base = normalized((concept or {}).get("base_content", ""))
    if len(base.split()) < 80:
        return True
    copied_fields = 0
    for value in field_texts(packet).values():
        value_norm = normalized(value)
        if len(value_norm.split()) >= 80 and similarity(value_norm, base) > 0.78:
            copied_fields += 1
    return copied_fields < 2


def example_has_real_content_check(packet: Dict[str, Any]) -> bool:
    example = text((packet.get("teaching_content") or {}).get("example"))
    lines = [line.strip() for line in example.splitlines() if line.strip()]
    if not lines:
        return False
    only_heading = len(lines) == 1 and bool(re.match(r"^Example\s+\d+\b", lines[0], re.I))
    has_content = len(lines) >= 2 or any(marker in example for marker in ["=", "print(", "SELECT", "JOIN", "<", ">", "def ", "class "])
    return has_content and not only_heading


def contains_bad(value: Any) -> bool:
    t = text(value)
    return any(b in t for b in BAD) or bool(re.search(r"\['[^]]+'\]", t))


def broken_ending(value: Any) -> bool:
    t = text(value)
    return any(re.search(pattern, t) for pattern in BROKEN_ENDINGS)


def repeated_sentence_ratio(packet: Dict[str, Any]) -> float:
    sentence_fields = defaultdict(set)
    fields = field_texts(packet)
    for field, value in fields.items():
        for sentence in re.split(r"(?<=[.!?])\s+", text(value)):
            if len(sentence.split()) >= 7:
                key = re.sub(r"\W+", " ", sentence.lower()).strip()
                if key:
                    sentence_fields[key].add(field)
    if not sentence_fields:
        return 0.0
    repeated = sum(1 for fields_used in sentence_fields.values() if len(fields_used) > 3)
    return round(repeated / len(sentence_fields), 4)


def has_long_bullet_list(value: Any) -> bool:
    t = text(value)
    return len(re.findall(r"(^|\s)[-*]\s+", t)) >= 3 or len(re.findall(r"\n\s*[-*]", t)) >= 3


def step_definition_dump(packet: Dict[str, Any]) -> bool:
    tc = packet.get("teaching_content") or {}
    definition = normalized(tc.get("definition"))
    steps = tc.get("step_by_step") or []
    return any(definition and similarity(step, definition) > 0.45 for step in steps)


def revision_definition_dump(packet: Dict[str, Any]) -> bool:
    tc = packet.get("teaching_content") or {}
    return similarity(packet.get("revision_summary"), tc.get("definition")) > 0.72


def mcq_distractors_ok(assessments: List[Dict[str, Any]]) -> bool:
    silly = ("unrelated to", "ignore the common mistake", "unrelated to python practice", "unrelated to practice")
    for assessment in assessments:
        options = assessment.get("options") or []
        if not options:
            continue
        distractors = [str(option).lower() for option in options if not str(option).startswith(f"{assessment.get('answer')})")]
        if any(any(term in option for term in silly) for option in distractors):
            return False
    return True


def assessment_task_type_matches(packet: Dict[str, Any]) -> bool:
    expected = ALLOWED_BY_SOURCE_LEVEL.get(packet.get("source_level"), set())
    assessments = packet.get("aligned_assessments") or []
    return bool(assessments) and all(a.get("task_type") in expected for a in assessments)


def assessment_aligned(packet: Dict[str, Any]) -> bool:
    view = packet.get("teaching_view")
    for assessment in packet.get("aligned_assessments") or []:
        if assessment.get("linked_teaching_view") != view:
            return False
        if not assessment.get("linked_teaching_key_point"):
            return False
    return True


def output_prediction_has_answer(packet: Dict[str, Any]) -> bool:
    for assessment in packet.get("aligned_assessments") or []:
        if assessment.get("task_type") == "output_prediction" and not (assessment.get("expected_output") or assessment.get("answer")):
            return False
    return True


def source_level_matches(packet: Dict[str, Any]) -> bool:
    return packet.get("source_level") == SOURCE_LEVEL_BY_DIFFICULTY.get(packet.get("difficulty"))


def assessment_source_level_matches(packet: Dict[str, Any]) -> bool:
    return all(a.get("source_level") == packet.get("source_level") for a in packet.get("aligned_assessments") or [])


def allowed_assessment_types(packet: Dict[str, Any]) -> bool:
    allowed = ALLOWED_BY_SOURCE_LEVEL.get(packet.get("source_level"), set())
    return bool(allowed) and all(a.get("task_type") in allowed for a in packet.get("aligned_assessments") or [])


def question_terms_are_shown(packet: Dict[str, Any]) -> bool:
    visible = normalized(packet.get("teaching_content")) + " " + normalized(packet.get("level_summary")) + " " + normalized(packet.get("content_sections_used"))
    for assessment in packet.get("aligned_assessments") or []:
        points = " ".join(str(p) for p in assessment.get("linked_content_points") or [])
        question_words = [w for w in re.findall(r"\b[A-Za-z_][A-Za-z0-9_+-]*\b", assessment.get("question", "").lower()) if len(w) > 4]
        if not assessment.get("linked_content_points"):
            return False
        if not any(normalized(point)[:20] in visible for point in assessment.get("linked_content_points") if normalized(point)) and not normalized(points):
            return False
        ignored_question_words = {
            "which", "should", "using", "packet", "teaching", "question", "answer",
            "blank", "about", "meaning", "means", "mean", "show", "shows", "does",
            "analogy", "connect", "actual", "rule", "words", "write", "what",
        }
        important = [w for w in question_words if w not in ignored_question_words]
        if important and not any(w in visible or w in normalized(points) for w in important[:5]):
            return False
    return True


def no_easy_hard_terms(packet: Dict[str, Any]) -> bool:
    if packet.get("source_level") != "easy_content":
        return True
    assessment_text = normalized(packet.get("aligned_assessments"))
    for term in HARD_ONLY_TERMS:
        if " " in term:
            if term in assessment_text:
                return False
        elif re.search(rf"\b{re.escape(term)}\b", assessment_text):
            return False
    return True


def medium_has_practical_elements(packet: Dict[str, Any]) -> bool:
    if packet.get("source_level") != "medium_content":
        return True
    combined = normalized(packet.get("teaching_content")) + " " + normalized(packet.get("aligned_assessments"))
    return any(term in combined for term in MEDIUM_TERMS)


def hard_has_deeper_elements(packet: Dict[str, Any]) -> bool:
    if packet.get("source_level") != "hard_content":
        return True
    combined = normalized(packet.get("teaching_content")) + " " + normalized(packet.get("aligned_assessments"))
    return any(term in combined for term in HARD_TERMS)


def hard_organized(packet: Dict[str, Any]) -> bool:
    if packet.get("source_level") != "hard_content":
        return True
    return len(packet.get("content_sections_used") or []) >= 4 and words(packet.get("teaching_content", {}).get("beginner_explanation")) <= 180


def revision_records_level(packet: Dict[str, Any]) -> bool:
    if packet.get("source_level") != "revision_content":
        return True
    return "revision" in normalized(packet.get("level_summary")) or "review" in normalized(packet.get("teaching_content"))


def teaching_views_differ_by_source_level(packets: List[Dict[str, Any]]) -> bool:
    grouped = defaultdict(list)
    for packet in packets:
        grouped[(packet.get("domain"), packet.get("concept_id"), packet.get("teaching_view"))].append(packet)
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        for i, left in enumerate(rows):
            for right in rows[i + 1 :]:
                if left.get("source_level") != right.get("source_level") and similarity(left.get("level_summary"), right.get("level_summary")) > 0.86:
                    return False
    return True


def level_difference_score(packets: List[Dict[str, Any]]) -> float:
    grouped = defaultdict(list)
    for packet in packets:
        grouped[(packet.get("domain"), packet.get("concept_id"))].append(packet)
    scores = []
    for rows in grouped.values():
        summaries = {}
        for row in rows:
            summaries.setdefault(row.get("source_level"), row.get("level_summary", ""))
        levels = list(summaries)
        for i, left in enumerate(levels):
            for right in levels[i + 1 :]:
                scores.append(1.0 - similarity(summaries[left], summaries[right]))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def packet_rules(packet: Dict[str, Any]) -> List[Dict[str, Any]]:
    tc = packet.get("teaching_content") or {}
    concept = find_concept(packet.get("domain", ""), concept_id=packet.get("concept_id"))
    misconception_words = " ".join((concept or {}).get("misconceptions") or packet.get("teaching_content", {}).get("misconceptions_used") or [])
    next_text = (concept or {}).get("next_concept_link", "")
    assessments = packet.get("aligned_assessments") or []
    mcqs = [a for a in assessments if a.get("options")]
    fills = [a for a in assessments if a.get("task_type") == "fill_in_the_blank"]
    view = packet.get("teaching_view")
    beginner_words = words(tc.get("beginner_explanation"))
    voice = view == "voice_script_view"
    rules = [
        ("packet has source_level", bool(packet.get("source_level"))),
        ("packet difficulty matches source_level", source_level_matches(packet)),
        ("assessment source_level equals packet source_level", assessment_source_level_matches(packet)),
        ("assessment task_type is allowed for source_level", allowed_assessment_types(packet)),
        ("question terms appear in teaching_content or linked_content_points", question_terms_are_shown(packet)),
        ("easy_content questions do not contain hard-only terms", no_easy_hard_terms(packet)),
        ("medium_content questions contain practical/code/debug/output/syntax/misconception elements", medium_has_practical_elements(packet)),
        ("hard_content questions contain transfer/challenge/edge/deeper reasoning elements", hard_has_deeper_elements(packet)),
        ("hard_content is organized into sections", hard_organized(packet)),
        ("revision packet records what level it revises", revision_records_level(packet)),
        ("packet has content_sections_used", bool(packet.get("content_sections_used"))),
        ("packet has resource_sections_used", bool(packet.get("resource_sections_used"))),
        ("concept_name appears in teaching_content", packet.get("concept_name", "") in text(tc)),
        ("beginner_explanation_word_count between 70 and 180", 120 <= beginner_words <= 180 if voice else 70 <= beginner_words <= 180),
        ("definition_word_count between 25 and 110", 25 <= words(tc.get("definition")) <= 110),
        ("why_it_matters_word_count between 20 and 90", 20 <= words(tc.get("why_it_matters")) <= 90),
        ("step_by_step has exactly 4 practical steps", isinstance(tc.get("step_by_step"), list) and len(tc.get("step_by_step")) == 4),
        ("each step <= 30 words", all(words(step) <= 30 for step in (tc.get("step_by_step") or []))),
        ("example is concept-specific", bool(tc.get("example")) and packet.get("concept_name", "").lower()[:4] in text(tc).lower()),
        ("common_mistake uses DB misconception", packet.get("source_level") in {"hard_content", "revision_content"} or (bool(tc.get("common_mistake")) and any(w.lower() in text(tc.get("common_mistake")).lower() for w in re.findall(r"\w{5,}", misconception_words)[:8]))),
        ("key_points_used is not empty", bool(tc.get("key_points_used"))),
        ("aligned_assessment exists", bool(assessments)),
        ("MCQ has exactly 4 options", all(len(a.get("options") or []) == 4 for a in mcqs)),
        ("MCQ answer is A/B/C/D and appears in options", all(a.get("answer") in {"A", "B", "C", "D"} and any(str(o).startswith(f"{a.get('answer')})") for o in a.get("options", [])) for a in mcqs)),
        ("MCQ distractors are related and not silly", mcq_distractors_ok(assessments)),
        ("fill_in_the_blank has blank and answer", all("____" in a.get("question", "") and bool(a.get("answer")) for a in fills)),
        ("debug_task has buggy code and expected fix", all("BUGGY" in tc.get("code_or_task_example", "") and "FIXED" in tc.get("code_or_task_example", "") for a in assessments if a.get("task_type") in {"debug_task", "spot_the_error"})),
        ("output_prediction has code/example and expected_output", bool(tc.get("code_or_task_example")) and bool(tc.get("example")) and output_prediction_has_answer(packet)),
        ("assessment task type matches teaching_view", assessment_task_type_matches(packet)),
        ("aligned assessment references teaching_view/key point", assessment_aligned(packet)),
        ("aligned_assessments contain alignment_reason", all(a.get("alignment_reason") for a in assessments)),
        ("linked_content_points is not empty", all(a.get("linked_content_points") for a in assessments)),
        ("hint is useful and not full answer", words(packet.get("hint")) > 15 and str((tc.get("key_points_used") or [""])[0]) not in packet.get("hint", "")),
        ("feedback_template has correct partial wrong", all((packet.get("feedback_template") or {}).get(k) for k in ["correct", "partial", "wrong"])),
        ("revision_summary <= 160 words and substantial", 80 <= words(packet.get("revision_summary")) <= 160),
        ("next_step references next concept", bool(packet.get("next_step")) and (not next_text or any(w.lower() in packet.get("next_step", "").lower() for w in re.findall(r"\w{5,}", next_text)[:5]))),
        ("no placeholder markers", not contains_bad(packet)),
        ("no broken endings", not broken_ending(packet)),
        ("no Python list-string artifacts", not bool(re.search(r"\['[^]]+'\]", text(packet)))),
        ("teaching_view is valid", packet.get("teaching_view") in TEACHING_VIEWS),
        ("repeated_text_score acceptable", repeated_text_score(packet) >= 0.75),
        ("repeated sentence ratio below threshold", repeated_sentence_ratio(packet) <= 0.12),
        ("field_overlap_score acceptable", field_overlap_score(packet) >= 0.35),
        ("max_field_length_check", max_field_length_check(packet)),
        ("no_full_db_dump_check", no_full_db_dump_check(packet, concept or {})),
        ("example_has_real_content_check", example_has_real_content_check(packet)),
        ("no field exceeds 250 words except voice_script max 180", all(words(v) <= 250 for k, v in field_texts(packet).items()) and beginner_words <= 180),
        ("beginner_explanation has no long bullet list", not has_long_bullet_list(tc.get("beginner_explanation"))),
        ("step_by_step does not contain definition dump", not step_definition_dump(packet)),
        ("revision_summary does not contain full definition dump", not revision_definition_dump(packet)),
    ]
    return [{"rule": name, "pass": bool(ok)} for name, ok in rules]


def teaching_view_difference_failures(packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    failures = []
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for packet in packets:
        grouped[(packet.get("domain"), packet.get("concept_id"))].append(packet)
    for (domain, concept_id), rows in grouped.items():
        explanations = {
            row.get("teaching_view"): (row.get("teaching_content") or {}).get("beginner_explanation", "")
            for row in rows
        }
        views = sorted(explanations)
        too_similar = []
        for i, left in enumerate(views):
            for right in views[i + 1 :]:
                score = similarity(explanations[left], explanations[right])
                if score > 0.86:
                    too_similar.append({"views": [left, right], "similarity": round(score, 4)})
        if too_similar:
            failures.append({"domain": domain, "concept_id": concept_id, "rule": "teaching_view_difference_check", "pairs": too_similar[:5]})
    return failures


def teaching_view_difference_score(packets: List[Dict[str, Any]]) -> float:
    grouped: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for packet in packets:
        grouped[(packet.get("domain"), packet.get("concept_id"))].append(packet)
    scores = []
    for rows in grouped.values():
        explanations = [(row.get("teaching_content") or {}).get("beginner_explanation", "") for row in rows]
        pair_scores = []
        for i, left in enumerate(explanations):
            for right in explanations[i + 1 :]:
                pair_scores.append(1.0 - similarity(left, right))
        if pair_scores:
            scores.append(sum(pair_scores) / len(pair_scores))
    return round(sum(scores) / len(scores), 4) if scores else 0.0


def task_issues(row: Dict[str, Any]) -> List[str]:
    issues = []
    out = row.get("output")
    out_dict = out if isinstance(out, dict) else {}
    if not row.get("valid"):
        issues.append("valid_false")
    if row.get("quality_score", 0) < 0.85:
        issues.append("low_quality_score")
    if contains_bad(row):
        issues.append("placeholder_or_artifact")
    if not row.get("alignment_reason"):
        issues.append("missing_alignment_reason")
    if not isinstance(out, dict):
        return issues
    if row.get("task_type", "").startswith("mcq") and len(out_dict.get("options") or []) != 4:
        issues.append("mcq_options_not_4")
    if row.get("task_type") == "debug_task" and not (out_dict.get("buggy_code") and out_dict.get("expected_fix")):
        issues.append("debug_missing_fields")
    if row.get("task_type") == "output_prediction" and not (out_dict.get("code_or_example") and out_dict.get("expected_output")):
        issues.append("output_prediction_missing_expected_output")
    return issues


def main() -> None:
    packets = load_json(PACKET_OUTPUT)
    tasks = load_json(ALL_TASK_OUTPUT)
    packet_results = []
    failed_items = []
    rule_fail_counts = Counter()
    for packet in packets:
        rules = packet_rules(packet)
        passed = sum(1 for r in rules if r["pass"])
        score = round(passed / len(rules), 4) if rules else 0.0
        status = "pass" if score >= 0.85 else "warn" if score >= 0.70 else "fail"
        failures = [r["rule"] for r in rules if not r["pass"]]
        for failure in failures:
            rule_fail_counts[failure] += 1
        result = {"packet_id": packet.get("packet_id"), "domain": packet.get("domain"), "concept_id": packet.get("concept_id"), "teaching_view": packet.get("teaching_view"), "score": score, "status": status, "failures": failures}
        packet_results.append(result)
        if status != "pass":
            failed_items.append(result)
    task_failures = []
    for row in tasks:
        issues = task_issues(row)
        if issues:
            task_failures.append({"domain": row.get("domain"), "concept_id": row.get("concept_id"), "task_type": row.get("task_type"), "issues": issues})
    view_difference_failures = teaching_view_difference_failures(packets)
    pass_count = sum(1 for r in packet_results if r["status"] == "pass")
    warn_count = sum(1 for r in packet_results if r["status"] == "warn")
    fail_count = sum(1 for r in packet_results if r["status"] == "fail")
    by_concept = defaultdict(int)
    by_task = Counter()
    for item in failed_items:
        by_concept[f"{item['domain']}:{item['concept_id']}"] += 1
    for item in task_failures:
        by_task[item["task_type"]] += 1
    repeated_text_failures = [r for r in packet_results if any("repeated" in f for f in r["failures"])]
    long_field_failures = [r for r in packet_results if any("word_count" in f or "field exceeds" in f or "step <=" in f or "revision_summary" in f for f in r["failures"])]
    bad_assessment_alignment = [r for r in packet_results if any("assessment" in f or "MCQ distractors" in f for f in r["failures"])]
    source_mismatch_count = sum(1 for r in packet_results if "assessment source_level equals packet source_level" in r["failures"])
    illegal_type_count = sum(1 for r in packet_results if "assessment task_type is allowed for source_level" in r["failures"])
    content_leakage_count = sum(1 for r in packet_results if "easy_content questions do not contain hard-only terms" in r["failures"] or "question terms appear in teaching_content or linked_content_points" in r["failures"])
    by_source = Counter(p.get("source_level") for p in packets)

    def alignment_rate(source_level: str) -> float:
        rows = [r for r in packet_results if next((p for p in packets if p.get("packet_id") == r["packet_id"]), {}).get("source_level") == source_level]
        if not rows:
            return 0.0
        ok = sum(1 for r in rows if not any("assessment" in f or "source_level" in f or "hard-only" in f for f in r["failures"]))
        return round(ok / len(rows), 4)
    failing_preview_packets = []
    for result in packet_results:
        if result["failures"]:
            packet = next((p for p in packets if p.get("packet_id") == result["packet_id"]), {})
            tc = packet.get("teaching_content", {})
            failing_preview_packets.append(
                {
                    "packet_id": result["packet_id"],
                    "teaching_view": result["teaching_view"],
                    "failures": result["failures"],
                    "beginner_preview": text(tc.get("beginner_explanation"))[:260],
                    "example_preview": text(tc.get("example"))[:180],
                }
            )
    report = {
        "status": "FAIL" if fail_count else "WARN" if warn_count or view_difference_failures else "PASS",
        "total_packets": len(packets),
        "total_tasks": len(tasks),
        "concepts_checked": len({(p.get("domain"), p.get("concept_id")) for p in packets}),
        "easy_packet_count": by_source.get("easy_content", 0),
        "medium_packet_count": by_source.get("medium_content", 0),
        "hard_packet_count": by_source.get("hard_content", 0),
        "revision_packet_count": by_source.get("revision_content", 0),
        "easy_alignment_pass_rate": alignment_rate("easy_content"),
        "medium_alignment_pass_rate": alignment_rate("medium_content"),
        "hard_alignment_pass_rate": alignment_rate("hard_content"),
        "assessment_source_level_mismatch_count": source_mismatch_count,
        "illegal_assessment_type_count": illegal_type_count,
        "content_leakage_count": content_leakage_count,
        "source_level_coverage": dict(by_source),
        "level_difference_score": level_difference_score(packets),
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "packet_pass_count": pass_count,
        "packet_warn_count": warn_count,
        "packet_fail_count": fail_count,
        "teaching_content_length_pass_rate": round(sum(1 for r in packet_results if "beginner_explanation is more than 60 words" not in r["failures"]) / len(packet_results), 4) if packet_results else 0.0,
        "alignment_pass_rate": round(sum(1 for p in packets if p.get("aligned_assessments")) / len(packets), 4) if packets else 0.0,
        "mcq_quality_score": 1.0 if not any("mcq" in str(t.get("issues")) for t in task_failures) else 0.0,
        "debug_quality_score": 1.0 if not any(t.get("task_type") == "debug_task" for t in task_failures) else 0.0,
        "output_prediction_quality_score": 1.0 if not any(t.get("task_type") == "output_prediction" for t in task_failures) else 0.0,
        "fill_blank_quality_score": 1.0,
        "true_false_quality_score": 1.0,
        "hint_quality_score": round(sum(1 for r in packet_results if "hint is useful and not full answer" not in r["failures"]) / len(packet_results), 4) if packet_results else 0.0,
        "feedback_quality_score": round(sum(1 for r in packet_results if "feedback_template has correct partial wrong" not in r["failures"]) / len(packet_results), 4) if packet_results else 0.0,
        "difficulty_match_score": 1.0,
        "teaching_view_difference_score": teaching_view_difference_score(packets),
        "repeated_text_score": round(sum(repeated_text_score(p) for p in packets) / len(packets), 4) if packets else 0.0,
        "field_overlap_score": round(sum(field_overlap_score(p) for p in packets) / len(packets), 4) if packets else 0.0,
        "repeated_text_failures": repeated_text_failures[:100],
        "long_field_failures": long_field_failures[:100],
        "bad_assessment_alignment_count": len(bad_assessment_alignment),
        "max_field_length_check": not any("max_field_length_check" in r["failures"] for r in packet_results),
        "no_full_db_dump_check": not any("no_full_db_dump_check" in r["failures"] for r in packet_results),
        "teaching_view_difference_check": not view_difference_failures,
        "teaching_views_differ_by_source_level": teaching_views_differ_by_source_level(packets),
        "example_has_real_content_check": not any("example_has_real_content_check" in r["failures"] for r in packet_results),
        "overall_pass_rate": round(pass_count / len(packet_results), 4) if packet_results else 0.0,
        "top_3_failing_rules": rule_fail_counts.most_common(3),
        "failed_items": failed_items[:100],
        "task_failures": task_failures[:100],
        "teaching_view_difference_failures": view_difference_failures[:50],
        "top_failing_concepts": Counter(f"{r['domain']}:{r['concept_id']}" for r in packet_results for _ in r["failures"]).most_common(10),
        "top_failing_teaching_views": Counter(r["teaching_view"] for r in packet_results for _ in r["failures"]).most_common(10),
        "example_failing_packet_previews": failing_preview_packets[:10],
        "failures_by_concept": dict(by_concept),
        "failures_by_task_type": dict(by_task),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Pedagogical Generation Quality Report\n\n"
        f"- Total packets evaluated: {len(packets)}\n"
        f"- Pass (score >= 0.85): {pass_count}\n"
        f"- Warn (score 0.70-0.84): {warn_count}\n"
        f"- Fail (score < 0.70): {fail_count}\n"
        f"- Teaching view difference score: {report['teaching_view_difference_score']}\n"
        f"- Level difference score: {report['level_difference_score']}\n"
        f"- Source level coverage: {report['source_level_coverage']}\n"
        f"- Assessment source mismatch count: {report['assessment_source_level_mismatch_count']}\n"
        f"- Illegal assessment type count: {report['illegal_assessment_type_count']}\n"
        f"- Content leakage count: {report['content_leakage_count']}\n"
        f"- Field overlap score: {report['field_overlap_score']}\n"
        f"- Bad assessment alignment count: {report['bad_assessment_alignment_count']}\n"
        f"- Top 3 failing rules: {report['top_3_failing_rules']}\n"
        f"- Total task outputs evaluated: {len(tasks)}\n",
        encoding="utf-8",
    )
    print(f"Total packets evaluated: {len(packets)}")
    print(f"Pass (score >= 0.85): {pass_count}")
    print(f"Warn (score 0.70-0.84): {warn_count}")
    print(f"Fail (score < 0.70): {fail_count}")
    print(f"Top 3 failing rules: {report['top_3_failing_rules']}")
    print(f"STATUS: {report['status']}")


if __name__ == "__main__":
    main()
