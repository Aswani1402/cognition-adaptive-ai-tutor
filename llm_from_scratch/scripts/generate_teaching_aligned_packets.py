import json
import re
from collections import defaultdict
from typing import Any, Dict, List

from src.cognitutor_lm_config import PACKET_OUTPUT, PACKETS_DIR, TEACHING_VIEWS
from src.content_versioning import attach_version_metadata
from src.concept_resource_loader import clean_text as loader_clean_text
from src.concept_resource_loader import load_concept_resources, print_concept_summary, safe_name
from src.production_quality_gate import apply_quality_gate


CODE_MARKERS = (
    " = ",
    "print(",
    "def ",
    "class ",
    "SELECT ",
    " FROM ",
    " JOIN ",
    "CREATE ",
    "INSERT ",
    "<",
    ">",
    "{",
    "}",
    "return ",
)

BROKEN_ENDINGS = (r"\bth\.$", r"\bst\.$", r"\bbecom\.$", r"\belemen\.$", r"\bComp\.$")


def clean_text(value: Any) -> str:
    text = loader_clean_text(value)
    text = text.replace("['", "").replace("']", "").replace('["', "").replace('"]', "")
    for pattern in BROKEN_ENDINGS:
        text = re.sub(pattern, "", text).strip(" ,.;:")
    return text


def split_sentences(text: str) -> List[str]:
    cleaned = clean_text(text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]


def split_bullets(text: Any) -> List[str]:
    if isinstance(text, list):
        items = text
    else:
        raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        items = re.split(r"\n+|\s+-\s+|\s+\*\s+|\s+\|\s+", raw)
    cleaned = []
    for item in items:
        value = clean_text(item).strip(" -*")
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


def resources_used() -> Dict[str, bool]:
    return {
        "base_content": True,
        "examples": True,
        "key_points": True,
        "misconceptions": True,
        "real_world_use": True,
        "next_concept_link": True,
    }


def source_level_for_difficulty(difficulty: str) -> str:
    return {
        "easy": "easy_content",
        "medium": "medium_content",
        "hard": "hard_content",
        "revision": "revision_content",
    }[difficulty]


def get_allowed_assessment_types(source_level: str) -> List[str]:
    return {
        "easy_content": ["mcq", "fill_in_the_blank", "true_or_false", "explanation_check"],
        "medium_content": ["debug_task", "output_prediction", "syntax_completion", "code_reasoning_task", "misconception_check"],
        "hard_content": ["transfer_question", "challenge_question", "multi_step_challenge", "real_world_application_question"],
        "revision_content": ["flashcard", "concept_recall", "weakness_review"],
    }[source_level]


def build_easy_content(concept: Dict[str, Any]) -> Dict[str, Any]:
    if concept.get("domain") == "Python" and str(concept.get("concept_name", "")).lower() == "variables":
        return {
            "source_level": "easy_content",
            "learning_goal": "Understand that a variable is a name used to store and reuse a value.",
            "definition": "A variable is a name you give to a value so you can use that value later in a program. For example, score = 10 gives the name score to the value 10.",
            "key_points": ["A variable is a name for a value."],
            "example": "score = 10\nprint(score)",
            "common_mistake": "A beginner mistake is starting a variable name with a number, such as 2score. Use a valid name like score2 instead.",
            "real_world_use": "Variables help programs remember simple information such as a score, age, name, or total while the program runs.",
            "next_concept_link": clean_text(concept.get("next_concept_link")),
            "allowed_assessment_types": get_allowed_assessment_types("easy_content"),
        }
    keys = extract_key_points(concept.get("key_points") or [concept["concept_name"]])
    examples = example_blocks(concept)
    mistake = misconception_pair(concept, keys)
    return {
        "source_level": "easy_content",
        "learning_goal": f"Understand the beginner meaning of {concept['concept_name']} and use one simple example.",
        "definition": extract_short_definition(concept.get("base_content", ""), concept["concept_name"], concept["domain"], keys),
        "key_points": keys[:1],
        "example": formatted_block(examples[0]),
        "common_mistake": common_mistake_from_pair(mistake),
        "real_world_use": real_world_use(concept, keys[0]),
        "next_concept_link": clean_text(concept.get("next_concept_link")),
        "allowed_assessment_types": get_allowed_assessment_types("easy_content"),
    }


def build_medium_content(concept: Dict[str, Any]) -> Dict[str, Any]:
    if concept.get("domain") == "Python" and str(concept.get("concept_name", "")).lower() == "variables":
        return {
            "source_level": "medium_content",
            "learning_goal": "Use Python variables with practical naming rules, case sensitivity, assignment, and type checking.",
            "definition": "Python variables are names assigned with =. They are case-sensitive, must follow naming rules, and can be rebound to values of different types during a program.",
            "key_points": ["age and Age are different names.", "Names cannot start with a digit.", "Python can infer the type from the assigned value."],
            "examples": ["age = 15\nAge = 20\nprint(age)", "score = 10\nscore = 'ten'\nprint(type(score))"],
            "syntax_or_rules": ["Use name = value for assignment.", "Start names with a letter or underscore.", "Use type(value) to inspect a value's current type."],
            "common_mistakes": ["Writing 2score = 10 is invalid because names cannot start with a digit.", "Assuming age and Age are the same name causes wrong output."],
            "debug_or_output_example": "age = 15\nAge = 20\nprint(age)",
            "real_world_use": "Readable variable names make scripts easier to debug when values change during calculations or input handling.",
            "next_concept_link": clean_text(concept.get("next_concept_link")),
            "allowed_assessment_types": get_allowed_assessment_types("medium_content"),
        }
    keys = extract_key_points(concept.get("key_points") or [concept["concept_name"]])
    examples = example_blocks(concept)
    mistakes = extract_misconceptions(concept.get("misconceptions")) or [f"Misapply the rule for {concept['concept_name']}."]
    syntax = keys[1:4] or keys[:2]
    return {
        "source_level": "medium_content",
        "learning_goal": f"Use {concept['concept_name']} in practical syntax, debugging, and prediction tasks.",
        "definition": extract_short_definition(concept.get("base_content", ""), concept["concept_name"], concept["domain"], keys),
        "key_points": keys[:3],
        "examples": [formatted_block(example) for example in examples[:2]],
        "syntax_or_rules": syntax,
        "common_mistakes": mistakes[:2],
        "debug_or_output_example": examples[0]["code"] or formatted_block(examples[0]),
        "real_world_use": real_world_use(concept, keys[0]),
        "next_concept_link": clean_text(concept.get("next_concept_link")),
        "allowed_assessment_types": get_allowed_assessment_types("medium_content"),
    }


