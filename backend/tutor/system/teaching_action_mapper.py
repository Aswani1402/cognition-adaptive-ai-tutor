from __future__ import annotations

from typing import Dict, Any


class TeachingActionMapper:
    def map_action(self, orchestrator_output: Dict[str, Any]) -> Dict[str, Any]:
        action = orchestrator_output.get("final_action", "reinforce_current")

        if action == "advance":
            return {
                "action": action,
                "strategy": "advanced",
                "content_type": "challenge_problem",
                "difficulty": "medium",
            }

        if action == "reinforce_current":
            return {
                "action": action,
                "strategy": "practice",
                "content_type": "guided_practice",
                "difficulty": "medium",
            }

        if action == "review_current":
            return {
                "action": action,
                "strategy": "remedial",
                "content_type": "worked_example",
                "difficulty": "easy",
            }

        if action == "schedule_review":
            return {
                "action": action,
                "strategy": "revision",
                "content_type": "flashcard",
                "difficulty": "easy",
            }

        return {
            "action": action,
            "strategy": "practice",
            "content_type": "guided_practice",
            "difficulty": "medium",
        }


def map_teaching_action(orchestrator_output: Dict[str, Any]) -> Dict[str, Any]:
    mapper = TeachingActionMapper()
    return mapper.map_action(orchestrator_output)


if __name__ == "__main__":
    import json
    import argparse
    from tutor.system.orchestrator import run_orchestrator

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    orchestrator_output = run_orchestrator(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id) if args.concept_id else None,
    )

    teaching_action = map_teaching_action(orchestrator_output)

    print(json.dumps({
        "orchestrator": orchestrator_output,
        "teaching_action": teaching_action
    }, indent=2))