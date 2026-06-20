import {
  Subject,
  ConceptNode,
  TeachingContent,
  AssessmentQuestion,
  CodeRunOutput,
  CodeSubmitResult,
  NotebookMemory,
  RewardState,
  LessonResult,
  DoubtResponse,
  DoubtFollowUpResult,
  MistakeReview,
  ProgressData,
  DemoRunData,
  CelebrationState,
  ProgressionResult,
  AuthResult,
  LearnerProfile,
  NotebookSearchResult,
  PuzzleActivity,
  Flashcard,
  MindMap,
  AdaptiveHint,
  LearnedHintOutput,
  RetentionPrediction,
  AdaptivePathRecommendation,
  RAGGroundingEvidence,
  XAIReflection,
} from './types';

export const mockSubjects: Subject[] = [
  { id: 'python', name: 'Python', progress: 72, unlockedConcepts: 14, totalConcepts: 20, icon: 'FileCode2', color: 'bg-sky-500', description: 'Programming foundations and problem solving.' },
  { id: 'sql', name: 'SQL / Database', progress: 38, unlockedConcepts: 6, totalConcepts: 15, icon: 'Database', color: 'bg-amber-500', description: 'Queries, joins, grouping, and data retrieval.' },
  { id: 'html', name: 'HTML/Web Basics', progress: 54, unlockedConcepts: 11, totalConcepts: 25, icon: 'Globe', color: 'bg-orange-500', description: 'Markup, links, forms, and web structure.' },
  { id: 'git', name: 'Git', progress: 24, unlockedConcepts: 3, totalConcepts: 10, icon: 'GitBranch', color: 'bg-violet-500', description: 'Version control workflows and collaboration.' },
  { id: 'dsa', name: 'Data Structures', progress: 18, unlockedConcepts: 5, totalConcepts: 30, icon: 'Network', color: 'bg-emerald-500', description: 'Arrays, stacks, queues, maps, and trees.' },
];

export const mockLearningPath: ConceptNode[] = [
  { id: 'P1', name: 'Variables', subjectId: 'python', status: 'mastered', type: 'lesson', difficulty: 'easy', dependsOn: [], mastery: 96, recommendedAction: 'Review with flashcards', adaptiveRank: 2 },
  { id: 'P2', name: 'Data Types', subjectId: 'python', status: 'current', type: 'lesson', difficulty: 'easy', dependsOn: ['P1'], prerequisiteConcept: 'Variables', mastery: 62, recommendedAction: 'Start adaptive lesson', adaptiveRank: 1 },
  { id: 'P3', name: 'Conditionals', subjectId: 'python', status: 'review_due', type: 'revision', difficulty: 'medium', dependsOn: ['P2'], prerequisiteConcept: 'Data Types', mastery: 58, reviewDue: true, recommendedAction: 'Review before quiz', adaptiveRank: 3 },
  { id: 'P4', name: 'Loops Challenge', subjectId: 'python', status: 'challenge', type: 'challenge', difficulty: 'medium', dependsOn: ['P3'], prerequisiteConcept: 'Conditionals', mastery: 35, recommendedAction: 'Try a guided challenge', adaptiveRank: 4 },
  { id: 'P5', name: 'Functions Boss', subjectId: 'python', status: 'locked', type: 'boss', difficulty: 'hard', dependsOn: ['P4'], prerequisiteConcept: 'Loops Challenge', lockedReason: 'Clear Loops Challenge to unlock this boss node.', mastery: 0, recommendedAction: 'Complete prerequisite challenge', adaptiveRank: 5 },
];

export const mockLesson: TeachingContent = {
  conceptId: 'P2',
  conceptName: 'Data Types',
  difficulty: 'easy',
  explanationMode: 'code',
  selectedView: 'code_view',
  adaptiveExplanation: 'Data types tell Python what kind of value a variable stores, so operations and checks behave correctly.',
  fallbackViewNames: ['simple_example_view', 'analogy_view', 'misconception_view', 'step_by_step_view', 'code_example_view'],
  keyPoints: ['Strings use quotes', 'Integers do not use quotes', 'Lists can hold mixed values'],
  commonMistakes: ['Forgetting quotes around text', 'Adding numbers and strings directly'],
  workedExample: 'age = 18\nname = "Ava"\nprint(type(age), type(name))',
  whySelected: 'You made recent syntax mistakes around literals, so code_view was selected.',
  nextActivity: 'output_prediction',
};