def build_hard_content(concept: Dict[str, Any]) -> Dict[str, Any]:
    if concept.get("domain") == "Python" and str(concept.get("concept_name", "")).lower() == "variables":
        return {
            "source_level": "hard_content",
            "learning_goal": "Reason about Python variables as references to objects and transfer that idea to mutability, identity, equality, and readable program design.",
            "definition": "At a deeper level, a Python variable is a name bound to an object. That distinction matters when comparing identity, equality, and mutable object behavior.",
            "advanced_points": ["Variables bind names to objects, not boxes that directly contain values.", "Identity checks whether two names refer to the same object.", "Equality checks whether two objects have equal values."],
            "edge_cases": ["Mutable objects can change through one name and be observed through another.", "The swap idiom a, b = b, a rebinds names in one clear step.", "Aliasing can make code harder to reason about if names are vague."],
            "transfer_examples": ["items = []\nother = items\nother.append('x')\nprint(items)", "a = 10\nb = 10\nprint(a == b)"],
            "real_world_use": "In larger programs, clear variable names and careful handling of mutable objects prevent confusing shared-state bugs.",
            "challenge_tasks": ["Explain when identity and equality can give different answers.", "Refactor unclear variable names in a small function without changing behavior."],
            "next_concept_link": clean_text(concept.get("next_concept_link")),
            "allowed_assessment_types": get_allowed_assessment_types("hard_content"),
        }
    keys = extract_key_points(concept.get("key_points") or [concept["concept_name"]])
    all_keys = split_bullets(concept.get("key_points")) or keys
    examples = example_blocks(concept)
    real = real_world_use(concept, keys[0])
    advanced = compact_list(all_keys[3:] or all_keys[-3:] or keys, max_items=4, max_words=20)
    return {
        "source_level": "hard_content",
        "learning_goal": f"Transfer {concept['concept_name']} to deeper reasoning, edge cases, and real-world use.",
        "definition": extract_short_definition(concept.get("base_content", ""), concept["concept_name"], concept["domain"], keys),
        "advanced_points": advanced,
        "edge_cases": compact_list(all_keys[6:] or advanced, max_items=3, max_words=20),
        "transfer_examples": [formatted_block(example) for example in examples[1:3]] or [formatted_block(examples[0])],
        "real_world_use": real,
        "challenge_tasks": [
            f"Apply {concept['concept_name']} in a new situation using this rule: {keys[0]}",
            f"Explain which misconception would lead to the wrong solution.",
        ],
        "next_concept_link": clean_text(concept.get("next_concept_link")),
        "allowed_assessment_types": get_allowed_assessment_types("hard_content"),
    }


def build_revision_content(concept: Dict[str, Any]) -> Dict[str, Any]:
    easy = build_easy_content(concept)
    medium = build_medium_content(concept)
    hard = build_hard_content(concept)
    summary = truncate_to_sentence(
        f"{concept['concept_name']} review: {easy['definition']} Practice the simple example, the practical rule, and the transfer use.",
        120,
    )
    return {
        "source_level": "revision_content",
        "summary": summary,
        "definition": easy["definition"],
        "key_points": (easy["key_points"] + medium["key_points"] + hard["advanced_points"])[:4],
        "example": easy["example"],
        "common_mistake": easy["common_mistake"],
        "real_world_use": hard["real_world_use"],
        "flashcards": [
            f"Definition: {easy['definition']}",
            f"Key point: {easy['key_points'][0]}",
            f"Example: {easy['example']}",
            f"Mistake: {easy['common_mistake']}",
            f"Real use: {hard['real_world_use']}",
        ],
        "weakness_review": f"Review the example and the common mistake before moving to the next view for {concept['concept_name']}.",
        "next_concept_link": clean_text(concept.get("next_concept_link")),
        "allowed_assessment_types": get_allowed_assessment_types("revision_content"),
    }


def build_difficulty_content_blocks(concept: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "domain": concept["domain"],
        "easy_content": build_easy_content(concept),
        "medium_content": build_medium_content(concept),
        "hard_content": build_hard_content(concept),
        "revision_content": build_revision_content(concept),
    }


def select_content_for_packet(concept: Dict[str, Any], difficulty: str, teaching_view: str) -> Dict[str, Any]:
    blocks = build_difficulty_content_blocks(concept)
    return blocks[source_level_for_difficulty(difficulty)]


def difficulty_for(view: str) -> str:
    if view in {"definition_view", "simple_example_view", "analogy_view", "voice_script_view"}:
        return "easy"
    if view in {"step_by_step_view", "code_view", "debug_view", "output_prediction_view", "misconception_view"}:
        return "medium"
    if view in {"transfer_view", "challenge_view"}:
        return "hard"
    return "revision"


def label(view: str) -> str:
    return view.replace("_", " ").title()


def sentence_split(text: str) -> List[str]:
    return split_sentences(text)


def cap_words(text: str, max_words: int) -> str:
    words = clean_text(text).split()
    if len(words) <= max_words:
        return " ".join(words)
    clipped = " ".join(words[:max_words]).strip(" ,;:")
    return clipped if clipped.endswith((".", "!", "?")) else f"{clipped}."


def truncate_to_sentence(text: str, max_words: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned.split()) <= max_words:
        return cleaned
    result = []
    count = 0
    for sentence in split_sentences(cleaned):
        sentence_words = sentence.split()
        if result and count + len(sentence_words) > max_words:
            break
        if not result and len(sentence_words) > max_words:
            return cap_words(sentence, max_words)
        result.append(ensure_sentence(sentence))
        count += len(sentence_words)
    return " ".join(result) if result else cap_words(cleaned, max_words)


def ensure_sentence(text: str) -> str:
    result = clean_text(text)
    return result if result.endswith((".", "!", "?")) else f"{result}."


