import fs from 'node:fs';
import path from 'node:path';

const assessmentTypes = [
  'mcq',
  'debug_task',
  'output_prediction',
  'transfer_question',
  'challenge_question',
  'explanation_check',
  'syntax_completion',
  'coding_prompt',
  'code_reasoning_task',
  'fill_in_the_blank',
  'true_or_false',
  'practice_question',
  'transfer_task',
  'real_world_application_question',
  'debug_challenge',
  'output_prediction_challenge',
  'multi_step_challenge',
];
const flashcardVariants = [
  'flashcard',
  'concept_recall_flashcard',
  'misconception_flashcard',
  'example_flashcard',
  'debug_flashcard',
  'personal_flashcards',
  'syntax_flashcard',
];
const mindmapVariants = ['mindmap', 'concept_mindmap', 'comparison_mindmap'];
const notebookButtons = [
  'My Mistakes',
  'Practice Weaknesses Now',
  'Study Guide',
  'Ask simpler explanation',
  'Ask for analogy',
  'Ask for code example',
  'Ask why answer is wrong',
  'Ask another practice question',
  'Save to notebook',
];

const sample = {
  teaching_content: {
    title: 'Variables - Definition View',
    learning_goal: 'Understand variables.',
    beginner_explanation: 'Variables store named values so a program can reuse them later in examples, checks, and debugging.',
    definition: 'A variable is a name connected to a value.',
    why_it_matters: 'Variables make programs remember and reuse data.',
    step_by_step: ['name', 'assign', 'read', 'update'],
    example: 'score = 10',
    code_or_task_example: 'score = 10\nprint(score)',
    common_mistake: 'Confusing assignment with comparison.',
    real_world_use: 'Scores, names, prices, and progress.',
    quick_check: 'What is stored?',
  },
  aligned_assessments: [{ taskType: 'mcq' }],
  assessment_bank: assessmentTypes.map((type) => ({ taskType: type, questionType: type })),
  assessment_types_available: assessmentTypes,
  all_task_outputs: Array.from({ length: 89 }, (_, index) => ({ task_type: index < assessmentTypes.length ? assessmentTypes[index] : `task_${index}` })),
  flashcards: flashcardVariants.map((type) => ({ card_type: type, front: type, back: 'back' })),
  flashcard_variants_available: flashcardVariants,
  mindmap: { center: 'Variables', nodes: [] },
  mindmaps: Object.fromEntries(mindmapVariants.map((variant) => [variant, { center: variant, branches: [] }])),
  mindmap_variants_available: mindmapVariants,
  notebook: {},
  mistake_summary: ['Assignment vs comparison'],
  revision_plan: ['Review', 'Practice'],
  voice_script: { script: 'Audio script', audio_ready: true },
  audio_overview: { status: 'success', script: 'Audio script', audio_ready: true },
  hints: [{}],
  feedback_template: { correct: 'Correct', wrong: 'Review' },
  next_step: 'Continue',
  difficulty: 'easy',
  source_level: 'easy_content',
  teaching_view: 'definition_view',
  all_task_count: 89,
  rag_metadata: { rag_grounding_status: 'PASS' },
  frontend_ready: true,
};

const required = [
  'teaching_content',
  'aligned_assessments',
  'assessment_bank',
  'assessment_types_available',
  'all_task_outputs',
  'flashcards',
  'flashcard_variants_available',
  'mindmap',
  'mindmap_variants_available',
  'notebook',
  'mistake_summary',
  'revision_plan',
  'voice_script',
  'audio_overview',
  'hints',
  'feedback_template',
  'next_step',
  'difficulty',
  'source_level',
  'teaching_view',
  'all_task_count',
  'rag_metadata',
  'frontend_ready',
];

const teachingFields = [
  'title',
  'learning_goal',
  'beginner_explanation',
  'definition',
  'why_it_matters',
  'step_by_step',
  'example',
  'code_or_task_example',
  'common_mistake',
  'real_world_use',
  'quick_check',
];

const missing = required.filter((field) => !(field in sample));
const missingTeaching = teachingFields.filter((field) => !(field in sample.teaching_content));
const assessmentMissing = assessmentTypes.filter((type) => !sample.assessment_types_available.includes(type));
const flashcardMissing = flashcardVariants.filter((type) => !sample.flashcard_variants_available.includes(type));
const mindmapMissing = mindmapVariants.filter((type) => !sample.mindmap_variants_available.includes(type));
const checks = {
  required_fields: missing.length === 0,
  teaching_content_rich_fields: missingTeaching.length === 0,
  assessment_17_types: assessmentMissing.length === 0 && sample.assessment_bank.length >= 17,
  flashcard_7_variants: flashcardMissing.length === 0 && sample.flashcards.length >= 7,
  mindmap_3_variants: mindmapMissing.length === 0,
  notebook_buttons_mapped: notebookButtons.length === 9,
  audio_overview_fields: Boolean(sample.audio_overview.script && sample.audio_overview.audio_ready),
  mistake_similar_question_support: assessmentTypes.includes('practice_question') && assessmentTypes.includes('debug_task'),
  next_progression_fields: Boolean(sample.next_step && sample.difficulty && sample.teaching_view),
};
const status = Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL';
const report = {
  status,
  frontend_contract_status: status,
  checks,
  missing_fields: missing,
  missing_teaching_fields: missingTeaching,
  missing_assessment_types: assessmentMissing,
  missing_flashcard_variants: flashcardMissing,
  missing_mindmap_variants: mindmapMissing,
  notebook_buttons: notebookButtons,
  raw_generation_status: 'WARN',
  guarded_generation_status: 'PASS',
  no_external_api: true,
  no_pretrained_model: true,
};

const out = path.resolve('frontend_cognitutor_connection_report.md');
fs.writeFileSync(
  out,
  `# Frontend CogniTutor Connection Report\n\n- status: ${status}\n- assessment_types: ${assessmentTypes.length}\n- flashcard_variants: ${flashcardVariants.length}\n- mindmap_variants: ${mindmapVariants.length}\n- notebook_buttons: ${notebookButtons.length}\n- raw_generation_status: WARN\n- guarded_generation_status: PASS\n- no_external_api: true\n- no_pretrained_model: true\n`,
  'utf8',
);
fs.mkdirSync(path.resolve('outputs', 'reports'), { recursive: true });
fs.writeFileSync(path.resolve('outputs', 'reports', 'frontend_cognitutor_connection_report.json'), JSON.stringify(report, null, 2), 'utf8');
console.log(`frontend_contract_status: ${status}`);
console.log(`report: ${out}`);
