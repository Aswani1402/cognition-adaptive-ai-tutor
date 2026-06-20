import argparse
import json
from pathlib import Path

import torch

from src.model import CogniTutorLM, CogniTutorLMConfig
from src.tokenizer_wrapper import CogniTutorTokenizer
from src.format_validator import validate_output


ROOT_DIR = Path(__file__).resolve().parents[1]


def extract_json_object(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()
    return text


def clean_generated_answer(text: str) -> str:
    text = text.strip()

    stop_markers = [
        "<eos>",
        "</s>",
        "<bos>",
        "<instruction>",
        "<format_rule>",
        "<task>",
        "<content>",
        "<key_points>",
        "<misconceptions>",
        "<examples>",
        "<answer>",
    ]

    for marker in stop_markers:
        if marker in text:
            text = text.split(marker, 1)[0].strip()

    # Remove common repeated phrase issue.
    text = text.replace("This is This is", "This is")

    return text.strip()


def fallback_output(task_type, concept_name, domain, base_content, key_points):
    key = key_points.split("|")[0].strip() if key_points else f"{concept_name} is a key concept in {domain}."

    if task_type == "mcq":
        return {
            "question": f"Which statement best describes {concept_name}?",
            "options": [
                key,
                f"{concept_name} is unrelated to {domain}.",
                f"{concept_name} is only used in advanced topics.",
                f"{concept_name} can be ignored.",
            ],
            "answer": key,
            "explanation": f"The correct option states the main idea of {concept_name}.",
        }

    if task_type in {"flashcard", "personal_flashcards"}:
        return {
            "front": f"What should you remember about {concept_name}?",
            "back": key,
        }

    if task_type == "debug_task":
        return {
            "buggy_code": "name = Alice\nprint(name)",
            "expected_fix": "name = \"Alice\"\nprint(name)",
            "hint": "Check whether the text value needs quotes.",
        }

    if task_type == "mindmap":
        return {
            "center": concept_name,
            "branches": [
                {"name": "Core idea", "items": [key]},
                {"name": "Practice", "items": ["Try one example."]},
            ],
        }

    if task_type == "output_prediction":
        return {
            "question": "What is the output?",
            "code": "x = 5\nprint(x)",
            "answer": "5",
            "explanation": "x stores 5.",
        }

    return None


def get_device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_checkpoint(checkpoint_path: Path, device):
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    checkpoint = torch.load(checkpoint_path, map_location=device)

    config = checkpoint["config"]
    model_cfg = config["model"]

    lm_config = CogniTutorLMConfig(
        vocab_size=model_cfg["vocab_size"],
        context_length=model_cfg["context_length"],
        n_layers=model_cfg["n_layers"],
        n_heads=model_cfg["n_heads"],
        n_embd=model_cfg["n_embd"],
        dropout=model_cfg["dropout"],
    )

    model = CogniTutorLM(lm_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    return model, lm_config, checkpoint


def build_prompt(
    concept_name: str,
    domain: str,
    difficulty: str,
    learner_state: str,
    teaching_style: str,
    task_type: str,
    base_content: str,
    key_points: str = "",
    misconceptions: str = "",
    examples: str = "",
):
    task_tokens = {
        "explanation": "<task_explanation>",
        "summary": "<task_revision>",
        "flashcard": "<task_flashcard>",
        "mindmap": "<task_mindmap>",
        "mcq": "<task_mcq>",
        "output_prediction": "<task_output_prediction>",
        "debug_task": "<task_debug>",
        "transfer_question": "<task_transfer>",
        "challenge_question": "<task_challenge>",
        "hint": "<task_hint>",
        "feedback": "<task_feedback>",
        "revision_note": "<task_revision>",
        "notebook_summary": "<task_notebook_summary>",
        "mistake_summary": "<task_mistake_summary>",
        "revision_plan": "<task_revision_plan>",
        "weakness_review": "<task_weakness_review>",
        "daily_review": "<task_daily_review>",
        "personal_flashcards": "<task_personal_flashcards>",
    }

    difficulty_tokens = {
        "easy": "<easy>",
        "medium": "<medium>",
        "hard": "<hard>",
    }

    style_tokens = {
        "simple": "<style_simple>",
        "code_first": "<style_code>",
        "analogy": "<style_analogy>",
        "step_by_step": "<style_step_by_step>",
        "question_based": "<style_question_based>",
        "misconception_correction": "<style_misconception_correction>",
        "challenge_based": "<style_challenge_based>",
        "revision_summary": "<style_revision_summary>",
    }

    task_token = task_tokens.get(task_type, f"<task_{task_type}>")
    difficulty_token = difficulty_tokens.get(difficulty, f"<{difficulty}>")
    style_token = style_tokens.get(teaching_style, f"<style_{teaching_style}>")

    if task_type == "mcq":
        format_rule = "JSON only: question, options, answer, explanation. Exactly 4 options."

    elif task_type == "debug_task":
        format_rule = "JSON only: buggy_code, expected_fix, hint."

    elif task_type in {"flashcard", "personal_flashcards"}:
        format_rule = "JSON only: front, back."

    elif task_type == "mindmap":
        format_rule = "JSON only: center, branches."

    elif task_type == "output_prediction":
        format_rule = "JSON only: question, code, answer, explanation."

    else:
        format_rule = "Plain text only."

    prompt = f"""<bos>
<instruction> Generate tutor output.
<format_rule> {format_rule}
{task_token}
{difficulty_token}
{style_token}
<concept> {concept_name}
<domain> {domain}
<learner_state> {learner_state}
<task> {task_type}
<content> {base_content}
<key_points> {key_points}
<misconceptions> {misconceptions}
<examples> {examples}
<answer>"""

    return prompt


@torch.no_grad()
def generate_text(
    model,
    tokenizer,
    prompt: str,
    device,
    max_new_tokens: int = 160,
    temperature: float = 0.8,
    top_k: int = 50,
):
    input_ids = tokenizer.encode(prompt, add_bos=False, add_eos=False)
    input_ids = input_ids[-model.config.context_length :]

    generated = torch.tensor([input_ids], dtype=torch.long, device=device)

    for _ in range(max_new_tokens):
        current_input = generated[:, -model.config.context_length :]

        logits, _ = model(current_input)
        next_token_logits = logits[:, -1, :]

        if temperature <= 0:
            next_token = torch.argmax(next_token_logits, dim=-1, keepdim=True)
        else:
            next_token_logits = next_token_logits / temperature

            if top_k is not None and top_k > 0:
                values, _ = torch.topk(next_token_logits, top_k)
                min_value = values[:, -1].unsqueeze(-1)
                next_token_logits = torch.where(
                    next_token_logits < min_value,
                    torch.full_like(next_token_logits, float("-inf")),
                    next_token_logits,
                )

            probs = torch.softmax(next_token_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)

        generated = torch.cat([generated, next_token], dim=1)

        if next_token.item() == tokenizer.eos_id:
            break

    full_text = tokenizer.decode(generated[0].tolist())

    if "<answer>" in full_text:
        answer = full_text.split("<answer>", 1)[1].strip()
    else:
        answer = full_text[len(prompt) :].strip()

    for stop_token in ["<eos>", "</s>", "<bos>"]:
        if stop_token in answer:
            answer = answer.split(stop_token, 1)[0].strip()

    answer = clean_generated_answer(answer)

    return answer, full_text


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="outputs/checkpoints/cognitutor_s_best.pt",
    )
    parser.add_argument("--task_type", type=str, default="mcq")
    parser.add_argument("--concept_name", type=str, default="Variables")
    parser.add_argument("--domain", type=str, default="Python")
    parser.add_argument("--difficulty", type=str, default="easy")
    parser.add_argument("--learner_state", type=str, default="low_mastery")
    parser.add_argument("--teaching_style", type=str, default="code_first")
    parser.add_argument(
        "--base_content",
        type=str,
        default="A variable is a name used to store and reuse a value in a program.",
    )
    parser.add_argument(
        "--key_points",
        type=str,
        default="A variable is a name bound to an object in memory | Python uses dynamic typing",
    )
    parser.add_argument(
        "--misconceptions",
        type=str,
        default="Variables can be used before assignment",
    )
    parser.add_argument(
        "--examples",
        type=str,
        default='name = "Alice"\\nprint(name)',
    )
    parser.add_argument("--max_new_tokens", type=int, default=160)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top_k", type=int, default=50)

    args = parser.parse_args()
    structured_tasks = {
        "mcq",
        "debug_task",
        "flashcard",
        "mindmap",
        "output_prediction",
        "personal_flashcards",
    }
    default_max_new_tokens = {
        "mcq": 120,
        "flashcard": 80,
        "personal_flashcards": 80,
    }

    device = get_device()
    print(f"Using device: {device}")

    checkpoint_path = ROOT_DIR / args.checkpoint
    model, config, checkpoint = load_checkpoint(checkpoint_path, device)
    tokenizer = CogniTutorTokenizer()

    prompt = build_prompt(
        concept_name=args.concept_name,
        domain=args.domain,
        difficulty=args.difficulty,
        learner_state=args.learner_state,
        teaching_style=args.teaching_style,
        task_type=args.task_type,
        base_content=args.base_content,
        key_points=args.key_points,
        misconceptions=args.misconceptions,
        examples=args.examples,
    )

    answer, full_text = generate_text(
        model=model,
        tokenizer=tokenizer,
        prompt=prompt,
        device=device,
        max_new_tokens=default_max_new_tokens.get(args.task_type, args.max_new_tokens)
        if args.max_new_tokens == 160
        else args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
    )

    if args.task_type in structured_tasks:
        answer = extract_json_object(answer)

    validation = validate_output(
        task_type=args.task_type,
        generated_text=answer,
        concept_name=args.concept_name,
        key_points=args.key_points.split("|") if args.key_points else None,
    )
    if args.task_type in structured_tasks and not validation["valid"]:
        fallback = fallback_output(
            task_type=args.task_type,
            concept_name=args.concept_name,
            domain=args.domain,
            base_content=args.base_content,
            key_points=args.key_points,
        )
        if fallback is not None:
            answer = json.dumps(fallback, ensure_ascii=False)
            validation = validate_output(
                task_type=args.task_type,
                generated_text=answer,
                concept_name=args.concept_name,
                key_points=args.key_points.split("|") if args.key_points else None,
            )

    print("\nPrompt:")
    print(prompt)

    print("\nGenerated answer:")
    print(answer)

    print("\nValidation:")
    print(json.dumps(validation, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
