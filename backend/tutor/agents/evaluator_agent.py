from __future__ import annotations

from typing import Any, Dict

from tutor.evaluation.assessment_bundle_evaluator import evaluate_assessment_bundle
from tutor.evaluation.mistake_type_classifier import classify_mistakes_for_evaluation
from tutor.evaluation.rubric_evaluator import evaluate_answers_with_rubric
from tutor.evaluation.debug_answer_evaluator import evaluate_debug_answers_from_assessment
from tutor.evaluation.output_prediction_evaluator import evaluate_output_predictions_from_assessment
from tutor.evaluation.evaluation_fusion_engine import fuse_evaluation_outputs


class EvaluatorAgent:
    def convert_assessment_for_evaluator(self, assessment_bundle: Dict[str, Any]) -> Dict[str, Any]:
        mapping = {
            "mcq": "mcq",
            "short_explanation": "explanation",
            "output_prediction": "output_prediction",
            "debug": "debug",
            "transfer": "transfer",
        }

        converted_questions = []
        for q in assessment_bundle.get("questions", []):
            converted_questions.append({
                "assessment_type": mapping.get(q.get("question_type"), q.get("question_type")),
                "question": q.get("prompt"),
                "prompt": q.get("prompt"),
                "expected_answer": q.get("expected_answer"),
                "options": q.get("options"),
                "correct_option_index": q.get("correct_option_index"),
                "metadata": q.get("metadata", {}),
            })

        return {
            "status": assessment_bundle.get("status", "success"),
            "concept_id": assessment_bundle.get("concept_id", ""),
            "concept_name": assessment_bundle.get("concept_name", ""),
            "difficulty": assessment_bundle.get("difficulty", ""),
            "questions": converted_questions,
            "assessment_items": converted_questions,
        }

    def derive_learning_signal(self, evaluation_output: Dict[str, Any]) -> str:
        score = float(evaluation_output.get("overall_score", 0.0))
        if score >= 0.8:
            return "mastered"
        if score >= 0.5:
            return "partial"
        return "weak"

    def build_evaluation_evidence(
        self,
        evaluation_output: Dict[str, Any],
        learning_signal: str,
    ) -> Dict[str, Any]:
        results = evaluation_output.get("results", [])
        weak_item_count = len(
            [r for r in results if float(r.get("score", 0.0)) < 0.75]
        )

        return {
            "overall_score": evaluation_output.get("overall_score", 0.0),
            "verdict": evaluation_output.get("verdict", ""),
            "feedback_summary": evaluation_output.get("feedback_summary", ""),
            "learning_signal": learning_signal,
            "weak_item_count": weak_item_count,
            "item_count": len(results),
        }

    def run(
        self,
        assessment_bundle: Dict[str, Any],
        learner_answers: Dict[str, str],
    ) -> Dict[str, Any]:


        converted_bundle = self.convert_assessment_for_evaluator(assessment_bundle)
        evaluation_output = evaluate_assessment_bundle(
            assessment_bundle=converted_bundle,
            learner_answers=learner_answers,
        )

        try:
            rubric_evaluation_output = evaluate_answers_with_rubric(
                assessment_output=assessment_bundle,
                learner_answers=learner_answers,
            )
        except Exception as e:
            rubric_evaluation_output = {
                "status": "error",
                "module": "RubricEvaluator",
                "reason": str(e),
            }

        try:
            debug_evaluation_output = evaluate_debug_answers_from_assessment(
                assessment_output=assessment_bundle,
                learner_answers=learner_answers,
            )
        except Exception as e:
            debug_evaluation_output = {
                "status": "error",
                "module": "DebugAnswerEvaluator",
                "reason": str(e),
            }

        debug_evaluation_mode = "comparison_only_not_replacing_final_evaluation"

        try:
            output_prediction_evaluation_output = evaluate_output_predictions_from_assessment(
                assessment_output=assessment_bundle,
                learner_answers=learner_answers,
            )
        except Exception as e:
            output_prediction_evaluation_output = {
                "status": "error",
                "module": "OutputPredictionEvaluator",
                "reason": str(e),
            }

        output_prediction_evaluation_mode = "comparison_only_not_replacing_final_evaluation"

        learning_signal = self.derive_learning_signal(evaluation_output)
        evaluation_evidence = self.build_evaluation_evidence(
            evaluation_output,
            learning_signal,
        )

        try:
            mistake_analysis_output = classify_mistakes_for_evaluation(
                assessment_output=assessment_bundle,
                learner_answers=learner_answers,
                evaluation_output=evaluation_output,
            )
        except Exception as e:
            mistake_analysis_output = {
                "status": "error",
                "module": "MistakeTypeClassifier",
                "reason": str(e),
            }

        try:
            evaluation_fusion_output = fuse_evaluation_outputs(
                baseline_evaluation_output=evaluation_output,
                rubric_evaluation_output=rubric_evaluation_output,
                debug_evaluation_output=debug_evaluation_output,
                output_prediction_evaluation_output=output_prediction_evaluation_output,
                mistake_analysis_output=mistake_analysis_output,
            )
        except Exception as e:
            evaluation_fusion_output = {
                "status": "error",
                "module": "EvaluationFusionEngine",
                "reason": str(e),
            }

        evaluation_fusion_mode = "comparison_only_not_replacing_final_evaluation"

        return {
            "status": "success",
            "agent": "EvaluatorAgent",
            "converted_assessment": converted_bundle,
            "evaluation": evaluation_output,

            "rubric_evaluation_output": rubric_evaluation_output,
            "rubric_mode": "comparison_only_not_replacing_final_evaluation",


            "debug_evaluation_output": debug_evaluation_output,
            "debug_evaluation_mode": debug_evaluation_mode,



            "output_prediction_evaluation_output": output_prediction_evaluation_output,
            "output_prediction_evaluation_mode": output_prediction_evaluation_mode,


            "evaluation_fusion_output": evaluation_fusion_output,
            "evaluation_fusion_mode": evaluation_fusion_mode,

            "learning_signal": learning_signal,
            "evaluation_evidence": evaluation_evidence,
            "mistake_analysis_output": mistake_analysis_output,
        }