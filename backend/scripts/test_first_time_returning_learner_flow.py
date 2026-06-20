from __future__ import annotations

from scripts.production_readiness_checks import register_login_select, unwrap


def main() -> None:
    setup = register_login_select("SQL / Database")
    learner_id = setup["learner_id"]
    client = setup["client"]
    context = client.get(f"/learner/context/{learner_id}")
    assert context.status_code == 200, context.text
    payload = unwrap(context.json())
    profile = payload.get("learner_profile") or {}
    assert profile.get("active_subject") == "SQL / Database", payload
    assert profile.get("current_concept_id") == setup["concept_id"], payload
    assert payload.get("current_activity", {}).get("type") in {"teaching", "returning_revision"}, payload
    assert payload.get("next_recommended_activity"), payload
    print("first-time returning learner flow test success")


if __name__ == "__main__":
    main()
