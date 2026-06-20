from tutor.api.concept_content_resolver import build_voice_scripts, resolve_concept_content


def main():
    scripts = build_voice_scripts(resolve_concept_content("Python", "P1"))
    required = {
        "voice_script",
        "teaching_voice_script",
        "revision_voice_script",
        "mistake_feedback_voice_script",
        "doubt_explanation_voice_script",
        "encouragement_script",
        "next_step_guidance_script",
        "concept_intro_voice_script",
    }
    assert required.issubset(scripts)
    print("voice script mascot coverage ok")


if __name__ == "__main__":
    main()
