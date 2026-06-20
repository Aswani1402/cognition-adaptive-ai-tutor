from tutor.system.teaching_content_connector import run_teaching_content_connector


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=True)
    args = parser.parse_args()

    output = run_teaching_content_connector(
        learner_id=str(args.learner_id),
        concept_id=str(args.concept_id),
    )
    print(json.dumps(output, indent=2))