export const mockAssessments: AssessmentQuestion[] = [
  { questionId: 'Q1', taskType: 'output_prediction', questionType: 'output_prediction', difficulty: 'easy', prompt: 'What will this code print?', code: 'name = "Alice"\nprint(name)', expectedOutput: 'Alice' },
  { questionId: 'Q2', taskType: 'debug_task', questionType: 'debug_task', difficulty: 'medium', prompt: 'Fix the bug in the code.', buggyCode: 'name = Alice\nprint(name)', expectedOutput: 'Alice', hint: 'Check how strings are written in Python.' },
  { questionId: 'Q3', taskType: 'syntax_completion', questionType: 'syntax_completion', difficulty: 'easy', prompt: 'Complete the statement to print 20.', starterCode: 'x = 20\n# write print statement below', expectedOutput: '20' },
  { questionId: 'Q4', taskType: 'coding_question', questionType: 'coding_question', difficulty: 'medium', prompt: 'Write a function square(n) that returns n*n.', starterCode: 'def square(n):\n    # your code here\n    pass', testCases: [{ input: '2', expectedOutput: '4' }, { input: '5', expectedOutput: '25' }] },
  { questionId: 'Q5', taskType: 'mcq', questionType: 'mcq', difficulty: 'easy', prompt: 'Which data type is used for whole numbers?', options: ['String', 'Integer', 'Float', 'Boolean'], correctAnswer: 'Integer' },
  { questionId: 'Q6', taskType: 'fill_blank', questionType: 'fill_blank', difficulty: 'medium', prompt: 'Fill the missing operator to compare equality: x __ 10', blanks: [{ id: 'b1', label: 'operator', answer: '==' }], correctAnswer: '==' },
  { questionId: 'Q7', taskType: 'match_pairs', questionType: 'match_pairs', difficulty: 'medium', prompt: 'Match concept with description.', pairs: [{ left: 'int', right: 'whole number' }, { left: 'str', right: 'text' }] },
  { questionId: 'Q8', taskType: 'short_explanation', questionType: 'short_explanation', difficulty: 'medium', prompt: 'Explain why variable naming matters in Python.' },
  { questionId: 'Q9', taskType: 'transfer_question', questionType: 'transfer_question', difficulty: 'medium', prompt: 'Apply variable naming rules to create a valid score variable for a game.', sourceConcept: 'Variables' },
  { questionId: 'Q10', taskType: 'challenge_question', questionType: 'challenge_question', difficulty: 'hard', prompt: 'Design a small snippet that stores a player name, score, and pass/fail flag.' },
  { questionId: 'Q11', taskType: 'code_tracing', questionType: 'code_tracing', difficulty: 'medium', prompt: 'Trace the final value of total.', code: 'total = 2\ntotal = total + 3\nprint(total)', expectedOutput: '5' },
  { questionId: 'Q12', taskType: 'drag_order', questionType: 'drag_order', difficulty: 'easy', prompt: 'Order the steps to create and use a variable.', options: ['Choose a name', 'Assign a value', 'Use it in an expression'], items: ['Use it in an expression', 'Choose a name', 'Assign a value'] },
];

export const mockRunOutput: CodeRunOutput = {
  status: 'success',
  runOutput: {
    stdout: 'Alice\n',
    stderr: '',
    errorType: null,
    errorMessage: null,
    timedOut: false,
    blocked: false,
  },
};

