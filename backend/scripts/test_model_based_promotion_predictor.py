from tutor.progression.model_based_promotion_predictor import (
    ModelBasedPromotionPredictor,
)


def main():
    predictor = ModelBasedPromotionPredictor(comparison_only=True)

    strong_case = {
        "mastery": 0.91,
        "evaluation_score": 0.88,
        "structured_score": 0.86,
        "debug_score": 0.85,
        "output_prediction_score": 0.84,
        "explanation_score": 0.87,
        "transfer_score": 0.82,
        "behaviour_score": 0.89,
        "wrong_rate": 0.08,
        "low_confidence_rate": 0.10,
        "view_reward": 0.84,
        "forgetting_priority": 0.15,
        "guess_probability": 0.08,
    }

    weak_case = {
        "mastery": 0.38,
        "evaluation_score": 0.42,
        "structured_score": 0.35,
        "debug_score": 0.31,
        "output_prediction_score": 0.34,
        "explanation_score": 0.40,
        "transfer_score": 0.28,
        "behaviour_score": 0.45,
        "wrong_rate": 0.62,
        "low_confidence_rate": 0.70,
        "view_reward": 0.25,
        "forgetting_priority": 0.75,
        "guess_probability": 0.55,
    }

    medium_case = {
        "mastery": 0.68,
        "evaluation_score": 0.66,
        "structured_score": 0.63,
        "debug_score": 0.61,
        "output_prediction_score": 0.64,
        "explanation_score": 0.67,
        "transfer_score": 0.58,
        "behaviour_score": 0.69,
        "wrong_rate": 0.28,
        "low_confidence_rate": 0.32,
        "view_reward": 0.60,
        "forgetting_priority": 0.38,
        "guess_probability": 0.22,
    }

    cases = {
        "strong_case": strong_case,
        "medium_case": medium_case,
        "weak_case": weak_case,
    }

    print("\nMODEL-BASED PROMOTION PREDICTOR TEST")

    for name, evidence in cases.items():
        output = predictor.predict(evidence)

        print("\nCASE:", name)
        print("status:", output.get("status"))
        print("module:", output.get("module"))
        print("comparison_only:", output.get("comparison_only"))
        print("model_promotion_allowed:", output.get("model_promotion_allowed"))
        print(
            "model_promotion_allowed_confidence:",
            round(output.get("model_promotion_allowed_confidence", 0.0), 4),
        )
        print("model_progression_action:", output.get("model_progression_action"))
        print(
            "model_progression_action_confidence:",
            round(output.get("model_progression_action_confidence", 0.0), 4),
        )

    print("\nSTATUS: success")
    print("MODULE: ModelBasedPromotionPredictor")
    print("MODE: comparison_only_not_overriding_baseline")


if __name__ == "__main__":
    main()