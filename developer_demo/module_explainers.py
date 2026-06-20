TEACHING_VIEWS = ["step-by-step", "code-focused", "analogy", "misconception correction", "revision summary", "challenge/transfer"]
TASK_TYPES = ["MCQ", "fill blank", "true/false", "output prediction", "debug", "code", "transfer", "challenge", "puzzle"]
POLICY_ACTIONS = ["continue", "practice_easy", "practice_medium", "practice_hard", "give_hint", "reteach", "revise", "unlock_next_concept", "move_to_next_difficulty"]


def status_from_source(source, artifact=True):
    if not source:
        return "NOT AVAILABLE"
    return "PASS" if artifact else "FALLBACK"


def behaviour_from_quiz(q):
    if not q:
        return {"state": "Not started", "risk": "NOT AVAILABLE", "source": "No completed interaction."}
    hint_count = int(q.get("hint_count") or 0)
    attempts = int(q.get("attempt_count") or q.get("attempt_no") or 1)
    wrong = int(q.get("wrong_attempt_count") or (0 if q.get("is_correct") else 1))
    confidence = float(q.get("confidence") or 0)
    slow = float(q.get("time_taken_sec") or 0) > 90
    if wrong >= 2 or attempts >= 3:
        state = "struggling"
    elif hint_count > 0 or slow:
        state = "confused"
    elif confidence and confidence < 0.35:
        state = "guessing"
    else:
        state = "stable"
    return {"state": state, "risk": "high" if state == "struggling" else "medium" if state in ("confused", "guessing") else "low", "source": "fallback/proxy signal scoring"}


def teaching_strategy(mastery, behaviour, mistake, difficulty, profile=None):
    if mistake and mistake != "NOT AVAILABLE":
        view = "misconception correction"
    elif behaviour in ("confused", "struggling"):
        view = "step-by-step"
    elif mastery is not None and mastery >= 0.75:
        view = "challenge/transfer"
    elif difficulty == "hard":
        view = "code-focused"
    else:
        view = "analogy"
    return {
        "selected teaching view": view,
        "explanation style": view,
        "difficulty": difficulty or "medium",
        "next teaching step": "reteach/practice" if behaviour in ("confused", "struggling") else "continue",
        "why": f"Selected from mastery={mastery}, behaviour={behaviour}, mistake={mistake}, difficulty={difficulty}.",
    }


def safe_policy(score, mastery, behaviour, prerequisites_met=True):
    allowed = list(POLICY_ACTIONS)
    if not prerequisites_met:
        allowed = [a for a in allowed if a not in ("unlock_next_concept", "move_to_next_difficulty")]
    if behaviour in ("confused", "struggling"):
        final = "reteach"
    elif score is not None and score < 0.5:
        final = "practice_easy"
    elif mastery is not None and mastery >= 0.8 and prerequisites_met:
        final = "unlock_next_concept"
    else:
        final = "continue"
    return {
        "state features used": {"score": score, "mastery": mastery, "behaviour": behaviour, "prerequisites_met": prerequisites_met},
        "raw recommendation": final,
        "safe action mask": allowed,
        "final safe action": final if final in allowed else "continue",
        "reason": "Policy/RL supports decisions, but final progression is safety checked.",
    }
