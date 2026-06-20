from tutor.system.concept_name_resolver import resolve_concept_name, resolve_concept_identity


def main():
    test_ids = ["1", "2", "3", "P1", "S2", "H1", "G1", "D1", "999"]

    print("\nCONCEPT NAME RESOLVER TEST")

    for concept_id in test_ids:
        name = resolve_concept_name(concept_id)
        identity = resolve_concept_identity(concept_id)

        print(
            {
                "concept_id": concept_id,
                "name": name,
                "identity": identity,
            }
        )

    assert resolve_concept_name("1") == "Variables"
    assert resolve_concept_name("2") == "Data Types"
    assert resolve_concept_name("3") == "Conditionals"

    print("\nSTATUS: success")
    print("MODULE: concept_name_resolver")


if __name__ == "__main__":
    main()