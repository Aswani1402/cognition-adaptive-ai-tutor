from __future__ import annotations

import re
from typing import Any


VOICE_SCRIPT_TYPES = {
    "teaching_explanation",
    "revision_summary",
    "mistake_feedback",
    "doubt_explanation",
    "encouragement",
    "next_step_guidance",
}


class VoiceScriptGenerator:
    """Build short spoken-text scripts for frontend TTS playback."""

    MODULE = "VoiceScriptGenerator"
    FRONTEND_COMPONENT = "VoiceScriptCard"
    TONE = "supportive"

    def generate(
        self,
        script_type: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        evidence = evidence or {}
        script_type = str(script_type or "").strip()
        if script_type not in VOICE_SCRIPT_TYPES:
            return {
                "status": "error",
                "module": self.MODULE,
                "script_type": script_type or "unknown",
                "concept_name": self._concept_name(evidence),
                "text": "",
                "tts_ready": False,
                "estimated_duration_sec": 0,
                "tone": self.TONE,
                "frontend_component": self.FRONTEND_COMPONENT,
                "limitations": [
                    f"Unsupported script_type. Supported types: {sorted(VOICE_SCRIPT_TYPES)}",
                    "This module prepares text only and does not synthesize audio.",
                ],
            }

        text = self._build_text(script_type, evidence)
        text = self._clean_for_tts(text)

        return {
            "status": "success",
            "module": self.MODULE,
            "script_type": script_type,
            "concept_name": self._concept_name(evidence),
            "text": text,
            "tts_ready": bool(text),
            "estimated_duration_sec": self._estimate_duration_sec(text),
            "tone": self.TONE,
            "frontend_component": self.FRONTEND_COMPONENT,
            "limitations": [],
        }

    def generate_bundle(self, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        evidence = evidence or {}
        scripts = [self.generate(script_type, evidence) for script_type in sorted(VOICE_SCRIPT_TYPES)]
        return {
            "status": "success",
            "module": self.MODULE,
            "script_count": len(scripts),
            "scripts": scripts,
            "frontend_component": self.FRONTEND_COMPONENT,
            "tts_ready": all(script.get("tts_ready") for script in scripts),
            "limitations": [
                "This bundle contains TTS-ready text only.",
                "Audio playback should be handled by browser Text-to-Speech or a frontend speech service.",
            ],
        }

    def _build_text(self, script_type: str, evidence: dict[str, Any]) -> str:
        concept = self._concept_name(evidence)
        view = self._label(evidence.get("teaching_view"), "current view")
        difficulty = self._label(evidence.get("difficulty"), "current level")
        learner_level = self._label(evidence.get("learner_level"), "your level")
        mistake_type = self._label(evidence.get("mistake_type"), "this mistake")
        weakest_skill = self._label(evidence.get("weakest_skill"), "the main skill")
        evaluation_label = self._label(evidence.get("evaluation_label"), "needs practice")
        doubt_intent = self._label(evidence.get("doubt_intent"), "your doubt")
        next_action = self._label(evidence.get("next_action"), "try one short practice question")
        key_points = self._list(evidence.get("key_points"))
        example = self._sentence(evidence.get("example"))

        main_point = key_points[0] if key_points else f"{concept} is the key idea for this step."
        second_point = key_points[1] if len(key_points) > 1 else "Use the rule once, then test it with a small example."

        if script_type == "teaching_explanation":
            parts = [
                f"Let's learn {concept} using the {view}.",
                f"At {difficulty}, focus on this: {main_point}",
            ]
            if example:
                parts.append(f"For example, {example}")
            parts.append(f"Quick check: can you say the main rule of {concept} in one sentence?")
            return " ".join(parts)

        if script_type == "revision_summary":
            return (
                f"Here is a quick revision of {concept}. Remember: {main_point} "
                f"Also keep this in mind: {second_point} "
                f"Check yourself: what is one place where you would use {concept}?"
            )

        if script_type == "mistake_feedback":
            return (
                f"Your answer is marked as {evaluation_label}. The main issue looks like {mistake_type}. "
                f"Go back to {weakest_skill} and use the rule for {concept} slowly. "
                "Small check: which part of your answer should change first?"
            )

        if script_type == "doubt_explanation":
            parts = [
                f"Your doubt is about {doubt_intent}.",
                f"For {concept}, start from this idea: {main_point}",
            ]
            if example:
                parts.append(f"Use this example as an anchor: {example}")
            parts.append("Does that explain the confusion, or should we try one more example?")
            return " ".join(parts)

        if script_type == "encouragement":
            return (
                f"You are working at {learner_level}, and {concept} can take a few tries. "
                f"Stay with the core idea: {main_point} "
                "One careful attempt is enough for the next step."
            )

        return (
            f"Next, focus on {concept}. Your next action is: {next_action}. "
            f"Before moving on, repeat the rule: {main_point} "
            "Then try the next question."
        )

    def _concept_name(self, evidence: dict[str, Any]) -> str:
        return self._sentence(evidence.get("concept_name")) or "Current concept"

    def _label(self, value: Any, fallback: str) -> str:
        text = self._sentence(value)
        return text.replace("_", " ") if text else fallback

    def _sentence(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" -")
        return text

    def _list(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._sentence(item) for item in value if self._sentence(item)]
        if isinstance(value, str):
            if "|" in value:
                return [self._sentence(item) for item in value.split("|") if self._sentence(item)]
            if "\n" in value:
                return [self._sentence(item) for item in value.splitlines() if self._sentence(item)]
            return [self._sentence(value)] if self._sentence(value) else []
        return [self._sentence(value)] if self._sentence(value) else []

    def _clean_for_tts(self, text: str) -> str:
        text = re.sub(r"[`*_#>]+", "", str(text or ""))
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _estimate_duration_sec(self, text: str) -> int:
        word_count = len(str(text or "").split())
        if word_count == 0:
            return 0
        return max(3, round(word_count / 2.4))


def generate_voice_script(
    script_type: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return VoiceScriptGenerator().generate(script_type=script_type, evidence=evidence)


def generate_voice_script_bundle(evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return VoiceScriptGenerator().generate_bundle(evidence=evidence)
