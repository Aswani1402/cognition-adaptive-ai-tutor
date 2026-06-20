from tutor.RL.dqn.dqn_policy import DQNPolicy


def test_state(name, state):
    policy = DQNPolicy()
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