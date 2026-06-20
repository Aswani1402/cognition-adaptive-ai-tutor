import json
import random
from pathlib import Path


OUTPUT_PATH = Path("evaluation_outputs/generation_dataset.jsonl")


LEARNING_SIGNALS = ["weak", "partial", "mastered"]
STRATEGIES = ["remedial", "practice", "advanced"]
CONTENT_TYPES = [
    "flashcard",
    "quick_recap",
    "mini_challenge",
    "voice_script",
    "mind_map"
]
DIFFICULTIES = ["easy", "medium", "hard"]


def simulate_state():
    mastery = round(random.uniform(0.0, 1.0), 2)
    behavior = round(random.uniform(0.0, 1.0), 2)

    if mastery < 0.4:
        signal = "weak"
    elif mastery < 0.75:
        signal = "partial"
    else:
        signal = "mastered"

    return {
        "mastery": mastery,
        "behavior": behavior,
        "learning_signal": signal,
    }


def label_decision(state):
    # introduce randomness (20% exploration)
    if random.random() < 0.2:
        return (
            random.choice(STRATEGIES),
            random.choice(CONTENT_TYPES),
            random.choice(DIFFICULTIES),
        )

    if state["learning_signal"] == "weak":
        return "remedial", "flashcard", "easy"

    if state["learning_signal"] == "partial":
        return "practice", "mini_challenge", "medium"

    return "advanced", "mind_map", "hard"

def build_row():
    state = simulate_state()

    strategy, content_type, difficulty = label_decision(state)

    return {
        "mastery": state["mastery"],
        "behavior": state["behavior"],
        "learning_signal": state["learning_signal"],
        "time_taken": round(random.uniform(5, 60), 2),
        "confidence": random.randint(1, 3),
        "hint_used": random.randint(0, 1),
        "strategy": strategy,
        "content_type": content_type,
        "difficulty": difficulty,
    }

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for _ in range(2000):
        rows.append(build_row())

    with open(OUTPUT_PATH, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print("Dataset created:", OUTPUT_PATH)
    print("Rows:", len(rows))


if __name__ == "__main__":
    main()