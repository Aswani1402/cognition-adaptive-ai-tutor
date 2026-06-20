# db_changes/test_system_content_fetch.py

from tutor.utils.fetch_learning_content import get_learning_content

def main():
    system_concept_id = "1"   # P1

    data = get_learning_content(system_concept_id)

    if data:
        print("SUCCESS\n")
        print("Concept:", data["concept_id"])
        print("Topic:", data["topic"])
        print("Base preview:", data["base_content"][:200])
    else:
        print("FAILED")

if __name__ == "__main__":
    main()