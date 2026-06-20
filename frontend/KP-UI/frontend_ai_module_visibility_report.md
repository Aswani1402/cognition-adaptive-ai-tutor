# Frontend AI Module Visibility Report

## Summary
- Added AI evidence visibility through `AIEvidencePanel` and module cards.
- XAI and Demo pages now show reviewer-facing KT, Behaviour, RAG, Teaching Strategy, Policy/RL, LLM generation, Agentic orchestration, Personalization, Retention, Evaluation/Fusion, and Reward evidence.
- Learner-facing flow remains guided; modules are surfaced as explanation/evidence, not manual controls.

## Module Status
- KT card: visible in reviewer evidence.
- Behaviour card: visible with wrong/slow/confidence/hint/option/answer/run-code signal fields.
- Concept dependency/adaptive path: visible.
- Teaching strategy: visible with selected view, difficulty, fallback views, and assessment types.
- Policy/RL: visible as safe decision and offline comparison status.
- RAG: visible with source sections and grounding status.
- LLM generation coverage: visible in Demo page; voice-ready scripts are labelled as text scripts, not TTS.
- Agentic trace: labelled honestly as orchestration trace.
- Long-term personalization: visible with weak concepts, past mistakes/doubts, revision queue.
- Retention/forgetting: visible with risk/review fields.
- Evaluation/fusion: visible with fused score/label/weakest skill.
- Reward: visible with XP/streak/unlock fields.

## Learner-Facing vs Reviewer-Facing
- Learner-facing: short "Why this next step?" explanation in `AIEvidencePanel` learner mode.
- Reviewer-facing: full cards on XAI and Demo pages.

## Remaining Limitations
- Some cards depend on backend fallback packets when model logs are unavailable.
- Sanvia remains comparison-only and is not connected to live runtime.

## Build/Test Results
- `npm run build`: passed.
- `npm run lint`: passed.
- Backend `python -m scripts.test_api_routes_smoke`: passed.
- Backend `python -m scripts.test_frontend_response_builder`: passed.
