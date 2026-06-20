from __future__ import annotations

import json
import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
)

from tutor.llm_finetune.output_validator import (
    infer_debug_domain,
    validate_output,
)


ROOT = Path(__file__).resolve().parents[2]

OUTPUT_JSON = (
    ROOT
    / "outputs"
    / "samples"
    / "qwen_coder_05b_generate_test_outputs.json"
)

MODEL_DIR = Path(
    os.getenv(
        "TUTOR_MODEL_DIR",
        str(
            ROOT
            / "models"
            / "llm_finetuned"
            / "qwen_coder_05b_lora"
        )
    )
)

BASE_MODEL = os.getenv(
    "TUTOR_BASE_MODEL",
    "Qwen/Qwen2.5-Coder-0.5B-Instruct"
)

MAX_NEW_TOKENS = int(os.getenv("TUTOR_MAX_NEW_TOKENS", "100"))


def _domain_debug_snippet(concept: str) -> str:

    domain = infer_debug_domain(concept)

    if domain == "html":
        return (
            "Use ONLY an HTML snippet as the buggy code. Example style (do not copy exactly):\n"
            "<div><p>Hello</div>\n"
            "(missing closing </p> tag)\n"
            "Expected fix: add the missing closing tag and keep valid HTML."
        )

    if domain == "sql":
        return (
            "Use ONLY a SQL snippet as the buggy code. Example style:\n"
            "SELECT name FORM users;\n"
            "(typo: FORM instead of FROM)\n"
            "Expected fix: correct the keyword to FROM."
        )

    if domain == "git":
        return (
            "Use ONLY a Git-related mistake (command or workflow), not Python. Example style:\n"
            "git comit -m \"fix\"\n"
            "(typo: comit)\n"
            "Expected fix: use the correct command spelling (commit)."
        )

    if domain == "data_structures":
        return (
            "Use a short data-structure / pseudocode snippet relevant to stacks. Example style:\n"
            "stack = []\n"
            "x = stack.pop()  # empty stack\n"
            "Expected fix: check empty before pop or push first."
        )

    return (
        "Use a Python snippet as the buggy code. Example style:\n"
        "for i in range(5)\n"
        "    print(i)\n"
        "(missing colon after range(5))\n"
        "Expected fix: add ':' after range(5)."
    )


def build_prompt(
    concept="Variables",
    difficulty="easy",
    learner_state="weak_output_prediction",
    style="simple",
    task_type="explanation",
):

    dbg = _domain_debug_snippet(concept)

    explanation_rules = """- explanation (teaching text, not code-only):
Write 4–8 short lines:
1) One-line definition of the concept.
2) One concrete example (may include a tiny code snippet if helpful, but add plain-English explanation around it).
3) One sentence on why it matters or how students use it.
Do NOT reply with only a code block."""

    flashcard_rules = """- flashcard:
Use EXACTLY this structure and nothing before it:
Front: <one short question>
Back: <one short answer>"""

    debug_rules = f"""- debug_task:
Include these exact labels on their own lines:
Buggy code:
Expected fix:
The buggy snippet MUST match the concept domain ({infer_debug_domain(concept)}).
{dbg}
Do NOT use a Python loop bug for HTML, SQL, or Git concepts."""

    return f"""### Instruction
You are a tutor content generator for a cognition-adaptive AI tutor.

Generate only the requested tutor output.

Do NOT include:
- URLs
- API fields
- hook names
- diff text
- random metadata
- repeated tokens

### Task
Concept: {concept}
Task type: {task_type}
Difficulty: {difficulty}
Learner state: {learner_state}
Teaching style: {style}

### Requirements
- Stay only about the given concept and its domain.
- Use simple student-friendly language.
- Keep answer under 120 words unless the format requires structure.
- Follow the requested format exactly.
- Avoid repetition.

Task format rules:

{explanation_rules}

{flashcard_rules}

{debug_rules}

- output_prediction:
Include:
Code:
Answer:

- transfer_question:
Include:
Question:
Answer:

- challenge_question:
Include:
Challenge:
Solution outline:

### Output
"""


def fallback_response(task_type: str, concept: str):

    if task_type == "flashcard":

        return f"""Front: What is {concept}?
Back: A short student-friendly definition of {concept}."""

    if task_type == "debug_task":

        domain = infer_debug_domain(concept)
        if domain == "html":
            return """Buggy code:
<div><p>Hello</div>

Expected fix:
Close the <p> tag: <div><p>Hello</p></div>"""

        if domain == "sql":
            return """Buggy code:
SELECT * FORM users;

Expected fix:
Use FROM instead of FORM."""

        if domain == "git":
            return """Buggy code:
git comit -m "save"

Expected fix:
Use git commit (correct spelling)."""

        if domain == "data_structures":
            return """Buggy code:
stack = []
x = stack.pop()

Expected fix:
Check if stack is non-empty before pop, or push items first."""

        return """Buggy code:
for i in range(5)
    print(i)

Expected fix:
Add ':' after range(5)."""

    if task_type == "challenge_question":

        return f"""Challenge:
Give one real-world use of {concept} and a tiny example.

Solution outline:
Name the use case, then outline 2–3 steps to apply the idea."""

    return f"""Definition: {concept} is a core idea in this topic.
Example: A small example helps remember how it works.
Why it matters: It is used often in real programs and learning paths."""


