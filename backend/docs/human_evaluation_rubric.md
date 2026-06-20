# Human Evaluation Rubric (CogniTutor)

## 1. Purpose

Automatic reports (RAG grounding scores, semantic benchmarks, hint policy metrics, etc.) measure **system behaviour**, not **pedagogical quality** as humans experience it. This rubric supports **human-rated evaluation** of concrete artifacts: teaching text, grounded answers, doubt replies, hints, assessments, flashcards, mindmaps, and feedback—using consistent dimensions so results can be compared across categories and over time.

## 2. Categories rated

| Category | What evaluators judge |
|----------|----------------------|
| **teaching_explanation** | Lesson-style explanation of a concept. |
| **rag_grounded_answer** | Answer that should cite or align with retrieved context. |
| **doubt_answer** | Response to a learner “doubt” or follow-up question. |
| **semantic_evaluator_judgement** | Model or rubric judgement text about learner work quality. |
| **adaptive_hint** | Hint text shown after a wrong or weak attempt. |
| **generated_flashcard** | Front/back or Q/A flashcard content. |
| **generated_mindmap** | Structured outline / node summaries. |
| **assessment_question** | Question stem, expected answer, and clarity of task. |
| **feedback_response** | Corrective or reinforcing feedback after submission. |

## 3. Rating dimensions (each 1–5)

| Dimension | Question the rater answers |
|-----------|----------------------------|
| **correctness** | Is the content factually and technically correct for the stated level? |
| **clarity** | Is wording precise, unambiguous, and easy to parse? |
| **helpfulness** | Would this move a typical learner toward understanding or success? |
| **grounding** | For RAG or evidence-backed items: does the output stay faithful to sources and avoid invention? For non-RAG items: is justification consistent with the prompt? |
| **learner_suitability** | Is difficulty, tone, and cognitive load appropriate for the intended audience? |
| **actionability** | Does the learner know what to do next (steps, fix, or study move)? |

**overall_score** (1–5, may be a rounded mean of the six dimensions in the sheet) captures a holistic judgement.

**rater_confidence** (1–5): how sure you are in your own ratings for this row (not quality of the system).

## 4. Scale definitions (1–5)

| Score | Meaning |
|------|---------|
| 1 | **Poor** — incorrect, misleading, or harmful; should not ship. |
| 2 | **Weak** — partially useful but has clear gaps or risks. |
| 3 | **Acceptable** — usable with minor fixes; average classroom bar. |
| 4 | **Good** — clear, accurate, and helpful; minor polish only. |
| 5 | **Excellent** — exemplar quality for the level; nothing material missing. |

## 5. Examples of strong vs weak outputs (illustrative)

- **Strong teaching explanation:** defines the idea, gives a minimal example, states a common pitfall, uses level-appropriate vocabulary.  
- **Weak:** circular definition, jargon with no example, or factual error.

- **Strong RAG answer:** ties claims to provided snippets; says when information is insufficient.  
- **Weak:** adds unstated facts, contradicts the context, or ignores the passage.

- **Strong hint:** nudges reasoning without giving away the full solution.  
- **Weak:** repeats the question, or reveals the exact answer with no scaffolding.

## 6. How to rate **grounding**

- **5:** Every substantive claim maps to the supplied context (or general knowledge where RAG is N/A and category allows).  
- **3:** Mostly grounded; small unsupported generalizations.  
- **1:** Fabrication, contradiction, or “hallucinated” detail relative to sources.

If **source_or_grounding** is empty, rate grounding on **internal consistency** with the prompt only, and lower confidence if evidence is thin.

## 7. How to rate **learner_suitability**

Consider reading level, prerequisite assumptions, length, and cognitive load. Penalize content that assumes knowledge the prompt says learners lack, or that uses intimidating tone for novices.

## 8. How to mark **needs_revision**

Set **yes** when any dimension would be ≤2, or when grounding/safety is questionable—even if other dimensions are high. Use **no** when the row is at least acceptable on all critical dimensions.

## 9. Multiple raters

- Each rater uses a distinct **rater_id**.  
- Rate **blind** to automatic scores when possible (hide `automatic_score_if_available` in a copy of the sheet).  
- Disagreements: third rater or discussion lead; record resolution in **human_notes**.

## 10. Honesty rule

Unless the main `human_evaluation_items.csv` is filled by **real evaluators** (not `DEMO_RATER` and not `SAMPLE_RATINGS_ONLY` notes), project reports must **not** claim a completed large-scale human study—only that the **workflow and instruments** exist.
