# Human Evaluation Protocol (CogniTutor)

## 1. Who can rate

- **Subject-matter experts** (instructors, TAs) for correctness and learner suitability.  
- **Learning designers** or experienced tutors for clarity, helpfulness, and actionability.  
- **Technical reviewers** when outputs involve code execution, SQL, or tool use.

Raters should complete a short **calibration** session (3–5 anchor items) before bulk rating.

## 2. How many items to rate

- **Pilot:** at least **30** items across all categories (minimum **3 per category**).  
- **Study-quality:** target **100+** items, stratified by category and difficulty/domain.  
- Use `item_id` to avoid double-counting merged exports.

## 3. Blind rating (recommended)

- Provide **prompt_or_context** and **system_output** without showing model name or internal run ID.  
- Hide **automatic_score_if_available** in a “blind” copy column or separate tab until ratings are locked.  
- After ratings are final, merge automatic scores for **post-hoc** comparison only.

## 4. Avoiding bias

- Do **not** change ratings after seeing automatic scores unless performing a documented **adjudication** pass.  
- Avoid ordering effects: shuffle `item_id` order per rater.  
- Take breaks; long sessions correlate with score drift.

## 5. Computing average scores

- Per dimension: mean of integer ratings (1–5) across rated rows.  
- **overall_score** in the sheet may be rater-supplied holistic score **or** mean of the six dimensions—pick one convention per study and document it in `human_notes` header row or README.  
- Report **95% CI** or standard error only when **n** is large enough (rule of thumb: **n ≥ 30** per subgroup).

## 6. Comparing automatic vs human scores

- Join on `item_id` (or stable hash of prompt+output).  
- Report **Pearson / Spearman** correlation and **Bland–Altman**-style bias (mean human minus mean automatic) if automatic scores are on a comparable 1–5 scale; otherwise use **quadratic weighted kappa** after mapping both to ordinal bins.  
- Do **not** treat disagreement as “human wrong”—use it to diagnose metric blind spots.

## 7. Limitations

- Human ratings are **subjective** and **context-dependent**; small **n** per category limits generalization.  
- **Proxy items** extracted from JSON reports may not match production UI wording.  
- **Sample-rated CSV** in this repository contains **placeholder** scores for demo layout only (`sample_ratings_only=true`); it is **not** evidence of a completed study.  
- Full **large-scale** human evaluation remains **future work** until real raters complete `human_evaluation_items.csv`.

## 8. Artifacts

- **Items sheet:** `evaluation_outputs/csv/human_evaluation_items.csv`  
- **Demo sheet:** `evaluation_outputs/csv/human_evaluation_sample_rated.csv`  
- **Rubric:** `docs/human_evaluation_rubric.md`  
- **Automation:** `scripts/data/export_human_evaluation_items.py`, `scripts/evaluation/check_human_evaluation_report.py`, `scripts/evaluation/generate_human_evaluation_charts.py`