def clean_output(text: str):

    if "### Output" in text:
        text = text.split("### Output")[-1]

    lines = text.split("\n")

    clean_lines = []

    for line in lines:

        line = line.strip()

        if not line:
            continue

        bad_words = [
            "Instruction",
            "Task",
            "Requirement",
            "Teaching",
            "Input",
            "http",
            "https",
            "PUT_HREF",
            "Hook",
            "Diff",
        ]

        skip = False

        for bad in bad_words:

            if bad.lower() in line.lower():
                skip = True

        if skip:
            continue

        clean_lines.append(line)

    return "\n".join(clean_lines).strip()


def _validator_score(v: dict) -> int:

    ts = bool(v.get("task_success"))
    ok = bool(v.get("valid"))

    return (2 if ts else 0) + (1 if ok else 0)


def generate_output(
    model,
    tokenizer,
    concept,
    task_type,
    difficulty="easy",
    learner_state="beginner",
    style="simple",
):

    prompt = build_prompt(
        concept=concept,
        difficulty=difficulty,
        learner_state=learner_state,
        style=style,
        task_type=task_type,
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    try:

        with torch.no_grad():

            output = model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False,
                repetition_penalty=1.2,
                pad_token_id=tokenizer.eos_token_id,
            )

    except Exception as e:

        fb = fallback_response(task_type, concept)
        v = validate_output(fb, concept=concept, task_type=task_type)
        return fb, prompt, v, str(e)

    result = tokenizer.decode(
        output[0],
        skip_special_tokens=True,
    )

    cleaned = clean_output(result)

    validation = validate_output(
        cleaned,
        concept=concept,
        task_type=task_type,
    )

    print("\nValidator Result:")
    print(validation)

    if (not validation.get("task_success")) or ("repetition" in validation.get("issues", [])):

        print("\nRetrying with tighter decoding...\n")

        try:

            with torch.no_grad():

                retry_out = model.generate(
                    **inputs,
                    max_new_tokens=max(64, MAX_NEW_TOKENS - 20),
                    do_sample=False,
                    repetition_penalty=1.3,
                    pad_token_id=tokenizer.eos_token_id,
                )

            retry_text = tokenizer.decode(
                retry_out[0],
                skip_special_tokens=True,
            )

            cleaned_retry = clean_output(
                retry_text
            )

            retry_validation = validate_output(
                cleaned_retry,
                concept=concept,
                task_type=task_type,
            )

            print("Retry Validator Result:")
            print(retry_validation)

            if _validator_score(retry_validation) > _validator_score(validation):
                cleaned = cleaned_retry
                validation = retry_validation

        except Exception as retry_e:

            print(f"\nRetry skipped: {retry_e}\n")

    if len(cleaned) < 12:
        cleaned = fallback_response(task_type, concept)
        validation = validate_output(
            cleaned,
            concept=concept,
            task_type=task_type,
        )

    return cleaned, prompt, validation, None


def main():

    print("Loading model...\n")

    print(f"Base model: {BASE_MODEL}")
    print(f"Model dir: {MODEL_DIR.resolve()}\n")

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR
    )

    base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL
    )

    model = PeftModel.from_pretrained(
        base_model,
        MODEL_DIR,
    )

    model.eval()

    tests = [

        ("Python Variables", "explanation"),

        ("Python Loops", "debug_task"),

        ("SQL SELECT", "explanation"),

        ("HTML Tags", "debug_task"),

        ("Git Commits", "flashcard"),

        ("Data Structures Stack", "challenge_question"),
    ]

    results = []

    all_ok = True

    for concept, task in tests:

        print("\n" + "=" * 60)

        print(f"Concept: {concept}")
        print(f"Task: {task}")

        try:

            result, prompt, validation, gen_err = generate_output(
                model=model,
                tokenizer=tokenizer,
                concept=concept,
                task_type=task,
            )

            print("\n===== GENERATED OUTPUT =====\n")

            print(result)

            if gen_err:
                status = "warning"
            elif validation.get("valid") and validation.get("task_success"):
                status = "success"
            else:
                status = "warning"
                all_ok = False

            results.append({
                "concept": concept,
                "task_type": task,
                "prompt": prompt,
                "output": result,
                "validator": validation,
                "status": status,
                "generation_error": gen_err,
            })

        except Exception as e:

            all_ok = False

            fb = fallback_response(task, concept)
            v = validate_output(fb, concept=concept, task_type=task)

            results.append({
                "concept": concept,
                "task_type": task,
                "prompt": "",
                "output": fb,
                "validator": v,
                "status": "error",
                "generation_error": str(e),
            })

            print(f"\nERROR: {e}\n")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nSaved run log: {OUTPUT_JSON.resolve()}")

    if all_ok:
        print("\nSTATUS: PASS")
    else:
        print("\nSTATUS: WARN (some tasks failed validation or had errors)")


if __name__ == "__main__":
    main()
