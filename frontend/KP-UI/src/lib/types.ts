export interface Subject {
  id: string;
  name: string;
  progress: number;
  unlockedConcepts: number;
  totalConcepts: number;
  icon: string;
  color: string;
  description?: string;
}

export type Difficulty = 'easy' | 'medium' | 'hard';
export type NodeStatus = 'locked' | 'unlocked' | 'current' | 'mastered' | 'review_due' | 'challenge' | 'completed';
export type NodeType = 'lesson' | 'practice' | 'quiz' | 'challenge' | 'revision' | 'boss';

export interface ConceptNode {
  id: string;
  name: string;
  subjectId: string;
  status: NodeStatus;
  type: NodeType;
  difficulty: Difficulty;
  dependsOn: string[];
  lockedReason?: string;
  prerequisiteConcept?: string;
  mastery?: number;
  reviewDue?: boolean;
  recommendedAction?: string;
  adaptiveRank?: number;
}

export type PathNode = ConceptNode;

export interface User {
  id: string;
  name: string;
  email: string;
  role?: 'learner' | 'teacher' | 'admin';
}

export interface AuthResult {
  access_token: string;
  user_id: string;
  learner_id: string;
  app_learner_code?: string;
  name?: string;
  email?: string;
  active_subject?: string;
  selected_subject?: string;
  current_subject?: string;
  current_concept?: string;
  current_concept_id?: string;
  current_concept_name?: string;
  current_difficulty?: string;
  preferred_subject?: string;
  next_route?: string;
  user: User;
}

export interface LearnerProfile {
  learnerId: string;
  userId: string;
  displayName: string;
  goal: string;
  level: 'beginner' | 'intermediate' | 'advanced';
  preferredSubject: string;
  currentStreak: number;
  totalXp: number;
  activeSubject?: string;
  currentConceptId?: string;
  currentConceptName?: string;
  returningRevisionNeeded?: boolean;
  guideMessage?: string;
}

export type GuidedActivityType =
  | 'welcome'
  | 'subject_selection'
  | 'teaching'
  | 'mini_check'
  | 'assessment'
  | 'feedback'
  | 'hint'
  | 'flashcard_revision'
  | 'mindmap_revision'
  | 'misconception_review'
  | 'revision_summary'
  | 'doubt_answer'
  | 'weakness_review'
  | 'comeback_summary'
  | 'code_practice'
  | 'challenge_practice'
  | 'reward'
  | 'xai_explanation'
  | 'next_step_guidance'
  | 'next_concept'
  | 'returning_revision'
  | 'complete';

export interface GuidedActivity {
  type: GuidedActivityType;
  frontend_component?: string;
  payload?: Record<string, unknown>;
}

export interface NextRecommendedActivity {
  type: GuidedActivityType;
  label: string;
  reason: string;
}

export interface GuidedFlowFields {
  auto_flow?: boolean;
  current_activity?: GuidedActivity;
  next_recommended_activity?: NextRecommendedActivity;
  recommended_next_activity?: NextRecommendedActivity;
  guide_message?: string;
  backend_connected?: boolean;
  memory_update?: {
    saved_to_notebook?: boolean;
    mistake_logged?: boolean;
    revision_saved?: boolean;
  };
}

export interface SubjectSelectionResult extends GuidedFlowFields {
  status: string;
  active_subject: string;
  current_concept_id: string;
  current_concept_name: string;
  current_difficulty?: string;
  current_teaching_view?: string;
  selected_teaching_view?: string;
  next_route: string;
}

export interface TeachingView {
  id: string;
  label: string;
  description: string;
  selectedReason?: string;
}

