from tutor.behaviour.lstm_behaviour_model import run_behaviour_model

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    args = parser.parse_args()

    output = run_behaviour_model(str(args.learner_id))
    print(json.dumps(output, indent=2))