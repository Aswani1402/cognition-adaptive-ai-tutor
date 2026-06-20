# Behaviour Human Labelling Guide (CogniTutor)

## 1. Purpose

This guide supports **human validation** of behaviour-related signals in CogniTutor. The adaptive tutor already uses **proxy / model-derived behaviour labels** (for example from session aggregates, risk scores, clustering, and anomaly detection). Those labels are **not** a substitute for adjudicated human judgement.

Annotators use the exported CSV (`evaluation_outputs/csv/behaviour_annotation_dataset.csv`) to assign **human_behaviour_label** values and optional notes. Results feed future **agreement studies**, calibration of proxy labels, and stronger supervised behaviour models—**without replacing** the current production behaviour pipeline until a study is complete.

## 2. What annotators should look at

For each row (one **annotation_id**), review:

- **Performance context:** `recent_score`, `correctness_rate`, `wrong_streak`, `attempt_count`.
- **Interaction style:** `wrong_rate`, `slow_rate`, `low_confidence_rate`, `hint_rate`, `option_change_rate`, `time_taken_avg`, `confidence_avg`.
- **Risk / model side signals (advisory only):** `behaviour_risk`, `behaviour_confidence`, `anomaly_score` (when present).
- **Mistake patterns:** `dominant_mistake_type`, per-type counts (`wrong_output_count`, `syntax_mistake_count`, etc.).
- **Proxy suggestion (do not copy blindly):** `proxy_behaviour_label`, `proxy_label_source`, `proxy_label_confidence`.

Use **learner_id**, **concept_id / concept_name / domain**, and **timestamp** only for traceability; do not infer identity beyond what is needed for labelling.

## 3. Label definitions

### stable

Learner performs consistently with reasonable confidence and low mistakes.

### confused

Learner shows mixed performance, repeated uncertainty, or inconsistent answers relative to the evidence window.

### struggling

Learner has repeated low scores, high mistakes, or evidence suggesting remediation is needed.

### guessing

Learner answers very fast, changes options often, shows low confidence or unstable correctness.

### careless

Learner seems to know the concept but makes simple, avoidable mistakes (e.g., slip-ups despite generally strong signals).

### low_confidence

Learner may answer correctly or partially but confidence remains low across the evidence.

### disengaged

Learner is slow, inactive, uses little effort, or shows repeated incomplete attempts.

### anomalous

Unusual behaviour pattern detected (e.g., abnormal timing, sudden failure spike, or strong anomaly score with inconsistent history).

### unclear

Not enough evidence in the row to label confidently—use **needs_review=yes** when in doubt.

## 4. Short examples (illustrative)

| Pattern | Suggested label |
|--------|-----------------|
| High correctness, moderate confidence, low hints | **stable** |
| Correct and incorrect attempts alternating, mid confidence | **confused** |
| Sustained low correctness, rising wrong streak | **struggling** |
| Very fast attempts, high option changes, low confidence | **guessing** |
| Mostly correct but repeated silly mistakes | **careless** |
| Correct answers but confidence stays very low | **low_confidence** |
| Very long times, few completed items, flat performance | **disengaged** |
| Spike in anomaly score with rare timing pattern | **anomalous** |
| Sparse or contradictory fields | **unclear** |

## 5. Annotation rules

1. **One primary label** per row in `human_behaviour_label` (allowed vocabulary only).
2. Prefer **unclear** over forcing a label when evidence is thin.
3. **Do not** treat `proxy_behaviour_label` as ground truth; treat it as a **hint** for discussion only.
4. If `anomaly_score` is missing or zero, do not infer **anomalous** from risk alone unless the rest of the row supports it.
5. Keep **annotation_notes** factual (what you observed), not learner-identifying gossip.

## 6. How to set `human_confidence` (1–5)

| Score | Meaning |
|------|---------|
| 1 | Very uncertain |
| 2 | Weak evidence |
| 3 | Moderate |
| 4 | Strong evidence |
| 5 | Very clear-cut |

## 7. When to set `needs_review=yes`

- Borderline between two labels.
- Missing key fields (e.g., no attempts but non-zero rates).
- Conflicting signals (e.g., high correctness but very high anomaly).
- Any ethical or ambiguity concern.

## 8. Two annotators and disagreements

1. Each annotator fills **human_behaviour_label** and **human_confidence** independently (use separate sheets or duplicate rows with different **annotator_id** values).
2. Compute agreement offline (see `behaviour_human_label_report.json` when the pipeline is run with merged labels).
3. **Resolve disagreements** by:
   - Joint review of the row and notes;
   - A **senior annotator** decision recorded in `annotation_notes` (e.g., `resolution: agreed_on_struggling`);
   - If still ambiguous, keep **unclear** and **needs_review=yes**.

Optional second column **human_behaviour_label_2** may be added in a fork of the CSV for dyad studies; document any schema extension in `behaviour_annotation_schema.md`.

## 9. Ethics and privacy

- Treat rows as **sensitive learner data**; store annotated files securely.
- Do not share raw exports in public repositories without policy approval.

## 10. What “done” means today

A **human-labelling workflow** and **annotation-ready export** are in place. **Full-scale human annotation** remains **future work** until real annotators complete the sheet and the project ingests merged labels.
