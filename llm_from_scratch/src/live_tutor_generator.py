import json
import re
import time
from pathlib import Path
from typing import Dict

import torch

from scripts.structured_generation_common import ROOT_DIR, build_prompt, load_concepts
from src.generate import clean_generated_answer, load_checkpoint
from src.tokenizer_wrapper import CogniTutorTokenizer


CHECKPOINT = ROOT_DIR / "models" / "cognitutor_lm_structured_generation" / "best_model.pt"
OUT_JSON = ROOT_DIR / "outputs" / "model_generated" / "live_structured_generator_self_test.json"
OUT_MD = ROOT_DIR / "outputs" / "model_generated" / "live_structured_generator_self_test.md"
JSON_TASKS = {"flashcard", "mcq", "debug_task", "output_prediction", "challenge_question", "mindmap"}

_MODEL = None
_TOKENIZER = None
_DEVICE = None


def _load():
    global _MODEL, _TOKENIZER, _DEVICE
    if _MODEL is None:
        _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _MODEL, _, _ = load_checkpoint(CHECKPOINT, _DEVICE)
        _TOKENIZER = CogniTutorTokenizer()
    return _MODEL, _TOKENIZER, _DEVICE


def extract_first_json_object(text: str) -> str:
    """Return the first balanced JSON object from model text when present."""
    text = str(text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1].strip()
    return text[start:].strip()


def extract_answer_text(decoded_text: str, prompt: str) -> str:
    text = str(decoded_text or "")
    if prompt and prompt in text:
        text = text.split(prompt, 1)[1]
    elif "<answer>" in text:
        text = text.rsplit("<answer>", 1)[1]

    stop_patterns = [
        "<eos>",
        "<bos>",
        "<instruction>",
        "<concept>",
        "<domain>",
        "<context>",
        "</context>",
    ]
    task_match = re.search(r"<task_[^>]+>", text)
    if task_match:
        stop_patterns.append(task_match.group(0))
    stops = [text.find(marker) for marker in stop_patterns if marker in text]
    if stops:
        text = text[: min(stops)]

    text = clean_generated_answer(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


@torch.no_grad()
def _sample(model, tokenizer, prompt, device, max_new_tokens, temperature, top_p, repetition_penalty=1.0):
    ids = tokenizer.encode(prompt, add_bos=False, add_eos=False)
    ids = ids[-model.config.context_length :]
    generated = torch.tensor([ids], dtype=torch.long, device=device)
    for _ in range(max_new_tokens):
        logits, _ = model(generated[:, -model.config.context_length :])
        logits = logits[:, -1, :]
        if repetition_penalty and repetition_penalty != 1.0:
            for token_id in set(generated[0].tolist()):
                if logits[0, token_id] > 0:
                    logits[0, token_id] = logits[0, token_id] / repetition_penalty
                else:
                    logits[0, token_id] = logits[0, token_id] * repetition_penalty
        if temperature <= 0:
            nxt = torch.argmax(logits, dim=-1, keepdim=True)
        else:
            logits = logits / temperature
            probs = torch.softmax(logits, dim=-1)
            sorted_probs, sorted_idx = torch.sort(probs, descending=True)
            keep = torch.cumsum(sorted_probs, dim=-1) <= top_p
            keep[..., 0] = True
            filtered = torch.zeros_like(probs)
            filtered.scatter_(1, sorted_idx, sorted_probs * keep)
            filtered = filtered / filtered.sum(dim=-1, keepdim=True)
            nxt = torch.multinomial(filtered, 1)
        generated = torch.cat([generated, nxt], dim=1)
        if nxt.item() == tokenizer.eos_id:
            break
    raw_text = tokenizer.decode(generated[0].tolist())
    text = extract_answer_text(raw_text, prompt)
    return text, raw_text


def generate_with_cognitutor_lm(
    prompt: str,
    task_type: str,
    max_new_tokens: int = 180,
    temperature: float = 0.7,
    top_p: float = 0.9,
    repetition_penalty: float = 1.0,
) -> dict:
    started = time.time()
    try:
        model, tokenizer, device = _load()
        output, raw_model_output = _sample(model, tokenizer, prompt, device, max_new_tokens, temperature, top_p, repetition_penalty)
        if task_type in JSON_TASKS:
            output = extract_first_json_object(output)
        return {
            "status": "success",
            "model_used": "CogniTutorLM-from-scratch-structured",
            "checkpoint_path_used": str(CHECKPOINT),
            "task_type": task_type,
            "output": output,
            "raw_model_output": raw_model_output,
            "extracted_output": output,
            "generation_parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
            },
            "latency_seconds": round(time.time() - started, 4),
            "error_message": None,
        }
    except Exception as exc:
        return {
            "status": "error",
            "model_used": "CogniTutorLM-from-scratch-structured",
            "checkpoint_path_used": str(CHECKPOINT),
            "task_type": task_type,
            "output": "",
            "raw_model_output": "",
            "extracted_output": "",
            "generation_parameters": {
                "max_new_tokens": max_new_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
            },
            "latency_seconds": round(time.time() - started, 4),
            "error_message": str(exc),
        }


def main() -> None:
    cases = [
        ("Python Variables", "Python", "explanation"),
        ("Python Variables", "Python", "flashcard"),
        ("SQL SELECT Queries", "SQL", "mcq"),
        ("Python Loops", "Python", "debug_task"),
        ("Data Structures Stack", "Data Structures", "challenge_question"),
        ("Git Commits and History", "Git", "revision_summary"),
        ("HTML Tags and Elements", "HTML", "explanation"),
    ]
    concepts = load_concepts()
    results = []
    for name, domain, task in cases:
        concept = next((c for c in concepts if c["domain"] == domain and name.lower().split()[-1] in c["concept_name"].lower()), None)
        concept = concept or next(c for c in concepts if c["domain"] == domain)
        prompt = build_prompt(concept, task)
        result = generate_with_cognitutor_lm(prompt, task, max_new_tokens=160, temperature=0.0, top_p=1.0)
        results.append({"concept_name": name, "domain": domain, "prompt": prompt, **result})
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT_MD.write_text(
        "# Live Structured Generator Self-Test\n\n"
        f"- checkpoint_path_used: {CHECKPOINT}\n\n"
        + "\n\n".join(f"## {r['concept_name']} {r['task_type']}\n\n```text\n{r['output']}\n```" for r in results),
        encoding="utf-8",
    )
    print(f"self_test_items: {len(results)}")
    print(f"checkpoint_path_used: {CHECKPOINT}")
    print(f"output_json: {OUT_JSON}")
    print(f"output_md: {OUT_MD}")


if __name__ == "__main__":
    main()