def ensure_min_words(text: str, min_words: int, extender: str) -> str:
    result = clean_text(text)
    while len(result.split()) < min_words:
        result = f"{ensure_sentence(result)} {clean_text(extender)}"
    return result


def make_short_paragraph(sentences: List[str], min_words: int, max_words: int) -> str:
    result = ""
    for sentence in sentences:
        candidate = f"{result} {ensure_sentence(sentence)}".strip()
        if result and len(candidate.split()) > max_words:
            break
        result = candidate
    if len(result.split()) < min_words and sentences:
        for sentence in sentences:
            candidate = f"{result} {ensure_sentence(sentence)}".strip()
            if len(candidate.split()) <= max_words:
                result = candidate
            if len(result.split()) >= min_words:
                break
    return truncate_to_sentence(result, max_words)


def remove_repeated_phrases(text: str) -> str:
    seen = set()
    kept = []
    for sentence in split_sentences(text):
        key = re.sub(r"\W+", " ", sentence.lower()).strip()
        if key and key not in seen:
            kept.append(ensure_sentence(sentence))
            seen.add(key)
    return " ".join(kept)


def compact_list(items: List[str], max_items: int = 4, max_words: int = 18) -> List[str]:
    cleaned: List[str] = []
    for item in items:
        value = cap_words(item, max_words)
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned[:max_items]


def extract_key_points(key_points: Any) -> List[str]:
    return compact_list(split_bullets(key_points), max_items=4, max_words=18)


def extract_examples(examples: Any) -> List[Dict[str, str]]:
    return example_blocks({"concept_name": "Example", "examples": split_bullets(examples), "key_points": ["Use the concept rule."]})


def extract_misconceptions(misconceptions: Any) -> List[str]:
    return compact_list(split_bullets(misconceptions), max_items=3, max_words=24)


def extract_real_world_use(real_world_use: Any) -> List[str]:
    return compact_list(split_bullets(real_world_use), max_items=3, max_words=22)


def extract_short_definition(base_content: str, concept_name: str, domain: str = "", keys: List[str] | None = None) -> str:
    keys = keys or [concept_name]
    base_sentences = split_sentences(base_content)
    first_key = ensure_sentence(keys[0] if keys else f"{concept_name} is an important concept")
    if domain == "Python" and concept_name.lower() == "variables":
        definition = (
            "A variable is a name bound to an object in memory. Python decides the variable's type from the value assigned to it, "
            "so you do not need to declare the type manually."
        )
    elif len(base_sentences) >= 2:
        definition = f"{base_sentences[0]} {base_sentences[1]}"
    elif base_sentences:
        definition = f"{base_sentences[0]} {first_key}"
    else:
        definition = first_key
    if len(definition.split()) < 35:
        definition = f"{ensure_sentence(definition)} It explains the core rule learners should use before studying examples, mistakes, or real applications."
    return truncate_to_sentence(definition, 90)


def short_definition(concept: Dict[str, Any], keys: List[str]) -> str:
    name = concept["concept_name"]
    return extract_short_definition(concept.get("base_content", ""), name, concept.get("domain", ""), keys)


def misconception_pair(concept: Dict[str, Any], keys: List[str]) -> Dict[str, str]:
    raw = (concept.get("misconceptions") or [f"Learners may treat {concept['concept_name']} as a memorized fact instead of applying its rule."])[0]
    parts = re.split(r"\s+[—-]\s+|\s+but actually\s+|\s+but\s+", clean_text(raw), maxsplit=1)
    misconception = parts[0].strip(" \"")
    correction = parts[1].strip() if len(parts) > 1 else keys[0]
    return {
        "misconception": ensure_sentence(cap_words(misconception, 24)),
        "correction": ensure_sentence(cap_words(correction, 32)),
    }


