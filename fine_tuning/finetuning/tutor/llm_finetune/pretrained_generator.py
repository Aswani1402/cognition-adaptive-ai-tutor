from __future__ import annotations

import time

import torch

from tutor.llm_finetune.model_loader import (
    load_model,
)

from tutor.llm_finetune.output_validator import (
    validate_output,
)


LOADED = load_model()

MODEL = LOADED.get("model")

TOKENIZER = LOADED.get("tokenizer")

GENERATION_STATUS = LOADED.get(
    "generation_status",
    "unknown"
)


def build_prompt(
    concept_name,
    difficulty,
    learner_state,
    teaching_style,
    task_type,
):

    return f"""### Instruction
You are an adaptive AI tutor.

Generate only the requested tutor content.

### Tutor Context
Concept: {concept_name}
Difficulty: {difficulty}
Learner state: {learner_state}
Teaching style: {teaching_style}
Task type: {task_type}

### Rules
- Keep answer concise.
- Use student-friendly language.
- Stay relevant to the concept.
- Do not include metadata.
- Do not include URLs or API text.

### Output
"""


def fallback_output(task_type, concept_name):

    if task_type == "flashcard":

        return f"""Front: What is {concept_name}?

Back: {concept_name} is an important programming concept."""

    elif task_type == "debug_task":

        return """Buggy code:
x == 5

Expected fix:
x = 5

Hint:
Use assignment operator."""

    elif task_type == "mcq":

        return """{
  "question": "What is a variable?",
  "options": [
    "Storage",
    "Loop",
    "Function",
    "Class"
  ],
  "answer": "Storage",
  "explanation": "Variables store values."
}"""

    return (
        f"{concept_name} is an important "
        f"programming concept."
    )


def generate_tutor_output(
    concept_resource,
    difficulty,
    learner_state,
    teaching_style,
    task_type,
):

    if MODEL is None or TOKENIZER is None:

        return {

            "status": "warning",

            "generation_status":
                GENERATION_STATUS,

            "output": None,

            "fallback_used": True,

            "error_message":
                LOADED.get("error_message"),
        }

    concept_name = str(
        concept_resource.get(
            "concept_name",
            "Unknown Concept"
        )
    )

    prompt = build_prompt(
        concept_name=concept_name,
        difficulty=difficulty,
        learner_state=learner_state,
        teaching_style=teaching_style,
        task_type=task_type,
    )

    start = time.time()

    try:

        inputs = TOKENIZER(
            prompt,
            return_tensors="pt"
        )

        with torch.no_grad():

            output = MODEL.generate(
                **inputs,
                max_new_tokens=120,
                do_sample=False,
                repetition_penalty=1.2,
                pad_token_id=TOKENIZER.eos_token_id,
            )

        result = TOKENIZER.decode(
            output[0],
            skip_special_tokens=True,
        )

        if "### Output" in result:

            result = result.split(
                "### Output"
            )[-1]

        result = result.strip()

        validation = validate_output(
            result,
            concept=concept_name,
            task_type=task_type,
        )

        if not validation["valid"]:

            result = fallback_output(
                task_type,
                concept_name
            )

        latency = round(
            time.time() - start,
            2
        )

        return {

            "status": "success",

            "generation_status":
                "success",

            "model_name":
                str(MODEL.__class__.__name__),

            "task_type":
                task_type,

            "concept_name":
                concept_name,

            "output":
                result,

            "validator":
                validation,

            "latency_seconds":
                latency,

            "fallback_used":
                not validation["valid"],
        }

    except Exception as e:

        return {

            "status": "warning",

            "generation_status":
                "generation_failed",

            "output": fallback_output(
                task_type,
                concept_name
            ),

            "fallback_used": True,

            "error_message":
                str(e),
        }


if __name__ == "__main__":

    sample_concept = {

        "concept_name": "Python Variables"
    }

    tasks = [

        "explanation",
        "flashcard",
        "debug_task",
        "mcq",
    ]

    for task in tasks:

        print("\n" + "=" * 60)

        print(f"Task: {task}")

        result = generate_tutor_output(
            concept_resource=sample_concept,
            difficulty="easy",
            learner_state="slow_learner",
            teaching_style="simple",
            task_type=task,
        )

        print(result)