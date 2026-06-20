from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "evaluation_outputs" / "reports"

SEARCH_ROOTS = ["tutor", "scripts", "evaluation_outputs/reports", "."]
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml"}
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
PATTERNS = {
    "PPO": re.compile(r"\bPPO\b", re.IGNORECASE),
    "DQN": re.compile(r"\bDQN\b", re.IGNORECASE),
    "Double DQN": re.compile(r"\bDouble\s+DQN\b|double_dqn", re.IGNORECASE),
    "Dueling DQN": re.compile(r"\bDueling\s+DQN\b|dueling_dqn", re.IGNORECASE),
    "contextual bandit": re.compile(r"contextual\s+bandit|bandit_policy", re.IGNORECASE),
    "safety mask": re.compile(r"safety\s+mask|safe_action_mask|rl_safe_action_mask", re.IGNORECASE),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iter_text_files() -> list[Path]:
    files: dict[str, Path] = {}
    for root_name in SEARCH_ROOTS:
        root = ROOT / root_name
        if root.is_file():
            candidates = [root]
        elif root.exists():
            candidates = [path for path in root.rglob("*") if path.is_file()]
        else:
            candidates = []
        for path in candidates:
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            relative = str(path.resolve().relative_to(ROOT)).replace("\\", "/")
            if relative in {
                "evaluation_outputs/reports/final_policy_rl_honesty_check.md",
            }:
                continue
            if path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path.stat().st_size > 2_000_000:
                continue
            files[str(path.resolve())] = path
    return sorted(files.values())


def search_mentions() -> dict[str, list[dict[str, Any]]]:
    mentions = {name: [] for name in PATTERNS}
    for path in iter_text_files():
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    mentions[name].append(
                        {
                            "path": str(path.relative_to(ROOT)),
                            "line": lineno,
                            "text": line.strip()[:260],
                        }
                    )
    return mentions


def file_exists(relative: str) -> bool:
    return (ROOT / relative).exists()


def implementation_status(mentions: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ppo_files = [item for item in mentions["PPO"] if "ppo" in item["path"].lower() and item["path"].endswith(".py")]
    ppo_future_mentions = [
        item for item in mentions["PPO"]
        if any(token in item["text"].lower() for token in ["future", "optional", "not implemented", "not currently implemented", "pending"])
    ]
    safe_negation_tokens = [
        "not implemented",
        "was not implemented",
        "do not claim",
        "not claim",
        "not claimed",
        "no real ppo",
        "no ppo code",
        "future",
        "optional",
        "pending",
        "unless",
        "not found claiming",
        "should be described as",
    ]
    ppo_claim_pattern = re.compile(
        r"\bPPO\b.{0,80}\b(implemented|trained|completed|available|success)\b|"
        r"\b(implemented|trained|completed|available|success)\b.{0,80}\bPPO\b",
        re.IGNORECASE,
    )
    ppo_implemented_claims = [
        item for item in mentions["PPO"]
        if ppo_claim_pattern.search(item["text"])
        and not any(token in item["text"].lower() for token in safe_negation_tokens)
        and "scripts\\final_review\\check_policy_rl_honesty_final.py" not in item["path"]
        and "scripts/final_review/check_policy_rl_honesty_final.py" not in item["path"]
    ]
    dqn_files = [
        "tutor/RL/dqn/dqn_policy.py",
        "tutor/policy/rl/double_dqn_policy.py",
        "tutor/policy/rl/dueling_dqn_policy.py",
    ]
    return {
        "contextual_bandit": {
            "status": "implemented/comparison evidence" if file_exists("tutor/RL/bandit_policy.py") else "not found",
            "files": [path for path in ["tutor/RL/bandit_policy.py", "models/rl/bandit_policy_model.pkl"] if file_exists(path)],
        },
        "dqn": {
            "status": "implemented/comparison evidence" if file_exists("tutor/RL/dqn/dqn_policy.py") else "not found",
            "files": [path for path in dqn_files if file_exists(path)],
        },
        "double_dqn": {
            "status": "implemented/comparison evidence" if file_exists("tutor/policy/rl/double_dqn_policy.py") else "not found",
            "files": [path for path in ["tutor/policy/rl/double_dqn_policy.py"] if file_exists(path)],
        },
        "dueling_dqn": {
            "status": "implemented/comparison evidence" if file_exists("tutor/policy/rl/dueling_dqn_policy.py") else "not found",
            "files": [path for path in ["tutor/policy/rl/dueling_dqn_policy.py"] if file_exists(path)],
        },
        "ppo": {
            "status": "future work / optional extension" if not ppo_files else "implementation file found; review manually",
            "implementation_files": ppo_files,
            "future_work_mentions": ppo_future_mentions[:20],
            "possible_implemented_claims": ppo_implemented_claims[:20],
        },
        "safety_mask": {
            "status": "available" if file_exists("tutor/policy/rl_safe_action_mask.py") else "not found",
            "files": [path for path in ["tutor/policy/rl_safe_action_mask.py", "evaluation_outputs/reports/rl_safe_action_masking_report.md"] if file_exists(path)],
        },
    }


def format_mentions(items: list[dict[str, Any]], limit: int = 12) -> list[str]:
    if not items:
        return ["- None found."]
    return [f"- `{item['path']}:{item['line']}`: {item['text']}" for item in items[:limit]]


def write_report(statuses: dict[str, Any], mentions: dict[str, list[dict[str, Any]]]) -> str:
    ppo_claims = statuses["ppo"]["possible_implemented_claims"]
    lines = [
        "# Final Policy/RL Honesty Check",
        "",
        f"Generated at: `{now_iso()}`",
        "",
        "## Implemented Policy/RL Files Found",
        "",
        f"- Contextual bandit: `{statuses['contextual_bandit']['status']}`; files: `{statuses['contextual_bandit']['files']}`",
        f"- DQN: `{statuses['dqn']['status']}`; files: `{statuses['dqn']['files']}`",
        f"- Double DQN: `{statuses['double_dqn']['status']}`; files: `{statuses['double_dqn']['files']}`",
        f"- Dueling DQN: `{statuses['dueling_dqn']['status']}`; files: `{statuses['dueling_dqn']['files']}`",
        f"- PPO: `{statuses['ppo']['status']}`",
        f"- Safety mask: `{statuses['safety_mask']['status']}`; files: `{statuses['safety_mask']['files']}`",
        "",
        "## PPO Status",
        "",
        "- No real PPO implementation or PPO result artifact should be claimed unless an implementation file and real output are added later.",
        "- Final safe wording: PPO is future work / optional extension.",
        f"- Possible implemented-claim lines found: `{len(ppo_claims)}`",
        "",
    ]
    lines.extend(format_mentions(ppo_claims))
    lines.extend(
        [
            "",
            "## Safety Mask Evidence",
            "",
            "- `tutor/policy/rl_safe_action_mask.py` is the final-review safety-control evidence when present.",
            "- It supports the claim that learned/bandit/DQN recommendations are filtered before becoming learner-facing actions.",
            "",
            "## Mention Summary",
            "",
            "| Term | Mentions found |",
            "|---|---:|",
        ]
    )
    for name, items in mentions.items():
        lines.append(f"| {name} | {len(items)} |")
    lines.extend(
        [
            "",
            "## Final Viva-Safe Wording",
            "",
            "Policy/RL is safety-controlled decision support. Contextual bandit, DQN, Double DQN, and Dueling DQN exist as implemented or comparison evidence where their files/artifacts are present. The final backend does not allow unrestricted autonomous RL control; recommendations are filtered through baseline logic and a safe action mask. PPO was not implemented in this project and should be described as future work / optional extension.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    mentions = search_mentions()
    statuses = implementation_status(mentions)
    report_path = REPORT_DIR / "final_policy_rl_honesty_check.md"
    report_path.write_text(write_report(statuses, mentions), encoding="utf-8")
    print("FINAL POLICY/RL HONESTY CHECK")
    print(f"contextual_bandit: {statuses['contextual_bandit']['status']}")
    print(f"dqn: {statuses['dqn']['status']}")
    print(f"double_dqn: {statuses['double_dqn']['status']}")
    print(f"dueling_dqn: {statuses['dueling_dqn']['status']}")
    print(f"ppo: {statuses['ppo']['status']}")
    print(f"safety_mask: {statuses['safety_mask']['status']}")
    print(f"report: {report_path}")


if __name__ == "__main__":
    main()