export const mockSubmitResult: CodeSubmitResult = {
  status: 'success',
  questionId: 'Q2',
  taskType: 'debug',
  correct: true,
  score: 0.95,
  runOutput: {
    stdout: 'Alice\n',
    stderr: '',
    errorType: null,
    errorMessage: null,
    timedOut: false,
    blocked: false,
  },
  testResults: [
    { input: '', expectedOutput: 'Alice', actualOutput: 'Alice', passed: true },
    { input: '', expectedOutput: 'no crash', actualOutput: 'no crash', passed: true },
  ],
  feedback: 'Great fix. You correctly added quotes around the string literal.',
  nextAction: 'continue',
};

export const mockNotebook: NotebookMemory = {
  learnerId: 'demo_learner',
  conceptId: 'P1',
  summary: 'Variables are named containers for values. Python infers the type from the assigned value.',
  weakPoints: ['variable naming', 'output prediction', 'type conversion'],
  mistakes: ['Started variable with a number', 'Forgot quotes in SQL string literal'],
  revisionPlan: ['Practice 5 output-prediction questions', 'Review naming rules', 'Do one debug challenge'],
  savedFlashcards: ['What is a valid Python identifier?', 'Difference between int and str'],
  lastUpdated: new Date().toISOString(),
  pastDoubts: ['Why is 2score wrong?', 'When should I use str() conversion?'],
  savedExplanations: ['Variables are labels for values.', 'Strings need quotes in Python.'],
  practiceHistory: ['Output prediction: 4/5', 'Debug task: 2/3'],
};

export const mockAuthResult: AuthResult = {
  access_token: 'mock-access-token',
  user_id: 'demo_user',
  learner_id: 'demo_learner',
  user: { id: 'demo_user', name: 'Demo Learner', email: 'learner@demo.com', role: 'learner' },
};

export const mockLearnerProfile: LearnerProfile = {
  learnerId: 'demo_learner',
  userId: 'demo_user',
  displayName: 'Demo Learner',
  goal: 'Learn data analysis',
  level: 'beginner',
  preferredSubject: 'Python',
  currentStreak: 0,
  totalXp: 0,
};

export const mockNotebookSearchResults: NotebookSearchResult[] = [
  { id: 'ns1', sourceType: 'summary', concept: 'Variables', summary: 'Variables are named references to values used later in code.', score: 0.94, timestamp: 'Today', tags: ['summary', 'python'] },
  { id: 'ns2', sourceType: 'mistake', concept: 'Variable Naming', summary: 'Learner previously started an identifier with a number.', score: 0.89, timestamp: 'Yesterday', tags: ['mistake', 'syntax'] },
  { id: 'ns3', sourceType: 'doubt', concept: 'Strings', summary: 'Prior doubt about why text values require quotes.', score: 0.82, timestamp: '3 days ago', tags: ['doubt', 'strings'] },
];

export const mockPuzzleActivities: PuzzleActivity[] = [
  { id: 'p1', conceptId: 'P1', type: 'debug', title: 'Fix the variable example', prompt: "This code should print a learner name, but the text value is missing quotes.", code: 'name = Alice\nprint(name)', solution: 'name = "Alice"', hint: 'Text values need quotes.', xp: 15 },
  { id: 'p2', conceptId: 'P1', type: 'predict_output', title: 'Predict Output', prompt: 'What will be printed?', code: 'score = 10\nprint(score)', solution: '10', hint: 'Trace the value stored in the variable.', xp: 10 },
];

export const mockFlashcards: Flashcard[] = [
  { id: 'f1', conceptId: 'P1', front: 'What is a variable?', back: 'A named reference that stores a value for later use.', difficulty: 'easy', due: true },
  { id: 'f2', conceptId: 'P1', front: "Why can't a variable start with a number?", back: 'Python identifiers must start with a letter or underscore.', difficulty: 'medium', due: true },
  { id: 'f3', conceptId: 'P2', front: 'What data type is 1.5?', back: 'Float.', difficulty: 'easy', due: true },
];

