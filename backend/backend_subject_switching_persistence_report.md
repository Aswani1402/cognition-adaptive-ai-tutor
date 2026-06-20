# Backend Subject Switching Persistence Report

## Status

Passed.

## What Changed

- `POST /learner/select-subject` now saves `active_subject` and restores subject-specific state instead of always resetting to the first concept.
- Before switching subjects, the current subject pointer is snapshotted into `concept_unlock_state.evidence_json` with its `current_difficulty`.
- When switching back to a subject, the route restores from existing `learner_concept_progress`, `concept_unlock_state`, and `knowledge_state` where available.
- First-time subject selection initializes the first concept with `current_difficulty=easy`, a `current` progress row, and a subject/concept-specific unlock row.
- Existing mastery and unlock state are preserved with max-mastery updates rather than reset to `0.0`.
- `knowledge_state.state_json` now preserves a subject-aware map:
  - `subjects[subject].current_concept_id`
  - `subjects[subject].current_difficulty`
  - `subjects[subject].concepts[concept_id].mastery`
- `GET /learner/context/{learner_id}` now returns top-level:
  - `active_subject`
  - `current_concept_id`
  - `current_concept_name`
  - `current_difficulty`
  - `current_teaching_view`
  - `subject_progress`

## Files Updated

- `tutor/api/learner_routes.py`
- `tutor/api/evaluation_routes.py`
- `scripts/test_subject_switching_persistence.py`

## Regression Covered

The new script verifies:

- Select Python.
- Submit a correct Python answer so progress/mastery is saved.
- Switch to SQL / Database.
- Switch back to Python.
- Confirm Python concept, difficulty, mastery, unlock state, and KT subject map remain preserved.
- Confirm SQL unlock state remains initialized and is not deleted.
- Confirm learner context returns the restored active subject and current concept fields.

## Verification

Commands run:

```powershell
python -m py_compile tutor\api\learner_routes.py tutor\api\evaluation_routes.py scripts\test_subject_switching_persistence.py
$env:PYTHONPATH='.'; python scripts\test_subject_switching_persistence.py
$env:PYTHONPATH='.'; python scripts\test_first_time_returning_learner_flow.py
$env:PYTHONPATH='.'; python scripts\test_subject_context_flow.py
$env:PYTHONPATH='.'; python scripts\test_user_db_persistence_flow.py
$env:PYTHONPATH='.'; python scripts\test_api_routes_smoke.py
$env:PYTHONPATH='.'; python scripts\test_subject_consistency_all_routes.py
```

Results:

- `subject switching persistence test success`
- `first-time returning learner flow test success`
- `subject context flow ok`
- `user db persistence flow ok`
- `api_routes_smoke_test` completed with `STATUS: success`
- `subject consistency all routes test success`

Note: API smoke emitted TensorFlow and sklearn model-version warnings during model loading, but the route smoke test completed successfully.
