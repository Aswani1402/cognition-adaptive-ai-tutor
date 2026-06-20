# Behaviour Annotation CSV Schema

Files:

- **`evaluation_outputs/csv/behaviour_annotation_dataset.csv`** — main export; **human** columns start blank for real annotation work.
- **`evaluation_outputs/csv/behaviour_annotation_sample_labelled.csv`** — **demo layout only**; `human_*` fields are placeholders copied from proxy labels with `annotator_id=DEMO_EXPORT` and a watermark in `annotation_notes`. **Not** real human labels.

All columns below appear in both files unless noted.

## Identity and context

| Column | Type | Description |
|--------|------|-------------|
| `annotation_id` | string | Stable row identifier (hash-based) for referencing in reports and merges. |
| `learner_id` | string | Internal learner identifier from `tutor.db`. |
| `concept_id` | string | Concept identifier when available (e.g., from `fusion_decision_log` or `learner_session_log`). |
| `concept_name` | string | Human-readable concept name when available. |
| `domain` | string | Course/domain string when available. |
| `timestamp` | string / ISO | Time associated with the behaviour snapshot (often `behaviour_state.timestamp`). |

## Behaviour evidence (numeric / rates)

| Column | Type | Description |
|--------|------|-------------|
| `recent_score` | float 0–1 | Latest quiz correctness signal (1 = correct) aggregated for the learner near the snapshot. |
| `correctness_rate` | float 0–1 | Mean correctness over recent attempts in export window. |
| `wrong_rate` | float 0–1 | From `behaviour_state.wrong_rate` when present; else derived from quiz window. |
| `slow_rate` | float 0–1 | Fraction of slow responses when column exists. |
| `low_confidence_rate` | float 0–1 | Fraction of low-confidence events when column exists. |
| `hint_rate` | float 0–1 | Hint usage rate when column exists. |
| `option_change_rate` | float 0–1 | Option-change rate when column exists. |
| `time_taken_avg` | float | Average time per attempt (seconds) from recent quiz rows when available. |
| `confidence_avg` | float | Average confidence (scaled roughly 0–5 in export for readability). |
| `wrong_streak` | float | Consecutive incorrect attempts at end of recent window. |
| `attempt_count` | float | Count of recent attempts used for aggregates. |
| `behaviour_risk` | float 0–1 | Model or heuristic risk when `behaviour_state` exposes it. |
| `behaviour_confidence` | float 0–1 | Confidence associated with behaviour estimate when present. |
| `anomaly_score` | float 0–1 | Optional anomaly signal (e.g., from `view_performance_log`); **0** if unavailable. |

## Mistake / evaluation evidence

| Column | Type | Description |
|--------|------|-------------|
| `dominant_mistake_type` | string | Most frequent `mistake_type` for the learner in `learner_mistake_log`. |
| `mistake_count` | float | Total mistake rows aggregated. |
| `wrong_output_count` | float | Count of mistakes classified as wrong-output-like. |
| `syntax_mistake_count` | float | Count with syntax-related `mistake_type`. |
| `debug_error_count` | float | Count with debug-related `mistake_type`. |
| `output_prediction_error_count` | float | Count with output-prediction-related `mistake_type`. |

## Proxy labels (system)

| Column | Type | Description |
|--------|------|-------------|
| `proxy_behaviour_label` | string | Proxy label (pattern scores and/or `behaviour_state` label column). |
| `proxy_label_source` | string | e.g. `pattern_scores_derived`, `behaviour_state_column`, `synthetic_demo_row` (sample only). |
| `proxy_label_confidence` | float 0–1 | Internal confidence for proxy label. |

## Human annotation (to be filled by annotators)

| Column | Type | Description |
|--------|------|-------------|
| `human_behaviour_label` | string | One of: `stable`, `confused`, `struggling`, `guessing`, `careless`, `low_confidence`, `disengaged`, `anomalous`, `unclear`. |
| `human_confidence` | int 1–5 | Annotator confidence in the chosen label. |
| `annotator_id` | string | Short ID for the annotator (never use `DEMO_EXPORT` for real work). |
| `annotation_notes` | string | Free-text evidence; include resolution text for disagreements. |
| `needs_review` | `yes` / `no` | Flag for borderline rows. |

## Optional extension (two raters)

| Column | Type | Description |
|--------|------|-------------|
| `human_behaviour_label_2` | string | Optional second annotator label for the same row; enables Cohen’s kappa in the checker when present. |

If you add columns, update this document and the `REQUIRED_COLUMNS` list in `scripts/evaluation/check_behaviour_human_label_report.py` only if they become mandatory for validation.