export const mockMindMap: MindMap = {
  conceptId: 'P1',
  title: 'Mind Map: Variables',
  center: 'Variables',
  nodes: [
    { id: 'definition', title: 'Definition', body: 'Variables are named references to values, making code readable and reusable.', color: 'from-[#2FC26E] to-[#26AE62]', x: 18, y: 20 },
    { id: 'syntax', title: 'Syntax Rules', body: 'Must start with letter/_ and can include numbers after the first character.', color: 'from-[#21B8F9] to-[#198FE6]', x: 72, y: 20 },
    { id: 'examples', title: 'Examples', body: 'score = 100\nname = "Ava"\npassed = True', color: 'from-[#7B61FF] to-[#6448EE]', x: 82, y: 62 },
    { id: 'mistakes', title: 'Common Mistakes', body: 'Using spaces, starting with digits, or shadowing built-ins like list.', color: 'from-[#FF6B8A] to-[#F24F75]', x: 20, y: 72 },
    { id: 'related', title: 'Related Concepts', body: 'Data types, assignment operators, scope, and function parameters.', color: 'from-[#FF9E2C] to-[#F08800]', x: 50, y: 86 },
  ],
};

export const mockAdaptiveHint: AdaptiveHint = {
  conceptId: 'P2',
  hintLevel: 'medium',
  message: 'Check whether your value is text or a number before choosing quotes.',
  example: 'name = "Ava" uses quotes; age = 18 does not.',
};

export const mockLearnedHintOutput: LearnedHintOutput = {
  learnerId: 'demo_learner',
  hintAccepted: true,
  updatedWeakness: 'string literal recognition',
  nextHintStrategy: 'show minimal contrasting example',
};

export const mockRetentionPrediction: RetentionPrediction = {
  learnerId: 'demo_learner',
  conceptId: 'P2',
  retentionProbability: 0.68,
  reviewDueInDays: 2,
  riskLevel: 'medium',
};

export const mockAdaptivePathRecommendation: AdaptivePathRecommendation = {
  learnerId: 'demo_learner',
  conceptId: 'P2',
  rank: 1,
  recommendedAction: 'Start adaptive lesson, then take a short quiz.',
  reason: 'Current concept is unlocked, has medium retention risk, and blocks later conditionals.',
};

export const mockRAGGroundingEvidence: RAGGroundingEvidence = {
  supportScore: 0.91,
  verdict: 'supported',
  safeToGenerate: true,
  evidenceSectionsUsed: ['definition', 'syntax_rules', 'misconceptions'],
  unsupportedTerms: [],
  retrievedSourceSnippets: [
    { sourceId: 'py_basics_01', section: 'Variable syntax', snippet: 'Identifiers begin with a letter or underscore and can contain digits after the first character.' },
    { sourceId: 'py_basics_02', section: 'String literals', snippet: 'Text values are represented as strings and are written with quotes.' },
  ],
};

export const mockXAIReflection: XAIReflection = {
  learnerId: 'demo_learner',
  conceptId: 'P2',
  teachingViewReason: 'Code view was selected because recent mistakes were syntax-related and the learner responds well to concrete examples.',
  difficultyReason: 'Easy difficulty was selected because retention prediction is medium-risk and the current concept is foundational.',
  promotionReason: 'Promotion did not happen yet because debug accuracy is below the threshold for the next node.',
  topFactors: [
    { factor: 'Recent syntax mistakes', impact: 'Selected code-first explanation', weight: 0.34 },
    { factor: 'Output prediction accuracy', impact: 'Kept practice short and guided', weight: 0.27 },
    { factor: 'Notebook weak areas', impact: 'Prioritized variable naming reminders', weight: 0.22 },
  ],
  surrogateModel: 'Interpretable decision tree v0.3',
  counterfactual: 'If debug accuracy rises above 85% and no quote mistakes appear in the next quiz, the learner is promoted to medium difficulty.',
  teacherEvidence: ['2 recent string literal mistakes', '1 successful output prediction', 'Notebook weak area: variable naming'],
  nextActionReason: 'A short syntax-completion quiz should confirm whether the quote misconception is resolved.',
  ragEvidence: mockRAGGroundingEvidence,
};

