from tutor.RL.bandit_policy import BanditPolicy


def test_state(name, state):
    policy = BanditPolicy()
    output = policy.predict(state)

    print("\n---")
    print("TEST:", name)
    print("STATE:", state)
    print("OUTPUT:", output)


def main():
    test_state(
        "strong",
        {
            "mastery_score": 0.6,
            "behavior_score": 0.6,
            "review_due": True,
            "evaluation_score": 0.9,
            "learning_signal": "mastered",
        },
    )

    test_state(
        "average",
        {
            "mastery_score": 0.6,
            "behavior_score": 0.6,
            "review_due": True,
            "evaluation_score": 0.7,
            "learning_signal": "partial",
        },
    )

    test_state(
        "weak",
        {
            "mastery_score": 0.6,
            "behavior_score": 0.6,
            "review_due": True,
            "evaluation_score": 0.2,
            "learning_signal": "weak",
        },
    )


if __name__ == "__main__":
    main()