from tutor.api.concept_content_resolver import FLASHCARD_TYPES, build_flashcards, build_mindmap


def main():
    cards = build_flashcards("Python", "P1")
    card_types = {card["card_type"] for card in cards["flashcards"]}
    assert set(FLASHCARD_TYPES).issubset(card_types)
    mindmap = build_mindmap("Python", "P1")
    assert len(mindmap["nodes"]) >= 5
    assert "comparison_mindmap" in mindmap["mindmap_variants"]
    print("flashcard and mindmap type coverage ok")


if __name__ == "__main__":
    main()