export const mockDemoLearnerProfiles: LearnerProfile[] = [
  mockLearnerProfile,
  { ...mockLearnerProfile, learnerId: 'demo_sql', userId: 'demo_user_sql', displayName: 'Demo SQL Learner', level: 'intermediate', preferredSubject: 'SQL / Database', totalXp: 0 },
  { ...mockLearnerProfile, learnerId: 'demo_dsa', userId: 'demo_user_dsa', displayName: 'Demo DSA Learner', level: 'advanced', preferredSubject: 'Data Structures', totalXp: 0 },
];

export const mockRewardState: RewardState = {
  totalXp: 0,
  xpAwardedToday: 0,
  currentLevel: 1,
  nextLevelXp: 100,
  dailyGoalXp: 50,
  dailyGoalCompleted: false,
  currentStreak: 0,
  longestStreak: 0,
  streakUpdated: false,
};

export const mockCelebration: CelebrationState = {
  show: true,
  type: 'concept_cleared',
  message: 'Great work! You cleared Variables.',
  mascotEmotion: 'happy',
  animation: 'confetti',
  xpAwarded: 20,
  streakUpdated: true,
  nextUnlock: 'Data Types',
};

export const mockProgressionResult: ProgressionResult = {
  currentConcept: 'Variables',
  currentDifficulty: 'medium',
  passed: true,
  nextDifficulty: 'hard',
  conceptCleared: false,
  nextConceptUnlocked: null,
  message: 'Great! Medium level cleared. Hard challenge unlocked.',
};

export const mockLessonResult: LessonResult = {
  score: 0.86,
  verdict: 'strong',
  correctCount: 4,
  partialCount: 1,
  wrongCount: 0,
  weakAreas: ['debug'],
  xpAwarded: 30,
  nextAction: 'Move to challenge',
};

export const mockDoubtResponse: DoubtResponse = {
  status: 'success',
  module: 'CogniTutorLMDoubtHandler',
  learnerId: 'demo_learner',
  doubtText: 'Why is 2score = 10 wrong?',
  doubtType: 'debug_doubt',
  conceptId: 'c1',
  conceptName: 'Variables',
  domain: 'Python',
  ragGrounded: true,
  answer: 'In Python, an identifier cannot start with a digit. Begin with a letter or underscore.',
  simpleExplanation: 'Use score2 or totalScore, not 2score.',
  example: { title: 'Correct variable naming', code: 'score2 = 10\nprint(score2)', explanation: 'Starts with a letter, so it is valid.' },
  sourceSectionsUsed: ['definition', 'key_points', 'misconceptions'],
  retrievedContextSummary: 'Grounded in naming rules and prior learner mistakes.',
  followUpCheck: {
    questionType: 'syntax_completion',
    question: 'Which variable name is valid in Python?',
    options: ['2score', 'score2', 'total-score', 'class'],
    correctAnswer: 'score2',
  },
  recommendedNextAction: 'Try one syntax practice question.',
  memoryUpdateSuggestion: {
    weakConcept: 'Variables',
    weakQuestionType: 'debug',
    mistakeType: 'syntax_misunderstanding',
  },
};

export const mockDoubtFollowUpResult: DoubtFollowUpResult = {
  status: 'success',
  correct: true,
  score: 1,
  feedback: 'Correct. Variable names cannot start with digits.',
  memoryUpdated: true,
  nextAction: 'Continue lesson',
};

