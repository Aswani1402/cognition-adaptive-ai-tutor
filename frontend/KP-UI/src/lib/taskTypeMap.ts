export type TaskCategory =
  | 'teaching'
  | 'assessment'
  | 'revision'
  | 'flashcards'
  | 'mindmaps'
  | 'feedback'
  | 'hints'
  | 'doubt'
  | 'notebook'
  | 'practice'
  | 'voice_script';

export type TaskTypeMapping = {
  category: TaskCategory;
  renderInside: string[];
  primaryComponent: string;
  learnerFacing: boolean;
};

const guidedTeaching = ['GuidedTutorJourney', 'SelectedTeachingViewRenderer'];
const assessment = ['AssessmentRenderer', 'QuestionCard components', 'CodeConsole where needed'];

export const taskTypeMap: Record<string, TaskTypeMapping> = {
  explanation: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  definition_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  simple_example_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  step_by_step_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  analogy_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  code_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  misconception_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  debug_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  output_prediction_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  transfer_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  challenge_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  revision_summary_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  comparison_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  real_world_connection_view: { category: 'teaching', renderInside: guidedTeaching, primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },

  mcq: { category: 'assessment', renderInside: assessment, primaryComponent: 'MCQQuestionCard', learnerFacing: true },
  debug_task: { category: 'assessment', renderInside: assessment, primaryComponent: 'DebugQuestionCard', learnerFacing: true },
  output_prediction: { category: 'assessment', renderInside: assessment, primaryComponent: 'OutputPredictionCard', learnerFacing: true },
  transfer_question: { category: 'assessment', renderInside: assessment, primaryComponent: 'TransferQuestionCard', learnerFacing: true },
  challenge_question: { category: 'assessment', renderInside: assessment, primaryComponent: 'ChallengeQuestionCard', learnerFacing: true },
  explanation_check: { category: 'assessment', renderInside: assessment, primaryComponent: 'ShortExplanationCard', learnerFacing: true },
  syntax_completion: { category: 'assessment', renderInside: assessment, primaryComponent: 'SyntaxCompletionCard', learnerFacing: true },
  coding_prompt: { category: 'assessment', renderInside: assessment, primaryComponent: 'CodeConsole', learnerFacing: true },
  coding_question: { category: 'assessment', renderInside: assessment, primaryComponent: 'CodeConsole', learnerFacing: true },
  code_reasoning_task: { category: 'assessment', renderInside: assessment, primaryComponent: 'ShortExplanationCard', learnerFacing: true },
  fill_in_the_blank: { category: 'assessment', renderInside: assessment, primaryComponent: 'FillBlankQuestionCard', learnerFacing: true },
  fill_blank: { category: 'assessment', renderInside: assessment, primaryComponent: 'FillBlankQuestionCard', learnerFacing: true },
  true_or_false: { category: 'assessment', renderInside: assessment, primaryComponent: 'MCQQuestionCard', learnerFacing: true },

  revision_note: { category: 'revision', renderInside: ['GuidedTutorJourney', 'NotebookPage'], primaryComponent: 'RevisionSummaryCard', learnerFacing: true },
  revision_summary: { category: 'revision', renderInside: ['GuidedTutorJourney', 'NotebookPage'], primaryComponent: 'RevisionSummaryCard', learnerFacing: true },
  weakness_review: { category: 'revision', renderInside: ['GuidedTutorJourney', 'MistakesPage'], primaryComponent: 'MistakeReviewCard', learnerFacing: true },
  daily_review: { category: 'revision', renderInside: ['DashboardPage', 'FlashcardsPage'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  personal_revision_plan: { category: 'revision', renderInside: ['NotebookPage', 'ReviewerInsightsPage'], primaryComponent: 'RevisionSummaryCard', learnerFacing: true },
  recommended_revision_views: { category: 'revision', renderInside: ['GuidedTutorJourney'], primaryComponent: 'SelectedTeachingViewRenderer', learnerFacing: true },
  spaced_repetition_card: { category: 'revision', renderInside: ['FlashcardsPage'], primaryComponent: 'FlashcardDeck', learnerFacing: true },

  flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck', 'GuidedTutorJourney'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  concept_recall_flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck', 'GuidedTutorJourney'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  misconception_flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck', 'GuidedTutorJourney'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  example_flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck', 'GuidedTutorJourney'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  debug_flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck', 'GuidedTutorJourney'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  personal_flashcards: { category: 'flashcards', renderInside: ['FlashcardDeck', 'NotebookPage'], primaryComponent: 'FlashcardDeck', learnerFacing: true },
  syntax_flashcard: { category: 'flashcards', renderInside: ['FlashcardDeck'], primaryComponent: 'FlashcardDeck', learnerFacing: true },

  mindmap: { category: 'mindmaps', renderInside: ['MindMapView', 'GuidedTutorJourney'], primaryComponent: 'MindMapView', learnerFacing: true },
  concept_mindmap: { category: 'mindmaps', renderInside: ['MindMapView', 'GuidedTutorJourney'], primaryComponent: 'MindMapView', learnerFacing: true },
  comparison_mindmap: { category: 'mindmaps', renderInside: ['MindMapView', 'GuidedTutorJourney'], primaryComponent: 'MindMapView', learnerFacing: true },

  feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CogniGuideCard'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  correct_answer_feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CogniGuideCard'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  wrong_answer_feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CogniGuideCard'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  partial_answer_feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CogniGuideCard'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  debug_feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CodeConsole'], primaryComponent: 'FeedbackCard', learnerFacing: true },
  output_prediction_feedback: { category: 'feedback', renderInside: ['FeedbackPanel'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  next_step_feedback: { category: 'feedback', renderInside: ['FeedbackPanel', 'CogniGuideCard'], primaryComponent: 'ActivityRenderer feedback panel', learnerFacing: true },
  encouragement_feedback: { category: 'feedback', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard', learnerFacing: true },

  hint: { category: 'hints', renderInside: ['HintPanel', 'Question cards'], primaryComponent: 'HintPanel', learnerFacing: true },
  small_hint: { category: 'hints', renderInside: ['HintPanel', 'Question cards'], primaryComponent: 'HintPanel', learnerFacing: true },
  guided_hint: { category: 'hints', renderInside: ['HintPanel', 'Question cards'], primaryComponent: 'HintPanel', learnerFacing: true },
  worked_example_hint: { category: 'hints', renderInside: ['HintPanel', 'Question cards'], primaryComponent: 'HintPanel', learnerFacing: true },
  debug_hint: { category: 'hints', renderInside: ['HintPanel', 'CodeConsole'], primaryComponent: 'HintPanel', learnerFacing: true },
  syntax_hint: { category: 'hints', renderInside: ['HintPanel', 'Question cards'], primaryComponent: 'HintPanel', learnerFacing: true },
  output_prediction_hint: { category: 'hints', renderInside: ['HintPanel', 'OutputPredictionCard'], primaryComponent: 'HintPanel', learnerFacing: true },
  misconception_hint: { category: 'hints', renderInside: ['HintPanel'], primaryComponent: 'HintPanel', learnerFacing: true },
  next_step_hint: { category: 'hints', renderInside: ['HintPanel'], primaryComponent: 'HintPanel', learnerFacing: true },
  analogy_hint: { category: 'hints', renderInside: ['HintPanel'], primaryComponent: 'HintPanel', learnerFacing: true },

  doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel', 'GuidedTutorJourney'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  concept_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  syntax_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  debug_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  output_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  example_request_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  revision_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  next_step_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },
  comparison_doubt_answer: { category: 'doubt', renderInside: ['DoubtPanel'], primaryComponent: 'DoubtPanel', learnerFacing: true },

  notebook_summary: { category: 'notebook', renderInside: ['NotebookPage', 'DashboardPage'], primaryComponent: 'NotebookPage', learnerFacing: true },
  mistake_summary: { category: 'notebook', renderInside: ['NotebookPage', 'MistakesPage'], primaryComponent: 'MistakeReviewCard', learnerFacing: true },
  revision_plan: { category: 'notebook', renderInside: ['NotebookPage'], primaryComponent: 'NotebookPage', learnerFacing: true },
  comeback_summary: { category: 'notebook', renderInside: ['DashboardPage'], primaryComponent: 'CogniGuideCard', learnerFacing: true },
  returning_learner_summary: { category: 'notebook', renderInside: ['DashboardPage'], primaryComponent: 'CogniGuideCard', learnerFacing: true },
  progress_insight: { category: 'notebook', renderInside: ['ProgressPage', 'ReviewerInsightsPage'], primaryComponent: 'ReviewerInsightsPage', learnerFacing: true },

  practice_question: { category: 'practice', renderInside: assessment, primaryComponent: 'AssessmentRenderer', learnerFacing: true },
  transfer_task: { category: 'practice', renderInside: assessment, primaryComponent: 'TransferQuestionCard', learnerFacing: true },
  real_world_application_question: { category: 'practice', renderInside: assessment, primaryComponent: 'ChallengeQuestionCard', learnerFacing: true },
  debug_challenge: { category: 'practice', renderInside: assessment, primaryComponent: 'CodeConsole', learnerFacing: true },
  output_prediction_challenge: { category: 'practice', renderInside: assessment, primaryComponent: 'OutputPredictionCard', learnerFacing: true },
  multi_step_challenge: { category: 'practice', renderInside: assessment, primaryComponent: 'ChallengeQuestionCard', learnerFacing: true },

  voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  teaching_voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  revision_voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  mistake_feedback_voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  doubt_explanation_voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  encouragement_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  next_step_guidance_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
  concept_intro_voice_script: { category: 'voice_script', renderInside: ['CogniGuideCard'], primaryComponent: 'CogniGuideCard text only', learnerFacing: true },
};

export function getTaskTypeMapping(taskType: string) {
  return taskTypeMap[taskType] || taskTypeMap.explanation_check;
}
