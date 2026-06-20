from typing import Any


class ReflectionAgent:
    def reflect(
        self,
        evaluation: dict,
        multi_evidence: dict,
        policy_output: dict,
        mistake_analysis_output: dict | None = None,
    ) -> dict:
        mistake_analysis_output = mistake_analysis_output or {}

        dominant_mistake_type = mistake_analysis_output.get("dominant_mistake_type")
        mistake_type_counts = mistake_analysis_output.get("mistake_type_counts", {})
        high_severity_count = mistake_analysis_output.get("high_severity_count", 0)
        classified_mistakes = mistake_analysis_output.get("classified_mistakes", [])

        results = evaluation.get("results", [])
        weak_types = [
            r.get("assessment_type")
            for r in results
            if isinstance(r, dict) and float(r.get("score", 0) or 0) < 0.6
        ]

        evidence = multi_evidence.get("evidence_summary", {})
        policy = policy_output.get("data", {})

        if "output_prediction" in weak_types and "debug" in weak_types:
            diagnosis = (
                "Learner understands the concept verbally but struggles with "
                "code execution and debugging."
            )
            what_next = "Give short code tracing and debugging practice."
        elif weak_types:
            diagnosis = f"Learner needs review in: {', '.join(weak_types)}."
            what_next = "Give targeted practice for weak question types."
        else:
            diagnosis = "Learner is performing well across assessment types."
            what_next = "Move toward challenge or next concept."

        mistake_focus = []

        for item in classified_mistakes:
            if not isinstance(item, dict):
                continue

            mistake_type = item.get("mistake_type")
            assessment_type = item.get("assessment_type")
            severity = item.get("severity")

            if severity in {"medium", "high"} and mistake_type and assessment_type:
                mistake_focus.append(f"{assessment_type}:{mistake_type}")

        if mistake_focus:
            diagnosis = (
                diagnosis
                + " Specific mistake patterns detected: "
                + ", ".join(mistake_focus[:4])
                + "."
            )

        if high_severity_count and high_severity_count >= 2:
            what_next = (
                "Give focused remediation using the exact mistake pattern before "
                "moving to harder practice."
            )

        if dominant_mistake_type == "low_confidence":
            what_next = (
                "Give confidence-building practice with hints and short checks."
            )

        return {
            "status": "success",
            "agent": "ReflectionAgent",
            "reflection": {
                "diagnosis": diagnosis,
                "weak_assessment_types": weak_types,
                "dominant_mistake_type": dominant_mistake_type,
                "mistake_type_counts": mistake_type_counts,
                "high_severity_mistake_count": high_severity_count,
                "mistake_focus": mistake_focus,
                "mastery_score": evidence.get("mastery_score"),
                "behavior_label": evidence.get("behavior_label"),
                "evaluation_score": evidence.get("evaluation_score"),
                "final_strategy": policy.get("strategy"),
                "final_difficulty": policy.get("difficulty"),
                "what_next": what_next,
                "reason": (
                    f"Policy selected {policy.get('strategy')} at "
                    f"{policy.get('difficulty')} difficulty because evaluation score is "
                    f"{evidence.get('evaluation_score')} and weak areas are {weak_types}. "
                    f"Dominant mistake type is {dominant_mistake_type}; "
                    f"high severity mistake count is {high_severity_count}."
                ),
            },
        }