def is_code_like(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    upper = text.upper()
    return any(marker in text or marker in upper for marker in CODE_MARKERS) or bool(re.match(r"^[A-Za-z_][\w.]*\([^)]*\)", text))


def normalize_code_example(text: str) -> str:
    lines = [clean_text(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines[:10])


def example_blocks(concept: Dict[str, Any]) -> List[Dict[str, str]]:
    if concept.get("domain") == "Python" and str(concept.get("concept_name", "")).lower() == "variables":
        return [{"title": "Example - assignment and printing", "body": "score = 10\nprint(score)", "code": "score = 10\nprint(score)"}]
    examples = [clean_text(e) for e in concept.get("examples") or [] if clean_text(e)]
    blocks: List[Dict[str, List[str]]] = []
    current: Dict[str, List[str]] = {"title": [f"{concept['concept_name']} example"], "lines": []}
    for item in examples:
        if re.match(r"^Example\s+\d+", item, re.I):
            if current["lines"]:
                blocks.append(current)
            current = {"title": [item], "lines": []}
        else:
            current["lines"].append(item)
    if current["lines"]:
        blocks.append(current)
    if not blocks and examples:
        blocks.append({"title": [f"{concept['concept_name']} example"], "lines": examples[:5]})
    if not blocks:
        key = (concept.get("key_points") or [concept["concept_name"]])[0]
        blocks.append({"title": [f"{concept['concept_name']} example"], "lines": [f"Apply the rule: {key}"]})

    result = []
    for block in blocks:
        lines = block["lines"][:8]
        code_lines = [line for line in lines if is_code_like(line)]
        result.append(
            {
                "title": block["title"][0],
                "body": "\n".join(lines),
                "code": normalize_code_example("\n".join(code_lines[:8] if code_lines else lines[:4])),
            }
        )
    return result


def formatted_block(example: Dict[str, str]) -> str:
    if example.get("body"):
        return f"{example['title']}\n{example['body']}"
    return example.get("title", "")


def common_mistake_from_pair(mistake: Dict[str, str]) -> str:
    return truncate_to_sentence(f"Many learners think {mistake['misconception']} Actually, {mistake['correction']}", 70)


def real_world_use(concept: Dict[str, Any], key: str) -> str:
    real = clean_text(concept.get("real_world_use"))
    if not real:
        real = f"{concept['concept_name']} is used when a {concept['domain']} task needs this rule: {key}"
    pieces = [p.strip(" -") for p in re.split(r"\s+-\s+|;\s+|\.\s+", real) if p.strip(" -")]
    if pieces:
        real = " ".join(ensure_sentence(p) for p in pieces[:3])
    if len(real.split()) < 25:
        real = f"{ensure_sentence(real)} This makes the concept useful when solving practical {concept['domain']} tasks with clear, reviewable decisions."
    return truncate_to_sentence(real, 70)


def line_by_line(example_code: str) -> List[str]:
    lines = [line for line in example_code.splitlines() if line.strip()]
    explanations = []
    for index, line in enumerate(lines[:5], start=1):
        explanations.append(f"Line {index}: `{line}` applies one part of the concept rule.")
    return explanations or ["Line 1: Read the example and connect it to the rule."]


def section_parts(concept: Dict[str, Any]) -> Dict[str, Any]:
    fallback_key = concept.get("concept_name") or "the concept"
    keys = extract_key_points(concept.get("key_points") or [fallback_key])
    definition = short_definition(concept, keys)
    examples = example_blocks(concept)
    mistake = misconception_pair(concept, keys)
    real = real_world_use(concept, keys[0])
    return {
        "definition": definition,
        "beginner_core": beginner_core(concept, definition, keys, examples[0], mistake, real),
        "keys": keys,
        "example": examples[0],
        "examples": examples,
        "mistake": mistake,
        "real": real,
        "next": clean_text(concept.get("next_concept_link")) or f"Practice one more {concept['domain']} concept after this.",
    }


def parts_from_level(concept: Dict[str, Any], level_content: Dict[str, Any]) -> Dict[str, Any]:
    source = level_content["source_level"]
    if source == "easy_content":
        keys = level_content["key_points"]
        example = {"title": "Easy example", "body": level_content["example"], "code": normalize_code_example(level_content["example"])}
        mistake = {"misconception": level_content["common_mistake"].replace("Many learners think ", "").split(" Actually,")[0], "correction": level_content["common_mistake"].split("Actually,")[-1].strip()}
    elif source == "medium_content":
        keys = level_content["key_points"]
        example_text = (level_content.get("examples") or [level_content.get("debug_or_output_example", "")])[0]
        example = {"title": "Medium example", "body": example_text, "code": normalize_code_example(level_content.get("debug_or_output_example") or example_text)}
        mistakes = level_content.get("common_mistakes") or [f"Misapply the rule for {concept['concept_name']}."]
        mistake = {"misconception": ensure_sentence(mistakes[0]), "correction": ensure_sentence(keys[0])}
    elif source == "hard_content":
        keys = level_content.get("advanced_points") or [level_content["learning_goal"]]
        example_text = (level_content.get("transfer_examples") or level_content.get("challenge_tasks") or [level_content["real_world_use"]])[0]
        example = {"title": "Hard transfer example", "body": example_text, "code": normalize_code_example(example_text)}
        mistake = {"misconception": "The first simple example is enough for every situation.", "correction": ensure_sentence(keys[0])}
    else:
        keys = level_content.get("key_points") or [level_content.get("summary", concept["concept_name"])]
        example = {"title": "Revision example", "body": level_content.get("example", ""), "code": normalize_code_example(level_content.get("example", ""))}
        mistake = {"misconception": level_content.get("weakness_review", "Forgetting the example makes review weak."), "correction": ensure_sentence(keys[0])}
    return {
        "definition": level_content.get("definition") or level_content.get("summary", ""),
        "beginner_core": "",
        "keys": compact_list(keys, max_items=4, max_words=22),
        "example": example,
        "examples": [example],
        "mistake": mistake,
        "real": level_content.get("real_world_use") or level_content.get("summary", ""),
        "next": level_content.get("next_concept_link") or f"Practice one more {concept['domain']} concept after this.",
        "learning_goal": level_content.get("learning_goal") or level_content.get("summary", ""),
        "source_level": source,
        "allowed_assessment_types": level_content.get("allowed_assessment_types", []),
        "level_content": level_content,
    }


def beginner_core(
    concept: Dict[str, Any],
    definition: str,
    keys: List[str],
    example: Dict[str, str],
    mistake: Dict[str, str],
    real: str,
) -> str:
    name = concept["concept_name"]
    body = (
        f"{definition} For a beginner, the important move is to connect the name {name} with one clear rule: {keys[0]} "
        f"Use the example `{example['code'].splitlines()[0] if example['code'] else example['body']}` as a small anchor, then ask what changes and what stays true. "
        f"This keeps the concept readable instead of turning it into a long list of facts. {real} "
        f"The main mistake to avoid is this: {mistake['misconception']} {mistake['correction']}"
    )
    return cap_words(body, 135)


def view_explanation(concept: Dict[str, Any], view: str, parts: Dict[str, Any]) -> str:
    name = concept["concept_name"]
    key = parts["keys"][0]
    example_line = parts["example"]["code"].splitlines()[0] if parts["example"]["code"] else parts["example"]["body"]
    mistake = parts["mistake"]
    if view == "definition_view":
        text = (
            f"{parts['definition']} In this view, focus on what the concept means before using a large example. "
            f"The practical rule is: {ensure_sentence(key)} A small example such as `{example_line}` is useful only because it shows that rule in action. "
            f"Once the meaning is clear, you can recognize the concept in longer programs or database queries without rereading every resource note."
        )
    elif view == "simple_example_view":
        text = (
            f"This view learns {name} through one concrete example: `{example_line}`. First read the line, then name the concept it demonstrates, then explain why it follows the rule: {key} "
            f"The goal is not to memorize a heading like {parts['example']['title']}; the goal is to understand the actual example underneath it. "
            f"After that, check the result against the common mistake: {mistake['misconception']}"
        )
    elif view == "step_by_step_view":
        text = (
            f"This view turns {name} into a repeatable process. Start by identifying where the concept appears, then apply the syntax or structure shown in the example, then check the result. "
            f"The rule guiding each step is: {ensure_sentence(key)} Keep the process short so you can use it while solving a real exercise. "
            f"The final check is to avoid the misconception: {mistake['misconception']}"
        )
    elif view == "analogy_view":
        text = (
            f"Think of {name} like a labeled tool in a workspace: the label helps you find and use the right thing, but the tool still follows its real technical rule. "
            f"For this concept, the rule is: {ensure_sentence(key)} The analogy helps beginners remember the idea, but it must connect back to the actual example `{example_line}`. "
            f"Do not let the analogy replace the rule; use it to make the rule easier to recall."
        )
    elif view == "code_view":
        text = (
            f"This view reads the example as code or syntax, not as a paragraph. Look at `{example_line}` and identify the exact part that demonstrates {name}. "
            f"Then explain each line in plain language and connect it to the rule: {ensure_sentence(key)} "
            f"If the concept has no executable code, treat the shown syntax or structured example as the object to read carefully."
        )
    elif view == "debug_view":
        text = (
            f"This view starts with a likely mistake and fixes it. The bug is based on this misconception: {mistake['misconception']} "
            f"The correction is: {mistake['correction']} Compare the buggy version with the corrected version and point to the rule that changed the answer: {key} "
            f"A good debug explanation says what was wrong, why it was wrong, and how the fixed version follows the concept."
        )
    elif view == "output_prediction_view":
        text = (
            f"This view asks what result will happen after applying {name}. Read the task or code first, predict the output or behavior, then justify the prediction using the rule: {key} "
            f"The example anchor is `{example_line}`. Do not guess from keywords alone; trace the values, rows, nodes, or elements involved. "
            f"The assessment checks the same prediction skill taught in this view."
        )
    elif view == "misconception_view":
        text = (
            f"This view focuses on one wrong idea: {mistake['misconception']} The correction is: {mistake['correction']} "
            f"Use the definition and the example `{example_line}` to see why the tempting answer is wrong. "
            f"When you can explain the difference between the misconception and the rule, you understand {name} more reliably."
        )
    elif view == "transfer_view":
        text = (
            f"This view moves {name} into a practical setting. {parts['real']} The same rule still controls the solution: {key} "
            f"Start with the familiar example, then ask how the rule appears when the names, data, or situation changes. "
            f"Transfer means you are not copying the first example; you are applying its idea to a new case."
        )
    elif view == "challenge_view":
        text = (
            f"This view gives a harder task for {name}. You must combine the definition, one example, and the common mistake instead of recalling only one sentence. "
            f"The key rule is: {ensure_sentence(key)} A strong answer explains the decision, checks the result, and names the misconception it avoided. "
            f"Use the challenge to prove you can apply the concept under slightly less guided conditions."
        )
    elif view == "revision_view":
        text = (
            f"This view compresses {name} for review. Remember the definition, one key rule, one example, and one mistake. "
            f"The key rule is: {ensure_sentence(key)} The example anchor is `{example_line}`. "
            f"The review should be compact enough to reread quickly while still reminding you how to apply the concept."
        )
    elif view == "flashcard_view":
        text = (
            f"This view turns {name} into quick recall cards. Each card checks one separate idea: meaning, rule, example, mistake, or real use. "
            f"The main rule is: {ensure_sentence(key)} Keep the answers short so the cards test memory without hiding the concept inside a long paragraph. "
            f"After recall, use the example `{example_line}` to confirm that the answer is not just memorized wording."
        )
    elif view == "mindmap_view":
        text = (
            f"This view organizes {name} as branches. Put the definition in one branch, key points in another, examples in another, and mistakes in another. "
            f"The central rule is: {ensure_sentence(key)} The map should show relationships, not repeat a full database entry. "
            f"Use it to see how the example, correction, and real use connect."
        )
    elif view == "voice_script_view":
        text = (
            f"Today, we are learning {name}. Start with the meaning in one line: {ensure_sentence(key)} "
            f"Here is the example to keep in mind: {example_line}. If that feels confusing, compare it with the mistake learners often make: {mistake['misconception']} "
            f"The correct takeaway is simple: {mistake['correction']} Now connect that example back to the rule and say what the concept is doing. "
            f"If you can explain the example, name the mistake, and give the corrected idea, you are ready for the quick check."
        )
    else:
        text = parts["beginner_core"]
    min_words = 130 if view == "voice_script_view" else 90
    max_words = 180 if view == "voice_script_view" else 150
    text = ensure_min_words(
        text,
        min_words,
        f"Use this view to study {name} by connecting the definition, example, mistake, and key rule from the resource.",
    )
    result = remove_repeated_phrases(truncate_to_sentence(text, max_words))
    if len(result.split()) < min_words:
        result = ensure_min_words(
            result,
            min_words,
            f"This view keeps {name} tied to the resource definition, one concrete example, the common mistake, and the correct rule.",
        )
    return cap_words(result, max_words)


def step_by_step(concept: Dict[str, Any], parts: Dict[str, Any]) -> List[str]:
    name = concept["concept_name"]
    if concept["domain"] == "Python" and name.lower() == "variables":
        return [
            "Choose a valid variable name.",
            "Assign a value using =.",
            "Use the variable name later in code.",
            "Avoid invalid names like 2score or Python keywords.",
        ]
    return [
        "Identify the concept in the prompt or example.",
        "Apply the syntax, structure, or rule shown.",
        "Check the result against the expected behavior.",
        "Avoid the common mistake described in this packet.",
    ]


def formatted_example(parts: Dict[str, Any]) -> str:
    example = parts["example"]
    if example["body"]:
        return f"{example['title']}\n{example['body']}"
    return example["title"]


def code_or_task(concept: Dict[str, Any], view: str, parts: Dict[str, Any]) -> str:
    code = parts["example"]["code"] or parts["example"]["body"]
    key = parts["keys"][0]
    if view == "debug_view":
        buggy = make_buggy_example(concept, code)
        return f"BUGGY VERSION:\n{buggy}\n\nFIXED VERSION:\n{code}\n\nMistake: {parts['mistake']['misconception']}"
    if view == "output_prediction_view":
        return f"PREDICT THE RESULT:\n{code}\n\nQuestion: What output, value, rows, or structure will this produce?\nAnswer: Use the rule: {key}"
    if view == "code_view":
        return f"{code}\n\nLINE BY LINE:\n" + "\n".join(line_by_line(code))
    if view == "challenge_view":
        return f"Challenge: Create a new example of {concept['concept_name']} that follows this rule: {key}"
    return f"Task: Explain how this example demonstrates {concept['concept_name']}.\n{code}"


def make_buggy_example(concept: Dict[str, Any], code: str) -> str:
    name = concept["concept_name"].lower()
    if concept["domain"] == "Python" and "variable" in name:
        return "2score = 10\nprint(2score)"
    if concept["domain"] == "SQL" and "join" in name:
        return "SELECT customers.name, orders.product\nFROM customers, orders;"
    if "tree" in name:
        return "Search every node without using the tree ordering rule."
    first = code.splitlines()[0] if code.splitlines() else f"{concept['concept_name']} example"
    return f"Incorrectly apply the concept without checking its rule:\n{first}"


def flashcards(concept: Dict[str, Any], parts: Dict[str, Any]) -> List[Dict[str, str]]:
    return [
        {"front": f"What is {concept['concept_name']}?", "back": parts["definition"]},
        {"front": "What is the key rule?", "back": parts["keys"][0]},
        {"front": "What is one example?", "back": formatted_example(parts)},
        {"front": "What mistake should you avoid?", "back": f"{parts['mistake']['misconception']} {parts['mistake']['correction']}"},
        {"front": "Where can this be used?", "back": parts["real"]},
    ]


def mindmap(concept: Dict[str, Any], parts: Dict[str, Any]) -> Dict[str, Any]:
    example_line = parts["example"]["code"].splitlines()[0] if parts["example"]["code"] else formatted_example(parts)
    return {
        "centre": concept["concept_name"],
        "branches": [
            {"label": "Definition", "children": [parts["definition"], parts["keys"][0]]},
            {"label": "Key Points", "children": (parts["keys"] + [parts["definition"]])[:4]},
            {"label": "Example", "children": [parts["example"]["title"], example_line]},
            {"label": "Common Mistake", "children": [parts["mistake"]["misconception"], parts["mistake"]["correction"]]},
            {"label": "Real-World Use", "children": [parts["real"], f"Apply the same rule in {concept['domain']} practice."]},
            {"label": "Next Step", "children": [cap_words(parts["next"], 24), "Answer one aligned quick check."]},
        ],
    }


def revision_summary(concept: Dict[str, Any], parts: Dict[str, Any]) -> str:
    sentences = [
        f"{concept['concept_name']} means {parts['definition']}",
        f"The main rule is: {parts['keys'][0]}",
        f"A useful example is `{parts['example']['code'].splitlines()[0] if parts['example']['code'] else parts['example']['body']}`.",
        f"A common mistake is {parts['mistake']['misconception']}",
        f"The correction is {parts['mistake']['correction']}",
        f"In practice, {parts['real']}",
    ]
    text = ensure_min_words(" ".join(ensure_sentence(s) for s in sentences), 80, f"Review {concept['concept_name']} by explaining the example in your own words.")
    return truncate_to_sentence(remove_repeated_phrases(text), 140)


def common_mistake_text(parts: Dict[str, Any]) -> str:
    if parts.get("source_level") == "easy_content" and str(parts["mistake"]["misconception"]).lower().startswith("a beginner mistake"):
        return truncate_to_sentence(
            f"{parts['mistake']['misconception']} Remember the easy rule: {parts['keys'][0]}",
            70,
        )
    text = f"Many learners think {parts['mistake']['misconception']} Actually, {parts['mistake']['correction']}"
    return truncate_to_sentence(text, 70)


def quick_check_for(concept: Dict[str, Any], view: str, parts: Dict[str, Any]) -> str:
    name = concept["concept_name"]
    example_line = parts["example"]["code"].splitlines()[0] if parts["example"]["code"] else parts["example"]["body"]
    checks = {
        "definition_view": f"What does {name} mean in this packet?",
        "simple_example_view": f"What does `{example_line}` show about {name}?",
        "step_by_step_view": f"Which step checks whether the result follows the rule for {name}?",
        "analogy_view": f"How does the analogy connect back to the real rule for {name}?",
        "code_view": f"What does the first line of the example do?",
        "debug_view": f"What mistake does the buggy version make?",
        "output_prediction_view": "What result should happen when the example is traced?",
        "misconception_view": f"Why is the misconception about {name} wrong?",
        "transfer_view": f"How would you use {name} in the real-world scenario?",
        "challenge_view": f"What rule must your harder {name} solution still follow?",
        "revision_view": f"What is the one sentence takeaway for {name}?",
        "flashcard_view": f"Which flashcard checks the common mistake for {name}?",
        "mindmap_view": f"Which mindmap branch connects the example to the mistake?",
        "voice_script_view": f"What should you say back in your own words about {name}?",
    }
    return checks.get(view, f"What is the key rule for {name}?")


def assessments(concept: Dict[str, Any], view: str, parts: Dict[str, Any]) -> List[Dict[str, Any]]:
    name = concept["concept_name"]
    key = parts["keys"][0]
    misconception = parts["mistake"]["misconception"]
    example_line = parts["example"]["code"].splitlines()[0] if parts["example"]["code"] else parts["example"]["body"]
    source_level = parts["source_level"]
    linked_points = [key, example_line, parts["mistake"]["misconception"]]
    base = {
        "linked_teaching_view": view,
        "linked_teaching_key_point": key,
        "source_level": source_level,
        "linked_content_points": linked_points,
    }

    def mcq(task_type: str, question: str) -> Dict[str, Any]:
        if task_type not in parts["allowed_assessment_types"]:
            task_type = parts["allowed_assessment_types"][0]
        return {
            **base,
            "task_type": task_type,
            "question": question,
            "options": [
                f"A) {key}",
                f"B) {misconception}",
                f"C) Use the example heading without reading the example content.",
                f"D) Apply the misconception first and check the rule later.",
            ],
            "answer": "A",
            "explanation": f"A is correct because this {view} packet teaches: {key}",
            "alignment_reason": f"This question checks only the {source_level} points taught in {view}.",
        }

    fill = {
        **base,
        "task_type": "fill_in_the_blank",
        "question": f"Fill in the blank from this packet: the key rule for {name} is ____.",
        "answer": key,
        "explanation": f"The blank uses the key rule taught in {view}: {key}",
        "alignment_reason": f"Tests recall of the {source_level} key term introduced in this view.",
    }
    if source_level == "easy_content":
        if view == "misconception_view":
            return [
                {
                    **base,
                    "task_type": "true_or_false",
                    "statement": misconception,
                    "question": f"True or false: {misconception}",
                    "answer": "false",
                    "explanation": f"False. The easy correction is: {parts['mistake']['correction']}",
                    "alignment_reason": "This true/false item checks only the easy misconception taught in the packet.",
                },
                fill,
            ]
        return [mcq("mcq", quick_check_for(concept, view, parts)), fill]
    if source_level == "revision_content":
        return [
            {
                **base,
                "task_type": "concept_recall",
                "question": f"Which review point best summarizes {name}?",
                "answer": key,
                "explanation": f"The revision packet summarizes this point: {key}",
                "alignment_reason": "This recall item checks only the revision content shown in the packet.",
            },
            {
                **base,
                "task_type": "flashcard",
                "question": f"What flashcard answer should you remember for {name}?",
                "answer": key,
                "explanation": "The answer comes from the revision flashcard/key point.",
                "alignment_reason": "This flashcard item is locked to revision_content.",
            },
        ]
    if source_level == "hard_content":
        task_type = "transfer_question" if view == "transfer_view" else "challenge_question" if view == "challenge_view" else "multi_step_challenge"
        return [
            {
                **base,
                "task_type": task_type,
                "question": f"Using the hard {name} content, how should the rule transfer to this challenge: {example_line}?",
                "answer": key,
                "explanation": f"The hard answer must use this deeper point: {key}",
                "alignment_reason": "This question uses only the hard transfer/challenge content taught in this packet.",
            }
        ]
    if view == "step_by_step_view":
        return [
            {
                **base,
                "task_type": "code_reasoning_task",
                "question": f"Which practical step should you use first for the medium {name} task?",
                "steps": step_by_step(concept, parts),
                "answer": step_by_step(concept, parts)[0],
                "explanation": "The packet teaches identifying the concept, applying the rule, checking the result, and avoiding the common mistake.",
                "alignment_reason": "Uses the exact medium step_by_step entries from this teaching view.",
            },
        ]
    if view == "debug_view":
        buggy = make_buggy_example(concept, parts["example"]["code"] or parts["example"]["body"])
        return [
            {
                **base,
                "task_type": "debug_task",
                "question": f"What should be fixed in the buggy {name} example?",
                "buggy_code": buggy,
                "buggy_example": buggy,
                "expected_fix": parts["example"]["code"] or parts["example"]["body"],
                "hint": f"Compare the bug with this misconception: {misconception}",
                "answer": parts["mistake"]["correction"],
                "explanation": f"The fixed version follows the packet rule: {key}",
                "alignment_reason": "The bug is derived from the medium misconception taught in debug_view.",
            },
        ]
    if view in {"code_view", "output_prediction_view"}:
        return [
            {
                **base,
                "task_type": "output_prediction",
                "code": parts["example"]["code"] or parts["example"]["body"],
                "example": formatted_example(parts),
                "question": f"What result or behavior should you expect from the shown {name} example?",
                "expected_output": key,
                "answer": key,
                "explanation": f"The prediction is justified by the teaching rule: {key}",
                "alignment_reason": f"This directly tests the medium example used in {view}.",
            },
        ]
    if view == "misconception_view":
        return [
            {
                **base,
                "task_type": "misconception_check",
                "statement": misconception,
                "question": f"Which correction fixes this misconception: {misconception}",
                "answer": parts["mistake"]["correction"],
                "explanation": f"The medium correction is: {parts['mistake']['correction']}",
                "alignment_reason": "Tests the medium misconception and correction from misconception_view.",
            },
        ]
    return [mcq("code_reasoning_task", quick_check_for(concept, view, parts))]


def build_packet(concept: Dict[str, Any], view: str) -> Dict[str, Any]:
    difficulty = difficulty_for(view)
    level_content = select_content_for_packet(concept, difficulty, view)
    parts = parts_from_level(concept, level_content)
    source_level = parts["source_level"]
    content = {
        "title": f"{concept['concept_name']} - {label(view)}",
        "learning_goal": parts["learning_goal"],
        "beginner_explanation": view_explanation(concept, view, parts),
        "definition": parts["definition"],
        "why_it_matters": parts["real"],
        "step_by_step": step_by_step(concept, parts),
        "example": formatted_example(parts),
        "code_or_task_example": code_or_task(concept, view, parts),
        "common_mistake": common_mistake_text(parts),
        "real_world_use": parts["real"],
        "key_points_used": parts["keys"],
        "misconceptions_used": [parts["mistake"]["misconception"]],
        "quick_check": quick_check_for(concept, view, parts),
        "revision_line": ensure_sentence(f"{concept['concept_name']} is best remembered as {parts['keys'][0]}"),
        "resources_used": resources_used(),
    }
    if view == "flashcard_view":
        content["flashcards"] = flashcards(concept, parts)
    if view == "mindmap_view":
        content["mindmap"] = mindmap(concept, parts)
    packet = {
        "packet_id": f"{safe_name(concept['domain'])}_{safe_name(concept['concept_id'])}_{view}",
        "domain": concept["domain"],
        "concept_id": concept["concept_id"],
        "concept_name": concept["concept_name"],
        "difficulty": difficulty,
        "source_level": source_level,
        "teaching_view": view,
        "content_sections_used": content_sections_used(source_level),
        "resource_sections_used": resources_used(),
        "level_summary": level_summary(level_content),
        "teaching_content": content,
        "aligned_assessments": assessments(concept, view, parts),
        "hint": f"Look at the example first, name the concept, then check whether your answer avoids the listed misconception.",
        "feedback_template": {
            "correct": f"Correct. You applied the key rule for {concept['concept_name']}.",
            "partial": f"You are close. Connect your answer more directly to this rule: {parts['keys'][0]}.",
            "wrong": f"Review the definition and the common mistake: {parts['mistake']['misconception']}",
        },
        "revision_summary": revision_summary(concept, parts),
        "next_step": f"{cap_words(parts['next'], 28)} Practice one aligned question from {view}.",
    }
    packet = remove_content_leakage_between_levels(dedupe_fields(packet))
    apply_quality_gate(packet, item_type="packet")
    attach_version_metadata(packet, source=packet, concept_resource=concept, website_ready=packet.get("website_ready", False))
    return packet


def content_sections_used(source_level: str) -> List[str]:
    return {
        "easy_content": ["definition", "key_points", "example", "common_mistake"],
        "medium_content": ["definition", "key_points", "examples", "syntax_or_rules", "common_mistakes", "debug_or_output_example"],
        "hard_content": ["advanced_points", "edge_cases", "transfer_examples", "real_world_use", "challenge_tasks"],
        "revision_content": ["summary", "flashcards", "weakness_review"],
    }[source_level]


def level_summary(level_content: Dict[str, Any]) -> str:
    if level_content["source_level"] == "easy_content":
        return truncate_to_sentence(f"Easy: {level_content['definition']} Example: {level_content['example']}", 45)
    if level_content["source_level"] == "medium_content":
        return truncate_to_sentence(f"Medium: {level_content['learning_goal']} Rules: {'; '.join(level_content.get('syntax_or_rules', [])[:2])}", 55)
    if level_content["source_level"] == "hard_content":
        return truncate_to_sentence(f"Hard: {level_content['learning_goal']} Transfer: {level_content['real_world_use']}", 55)
    return truncate_to_sentence(f"Revision: {level_content.get('summary', '')}", 55)


def validate_assessment_with_source_level(packet: Dict[str, Any], assessment: Dict[str, Any]) -> bool:
    return (
        assessment.get("source_level") == packet.get("source_level")
        and assessment.get("task_type") in get_allowed_assessment_types(packet.get("source_level"))
        and assessment.get("linked_teaching_view") == packet.get("teaching_view")
        and bool(assessment.get("linked_content_points"))
    )


def remove_content_leakage_between_levels(packet: Dict[str, Any]) -> Dict[str, Any]:
    hard_only = ["identity", "equality", "mutable", "reference", "swap"]
    if packet.get("source_level") == "easy_content":
        for assessment in packet.get("aligned_assessments", []):
            question = assessment.get("question", "")
            for term in hard_only:
                question = re.sub(rf"\b{term}\b", "value", question, flags=re.I)
            assessment["question"] = question
    if (
        packet.get("source_level") == "easy_content"
        and packet.get("domain") == "Python"
        and str(packet.get("concept_name", "")).lower() == "variables"
    ):
        easy_replacements = {
            r"\breferences?\b": "names",
            r"\bobjects?\b": "values",
            r"\bmemory\b": "a program",
            r"\bidentity\b": "name",
            r"\bequality\b": "same value",
            r"\bmutable\b": "changeable",
            r"\bswap\b": "change",
        }

        def scrub(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: scrub(v) for k, v in value.items()}
            if isinstance(value, list):
                return [scrub(v) for v in value]
            if isinstance(value, str):
                result = value
                for pattern, replacement in easy_replacements.items():
                    result = re.sub(pattern, replacement, result, flags=re.I)
                return result
            return value

        packet = scrub(packet)
    return packet


def dedupe_fields(packet: Dict[str, Any]) -> Dict[str, Any]:
    tc = packet["teaching_content"]
    seen = set()
    for field in ["definition", "beginner_explanation", "common_mistake"]:
        kept = []
        original = tc.get(field, "")
        for sentence in split_sentences(tc.get(field, "")):
            key = re.sub(r"\W+", " ", sentence.lower()).strip()
            if key not in seen or field == "definition":
                kept.append(ensure_sentence(sentence))
                seen.add(key)
        if kept:
            candidate = " ".join(kept)
            if field == "beginner_explanation" and len(candidate.split()) < 90:
                tc[field] = original
            else:
                tc[field] = candidate
    packet["revision_summary"] = remove_repeated_phrases(packet.get("revision_summary", ""))
    return packet


def markdown(packets: List[Dict[str, Any]]) -> str:
    lines = ["# CogniTutorLM Learning Packets", ""]
    for packet in packets:
        tc = packet["teaching_content"]
        lines += [
            f"## {packet['domain']} / {packet['concept_id']} / {packet['concept_name']} / {packet['teaching_view']}",
            "",
            f"### {tc['title']}",
            tc["beginner_explanation"],
            "",
            f"Definition: {tc['definition']}",
            f"Example: {tc['example']}",
            f"Common mistake: {tc['common_mistake']}",
            f"Revision: {packet['revision_summary']}",
            "",
        ]
    return "\n".join(lines)


def write_outputs(packets: List[Dict[str, Any]]) -> None:
    PACKETS_DIR.mkdir(parents=True, exist_ok=True)
    (PACKETS_DIR / "by_subject").mkdir(parents=True, exist_ok=True)
    (PACKETS_DIR / "by_concept").mkdir(parents=True, exist_ok=True)
    PACKET_OUTPUT.write_text(json.dumps(packets, indent=2, ensure_ascii=False), encoding="utf-8")
    PACKET_OUTPUT.with_suffix(".md").write_text(markdown(packets), encoding="utf-8")
    by_subject: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_concept: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for packet in packets:
        by_subject[packet["domain"]].append(packet)
        by_concept[f"{safe_name(packet['domain'])}_{safe_name(packet['concept_id'])}_{safe_name(packet['concept_name'])}"].append(packet)
    for domain, rows in by_subject.items():
        stem = safe_name(domain)
        (PACKETS_DIR / "by_subject" / f"{stem}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        (PACKETS_DIR / "by_subject" / f"{stem}.md").write_text(markdown(rows), encoding="utf-8")
    for stem, rows in by_concept.items():
        (PACKETS_DIR / "by_concept" / f"{stem}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        (PACKETS_DIR / "by_concept" / f"{stem}.md").write_text(markdown(rows), encoding="utf-8")


def generate_packets() -> List[Dict[str, Any]]:
    concepts = load_concept_resources()
    print_concept_summary(concepts)
    return [build_packet(concept, view) for concept in concepts for view in TEACHING_VIEWS]


def main() -> None:
    packets = generate_packets()
    write_outputs(packets)
    print(f"Learning packets generated: {len(packets)}")
    print(f"Output: {PACKET_OUTPUT}")
    print("STATUS: PASS" if len(packets) == 532 else "STATUS: CHECK")


if __name__ == "__main__":
    main()