export const mockMistakeReview: MistakeReview[] = [
  {
    mistakeId: 'm1', learnerId: 'demo_learner', subject: 'Python', conceptId: 'P1', conceptName: 'Variable Naming', questionId: 'q_py_01', questionType: 'syntax',
    prompt: 'Fix this variable declaration.', learnerAnswer: '2score = 100', expectedAnswer: 'score2 = 100',
    feedback: 'Variable names cannot start with numbers.', misconceptionDetected: 'Identifiers can start with digits',
    mistakeType: 'syntax', severity: 'high', status: 'needs_review', tryAgainType: 'Syntax'
  },
  {
    mistakeId: 'm2', learnerId: 'demo_learner', subject: 'SQL', conceptId: 'S2', conceptName: 'String Literals', questionId: 'q_sql_03', questionType: 'debug',
    prompt: 'Fix the SQL query literal.', learnerAnswer: 'SELECT * FROM users WHERE name = Alice', expectedAnswer: "SELECT * FROM users WHERE name = 'Alice'",
    feedback: 'String literals must be wrapped in single quotes.', misconceptionDetected: 'SQL string formatting confusion',
    mistakeType: 'concept', severity: 'medium', status: 'needs_review', tryAgainType: 'Debug'
  },
  {
    mistakeId: 'm3', learnerId: 'demo_learner', subject: 'HTML', conceptId: 'H3', conceptName: 'Anchor Tag', questionId: 'q_html_01', questionType: 'concept',
    prompt: 'Create a working hyperlink.', learnerAnswer: '<a>Click Here</a>', expectedAnswer: "<a href='url'>Click Here</a>",
    feedback: 'Anchor tags need an href target.', misconceptionDetected: 'Anchor semantic misunderstanding',
    mistakeType: 'concept', severity: 'low', status: 'reviewed', tryAgainType: 'Concept'
  },
];

export const mockProgressData: ProgressData = {
  currentLevel: 1,
  totalXP: 0,
  currentStreak: 0,
  conceptsMastered: 0,
  accuracy: 0,
  averageConfidence: 0,
  reviewDue: 0,
  xpToday: 0,
  masteryPercent: 0,
  subjectProgress: [
    { subjectName: 'Python', progressPercentage: 75, masteredConcepts: 15, totalConcepts: 20, color: '#1CB0F6' },
    { subjectName: 'SQL', progressPercentage: 30, masteredConcepts: 5, totalConcepts: 15, color: '#FFC800' },
    { subjectName: 'HTML', progressPercentage: 56, masteredConcepts: 14, totalConcepts: 25, color: '#58CC02' },
  ],
  conceptMastery: [
    { conceptName: 'Variables', subject: 'Python', mastery: 96, status: 'mastered', lastPracticed: 'Today' },
    { conceptName: 'Conditionals', subject: 'Python', mastery: 62, status: 'in_progress', lastPracticed: 'Yesterday' },
    { conceptName: 'SQL Joins', subject: 'SQL', mastery: 42, status: 'review_due', lastPracticed: '3 days ago' },
  ],
  weakAreas: [
    { concept: 'Loop Debugging', skill: 'Debug', severity: 'high', recommendedAction: 'Solve 3 guided debug tasks' },
    { concept: 'SQL Joins', skill: 'Concept', severity: 'medium', recommendedAction: 'Revisit examples in notebook' },
  ],
  xpHistory: [
    { day: 'Mon', xp: 120 }, { day: 'Tue', xp: 250 }, { day: 'Wed', xp: 180 }, { day: 'Thu', xp: 300 }, { day: 'Fri', xp: 280 }, { day: 'Sat', xp: 400 }, { day: 'Sun', xp: 320 }
  ],
  streakCalendar: [
    { day: 'Mon', completed: true, xp: 120 }, { day: 'Tue', completed: true, xp: 250 }, { day: 'Wed', completed: true, xp: 180 },
    { day: 'Thu', completed: true, xp: 300 }, { day: 'Fri', completed: true, xp: 280 }, { day: 'Sat', completed: true, xp: 400 }, { day: 'Sun', completed: true, xp: 320 }
  ],
};

export const mockDemoRunData: DemoRunData = {
  profile: 'beginner',
  selectedView: 'simple_example_view',
  assessmentJson: { generatedQuestions: 3 },
  xaiReason: 'Learner struggled with syntax previously. Presenting minimal code examples.',
  notebookMemory: { recentMistake: 'Forgot colon in if statement' },
  rewardOutput: { xpGained: 15, streakMaintained: true },
  backendJson: { requestId: '12345', processingTime: '120ms' },
  ragSource: 'DocID: py_basics_02, Section: Conditionals',
  decisionOutput: { recommendation: 'Start flashcard review' },
  evaluationOutput: { masteryEstimate: 0.3 },
  rlOutput: { rewardSignal: 0.2, policyUpdate: true },
};