export interface TeachingContent {
  conceptId: string;
  conceptName: string;
  difficulty: Difficulty;
  explanationMode: string;
  selectedView: string;
  requestedView?: string;
  backendConnected?: boolean;
  mockFallbackUsed?: boolean;
  backendStatusReason?: string;
  adaptiveExplanation: string;
  fallbackViewNames: string[];
  keyPoints: string[];
  commonMistakes: string[];
  workedExample: string;
  whySelected: string;
  nextActivity: string;
  subject?: string;
  ragEvidence?: Record<string, unknown>;
  teachingStrategy?: Record<string, unknown>;
  xai?: Record<string, unknown>;
  generationStatus?: string;
  difficultyProgress?: DifficultyProgress;
  teachingContent?: {
    title?: string;
    learning_goal?: string;
    concept_intro?: string;
    definition?: string;
    beginner_explanation?: string;
    why_it_matters?: string;
    step_by_step?: string[];
    explanation?: string;
    examples?: string[];
    example?: string;
    syntax?: string;
    code?: string;
    key_points?: string[];
    common_mistakes?: string[];
    misconception_correction?: string;
    debug_explanation?: string;
    output_tracing_explanation?: string;
    real_world_use?: string;
    transfer_context?: string;
    challenge_context?: string;
    comparison?: string;
    code_or_task_example?: string;
    common_mistake?: string;
    quick_check?: string;
    revision_line?: string;
    practice_prompt?: string;
    summary?: string;
  };
  contentByView?: Record<string, {
    title?: string;
    learning_goal?: string;
    concept_intro?: string;
    definition?: string;
    beginner_explanation?: string;
    why_it_matters?: string;
    step_by_step?: string[];
    explanation?: string;
    examples?: string[];
    example?: string;
    syntax?: string;
    code?: string;
    key_points?: string[];
    common_mistakes?: string[];
    misconception_correction?: string;
    debug_explanation?: string;
    output_tracing_explanation?: string;
    real_world_use?: string;
    transfer_context?: string;
    challenge_context?: string;
    comparison?: string;
    code_or_task_example?: string;
    common_mistake?: string;
    quick_check?: string;
    revision_line?: string;
    practice_prompt?: string;
    summary?: string;
  }>;
  voiceScript?: string;
}

export type DifficultyProgressState = 'locked' | 'current' | 'passed' | 'review_due' | 'retry';
export type DifficultyProgress = Record<Difficulty, DifficultyProgressState>;

export interface AssessmentQuestion {
  questionId: string;
  taskType: string;
  frontendComponent?: string;
  questionType?: string;
  difficulty: Difficulty;
  prompt: string;
  code?: string;
  starterCode?: string;
  buggyCode?: string;
  expectedOutput?: string;
  testCases?: { input: string; expectedOutput: string }[];
  hint?: string;
  title?: string;
  instructions?: string;
  constraints?: string[];
  expected_answer?: unknown;
  expected_idea?: unknown;
  rubric?: unknown;
  evaluation_mode?: string;
  generated_source?: string;
  grounding_source_label?: string;
  frontend_component?: string;
  frontend_render_type?: string;
  instruction?: string;
  code_snippet?: string;
  hidden_hint?: string;
  source?: string;
  puzzle_type?: string;
  correct_order?: string[];
  options?: string[];
  correctAnswer?: string;
  pairs?: { left: string; right: string }[];
  blanks?: { id: string; label: string; answer: string }[];
  items?: string[];
  sourceConcept?: string;
  subject?: string;
  concept_id?: string;
  concept_name?: string;
}

export interface PuzzleActivity {
  id: string;
  conceptId: string;
  type: 'debug' | 'predict_output' | 'logic' | 'challenge';
  title: string;
  prompt: string;
  code?: string;
  solution: string;
  hint: string;
  xp: number;
}

export interface EvaluationResult {
  status: string;
  score: number;
  correct: boolean;
  feedback: string;
  weakAreas: string[];
  nextAction: string;
}

export interface CodeRunOutput {
  status: 'success' | 'error';
  runOutput: {
    stdout: string;
    stderr: string;
    errorType: string | null;
    errorMessage: string | null;
    timedOut: boolean;
    blocked: boolean;
  };
}

export interface TestResult {
  input: string;
  expectedOutput: string;
  actualOutput: string;
  passed: boolean;
}

export interface CodeSubmitResult extends CodeRunOutput {
  questionId: string;
  taskType: string;
  correct: boolean;
  score: number;
  testResults: TestResult[];
  feedback: string;
  feedback_by_type?: Record<string, string>;
  feedback_type?: string;
  source?: string;
  generation_source?: string;
  correct_answer?: string;
  learner_answer?: string;
  explanation?: string;
  mascot_script?: string;
  next_recommended_action?: string;
  recommended_teaching_view?: string;
  next_teaching_view?: string;
  recommended_view?: string;
  nextAction: string;
  label?: string;
  mistake_type?: string;
  weakest_skill?: string;
  recommended_next_activity?: NextRecommendedActivity;
  guide_message?: string;
  reward_state?: Record<string, unknown>;
  xai_reason?: Record<string, unknown>;
  memory_update?: {
    saved_to_notebook?: boolean;
    mistake_logged?: boolean;
    revision_saved?: boolean;
  };
  difficulty?: Difficulty;
  difficulty_passed?: boolean;
  concept_completed?: boolean;
  next_difficulty?: Difficulty;
  next_concept_id?: string | null;
  difficulty_progress?: DifficultyProgress;
}

