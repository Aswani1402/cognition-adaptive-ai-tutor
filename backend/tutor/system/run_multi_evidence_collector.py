from tutor.system.multi_evidence_collector import collect_multi_evidence


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--learner_id", required=True)
    parser.add_argument("--concept_id", required=False, default=None)
    args = parser.parse_args()

    output = collect_multi_evidence(
        learner_id=str(args.learner_id),
        system_concept_id=str(args.concept_id) if args.concept_id else None,
    )

    print(json.dumps(output, indent=2))