export interface NotebookMemory {
  learnerId: string;
  conceptId: string;
  summary: string;
  weakPoints: string[];
  mistakes: string[];
  revisionPlan: string[];
  savedFlashcards: string[];
  lastUpdated: string;
  pastDoubts?: string[];
  notes?: { id?: number | string; title?: string; content?: string; note_type?: string; source_page?: string; updated_at?: string }[];
  savedNotes?: { id?: number | string; title?: string; content?: string; note_type?: string; source_page?: string; updated_at?: string }[];
  savedExplanations?: string[];
  practiceHistory?: string[];
  practiceQueue?: string[];
  learner_facing_summary?: string;
  learner_facing_key_points?: string[];
  learner_facing_mistakes?: string[];
  learner_facing_revision_plan?: string[];
  learner_facing_flashcards?: { front: string; back: string }[];
  learner_facing_doubts?: { question: string; answer_preview: string }[];
  learner_facing_practice_queue?: string[];
  source?: string;
  raw_evidence?: Record<string, unknown>;
  debug_evidence?: Record<string, unknown>;
}

export interface NotebookSearchResult {
  id: string;
  sourceType: 'summary' | 'mistake' | 'doubt' | 'flashcard' | 'practice';
  concept: string;
  summary: string;
  score: number;
  timestamp: string;
  tags: string[];
}

export interface RewardState {
  totalXp: number;
  xpAwardedToday: number;
  currentLevel: number;
  nextLevelXp: number;
  dailyGoalXp: number;
  dailyGoalCompleted: boolean;
  currentStreak: number;
  longestStreak: number;
  streakUpdated: boolean;
  badges?: string[];
  levelName?: string;
}

export interface CelebrationState {
  show: boolean;
  type: string;
  message: string;
  mascotEmotion: 'happy' | 'encouraging' | 'supportive';
  animation: 'confetti' | 'pulse' | 'sparkle';
  xpAwarded: number;
  streakUpdated: boolean;
  nextUnlock: string | null;
}

export type Celebration = CelebrationState;

export interface ProgressionResult {
  currentConcept: string;
  currentDifficulty: Difficulty;
  passed: boolean;
  nextDifficulty: Difficulty | null;
  conceptCleared: boolean;
  nextConceptUnlocked: string | null;
  message: string;
}

export interface LessonResult {
  score: number;
  verdict: string;
  correctCount: number;
  partialCount: number;
  wrongCount: number;
  weakAreas: string[];
  xpAwarded: number;
  nextAction: string;
}

export interface DoubtRequest {
  learnerId: string;
  doubtText: string;
  currentConceptId: string;
  currentConceptName: string;
  domain: string;
  currentTeachingView?: string;
  difficulty?: Difficulty;
  recentAssessmentTypes?: string[];
  weakestSkill?: string;
  dominantMistakeType?: string;
}

export interface DoubtResponse {
  status: string;
  module: string;
  learnerId: string;
  doubtText: string;
  doubtType: string;
  conceptId: string;
  conceptName: string;
  domain: string;
  ragGrounded: boolean;
  answer: string;
  simpleExplanation?: string;
  example?: {
    title: string;
    code: string;
    explanation: string;
  };
  sourceSectionsUsed?: string[];
  retrievedContextSummary?: string;
  voiceScript?: string;
  followUpCheck?: {
    questionType: string;
    question: string;
    options?: string[];
    correctAnswer: string;
  };
  recommendedNextAction?: string;
  memoryUpdateSuggestion?: {
    weakConcept: string;
    weakQuestionType: string;
    mistakeType: string;
  };
}

export interface DoubtFollowUpResult {
  status: string;
  correct: boolean;
  score: number;
  feedback: string;
  memoryUpdated: boolean;
  nextAction: string;
}

export type ProgressData = {
  hasProgressData?: boolean;
  sourceLabel?: string;
  currentLevel: number;
  totalXP: number;
  currentStreak: number;
  conceptsMastered: number;
  accuracy: number;
  averageConfidence: number;
  reviewDue: number;
  xpToday: number;
  masteryPercent: number;
  subjectProgress: {
    subjectName: string;
    progressPercentage: number;
    masteredConcepts: number;
    totalConcepts: number;
    color: string;
  }[];
  conceptMastery: {
    conceptName: string;
    subject: string;
    mastery: number;
    status: 'mastered' | 'in_progress' | 'review_due' | 'locked';
    lastPracticed: string;
  }[];
  weakAreas: {
    concept: string;
    skill: string;
    severity: 'low' | 'medium' | 'high';
    recommendedAction: string;
  }[];
  xpHistory: {
    day: string;
    xp: number;
  }[];
  streakCalendar: {
    day: string;
    completed: boolean;
    xp: number;
  }[];
  recentAttempts?: {
    conceptName: string;
    subject: string;
    questionType: string;
    score: number;
    timestamp: string;
  }[];
};

export type MistakeReview = {
  mistakeId: string;
  learnerId: string;
  subject: string;
  conceptId: string;
  conceptName: string;
  questionId: string;
  questionType: string;
  prompt: string;
  learnerAnswer: string;
  expectedAnswer: string;
  feedback: string;
  misconceptionDetected: string;
  mistakeType: string;
  severity: 'low' | 'medium' | 'high';
  status: 'needs_review' | 'reviewed' | 'mastered';
  tryAgainType: string;
};

export interface MindMap {
  conceptId: string;
  title: string;
  center: string;
  nodes: {
    id: string;
    title: string;
    body: string;
    color: string;
    x: number;
    y: number;
  }[];
  mindmap_variants?: Record<string, MindMap['nodes']>;
  available_mindmap_types?: string[];
}

export interface Flashcard {
  id: string;
  conceptId: string;
  front: string;
  back: string;
  difficulty: Difficulty;
  due: boolean;
  card_type?: string;
  cardType?: string;
  explanation?: string;
}

export interface AdaptiveHint {
  conceptId: string;
  hintLevel: 'light' | 'medium' | 'strong';
  message: string;
  example?: string;
}

export interface LearnedHintOutput {
  learnerId: string;
  hintAccepted: boolean;
  updatedWeakness: string;
  nextHintStrategy: string;
}

export interface RetentionPrediction {
  learnerId: string;
  conceptId: string;
  retentionProbability: number;
  reviewDueInDays: number;
  riskLevel: 'low' | 'medium' | 'high';
}

export interface AdaptivePathRecommendation {
  learnerId: string;
  conceptId: string;
  rank: number;
  recommendedAction: string;
  reason: string;
}

export interface RAGGroundingEvidence {
  supportScore: number;
  verdict: 'supported' | 'partially_supported' | 'unsupported';
  safeToGenerate: boolean;
  evidenceSectionsUsed: string[];
  unsupportedTerms: string[];
  retrievedSourceSnippets: {
    sourceId: string;
    section: string;
    snippet: string;
  }[];
}

export interface XAIReflection {
  learnerId: string;
  conceptId: string;
  teachingViewReason: string;
  difficultyReason: string;
  promotionReason: string;
  topFactors: { factor: string; impact: string; weight: number }[];
  surrogateModel: string;
  counterfactual: string;
  teacherEvidence: string[];
  nextActionReason: string;
  ragEvidence: RAGGroundingEvidence;
}

export interface DemoRunData {
  profile: string;
  selectedView: string;
  assessmentJson: Record<string, unknown>;
  xaiReason: string;
  notebookMemory: Record<string, unknown>;
  rewardOutput: Record<string, unknown>;
  backendJson: Record<string, unknown>;
  ragSource: string;
  decisionOutput: Record<string, unknown>;
  evaluationOutput: Record<string, unknown>;
  rlOutput: Record<string, unknown>;
}

export interface AdaptiveSession extends GuidedFlowFields {
  learner_id: string;
  concept_id?: string;
  concept_name?: string;
  frontend_response?: Record<string, unknown>;
  learner_session_state?: Record<string, unknown>;
}
