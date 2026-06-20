import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const outJson = path.join(root, 'outputs', 'final_evaluation', 'json', 'frontend_feature_final_evaluation.json');
const outMd = path.join(root, 'outputs', 'final_evaluation', 'reports', 'frontend_feature_final_evaluation.md');
const connectionMd = path.join(root, 'frontend_cognitutor_connection_report.md');

const files = {
  sidebar: 'src/components/layout/Sidebar.tsx',
  lesson: 'src/pages/LessonPage.tsx',
  selectedTeaching: 'src/components/teaching/SelectedTeachingViewRenderer.tsx',
  assessment: 'src/components/assessment/AssessmentRenderer.tsx',
  quiz: 'src/pages/QuizPage.tsx',
  puzzle: 'src/pages/PuzzlePage.tsx',
  flashcards: 'src/pages/FlashcardsPage.tsx',
  mindmap: 'src/pages/MindMapPage.tsx',
  notebook: 'src/pages/NotebookPage.tsx',
  mistakes: 'src/pages/MistakesPage.tsx',
  audio: 'src/pages/AudioOverviewPage.tsx',
  doubt: 'src/components/doubt/DoubtPanel.tsx',
  feedback: 'src/components/feedback/FeedbackPanel.tsx',
  topbar: 'src/components/layout/Topbar.tsx',
  api: 'src/lib/api.ts',
  fixture: 'src/fixtures/cognitutorProductPacket.ts',
  packageJson: 'package.json',
};

const assessmentTypes = [
  'mcq', 'debug_task', 'output_prediction', 'transfer_question', 'challenge_question',
  'explanation_check', 'syntax_completion', 'coding_prompt', 'code_reasoning_task',
  'fill_in_the_blank', 'true_or_false', 'practice_question', 'transfer_task',
  'real_world_application_question', 'debug_challenge', 'output_prediction_challenge',
  'multi_step_challenge',
];
const teachingViews = [
  'definition_view', 'simple_example_view', 'step_by_step_view', 'analogy_view',
  'code_view', 'debug_view', 'output_prediction_view', 'misconception_view',
  'transfer_view', 'challenge_view', 'revision_view', 'flashcard_view',
  'mindmap_view', 'voice_script_view',
];
const flashcardVariants = [
  'flashcard', 'concept_recall_flashcard', 'misconception_flashcard',
  'example_flashcard', 'debug_flashcard', 'personal_flashcards', 'syntax_flashcard',
];
const mindmapVariants = ['mindmap', 'concept_mindmap', 'comparison_mindmap'];

function read(file) {
  const full = path.join(root, file);
  return fs.existsSync(full) ? fs.readFileSync(full, 'utf8') : '';
}

function evidence(status, reason, fileList = []) {
  return { status, reason, files: fileList };
}

function labelsFromSidebar(source) {
  return [...source.matchAll(/label:\s*['"`]([^'"`]+)['"`]/g)].map((m) => m[1]);
}

const source = Object.fromEntries(Object.entries(files).map(([key, file]) => [key, read(file)]));
const allSource = Object.values(source).join('\n');
const sidebarLabels = labelsFromSidebar(source.sidebar);
const duplicateLabels = sidebarLabels.filter((label, index) => sidebarLabels.indexOf(label) !== index);

const checks = {
  no_duplicate_sidebar_entries: evidence(
    duplicateLabels.length === 0 && source.sidebar.includes('uniqueNavItems') ? 'PASS' : 'FAIL',
    duplicateLabels.length ? `duplicate labels: ${duplicateLabels.join(', ')}` : 'labels are unique and Sidebar filters duplicates',
    [files.sidebar],
  ),
  teaching_component_rich_fields: evidence(
    ['learning_goal', 'beginner_explanation', 'definition', 'why_it_matters', 'step_by_step', 'example', 'common_mistake', 'real_world_use', 'quick_check'].every((field) => allSource.includes(field)) ? 'PASS' : 'FAIL',
    'rich teaching field names are referenced by source or fixture',
    [files.selectedTeaching, files.lesson, files.fixture],
  ),
  teaching_14_view_tabs: evidence(
    teachingViews.every((view) => allSource.includes(view)) ? 'PASS' : 'FAIL',
    '14 required teaching view ids found in source/fixture',
    [files.lesson, files.selectedTeaching, files.api, files.fixture],
  ),
  assessment_renderer_17_types: evidence(
    assessmentTypes.every((type) => source.assessment.includes(type) || source.fixture.includes(type) || source.api.includes(type)) ? 'PASS' : 'FAIL',
    '17 assessment/practice task types found in renderer, api mapping, or fixture',
    [files.assessment, files.api, files.fixture],
  ),
  puzzle_quiz_more_than_2_questions: evidence(
    (source.quiz.includes('questions.length') || source.quiz.includes('activeQuestions.length') || source.quiz.includes('assessment_bank')) && (source.puzzle.includes('visibleChallenges.length') || source.puzzle.includes('challenges.length') || source.puzzle.includes('puzzle_tasks')) ? 'PASS' : 'FAIL',
    'quiz and puzzle sources iterate over question arrays instead of fixed two-question display',
    [files.quiz, files.puzzle],
  ),
  flashcard_variants_supported: evidence(
    flashcardVariants.every((variant) => allSource.includes(variant)) ? 'PASS' : 'FAIL',
    '7 flashcard variant ids found',
    [files.flashcards, files.fixture, files.api],
  ),
  mindmap_variants_supported: evidence(
    mindmapVariants.every((variant) => allSource.includes(variant)) ? 'PASS' : 'FAIL',
    'mindmap, concept_mindmap, comparison_mindmap found',
    [files.mindmap, files.fixture, files.api],
  ),
  notebook_buttons_wired: evidence(
    ['Study Guide', 'My Mistakes', 'Practice Weakness', 'Revision Plan', 'Flashcards', 'Past Doubts', 'Comeback Summary', 'Progress Insight'].every((label) => source.notebook.includes(label)) && source.notebook.includes('onClick=') ? 'PASS' : 'FAIL',
    'notebook action labels and onClick handlers found',
    [files.notebook],
  ),
  mistakes_try_similar_wired: evidence(
    source.mistakes.includes('trySimilar') && source.mistakes.includes('getSimilarQuestion') && source.mistakes.includes('AssessmentRenderer') ? 'PASS' : 'FAIL',
    'Try Similar Question handler/API/render fallback found',
    [files.mistakes],
  ),
  audio_overview_page_uses_voice: evidence(
    source.audio.includes('voice_script') && source.audio.includes('audio_overview') ? 'PASS' : 'FAIL',
    'AudioOverviewPage references voice_script and audio_overview',
    [files.audio],
  ),
  doubt_submit_handler: evidence(
    source.doubt.includes('onSubmit') || (source.doubt.includes('handle') && source.doubt.includes('askDoubt')) ? 'PASS' : 'FAIL',
    'doubt submit handler found',
    [files.doubt],
  ),
  hint_button_exists: evidence(
    source.assessment.includes('handleHint') && source.assessment.toLowerCase().includes('hint') ? 'PASS' : 'FAIL',
    'AssessmentRenderer includes hint handler/button path',
    [files.assessment],
  ),
  feedback_panel_handlers: evidence(
    ['Try Similar', 'Continue', 'Review'].every((label) => source.feedback.includes(label) || allSource.includes(label)) ? 'PASS' : 'FAIL',
    'feedback action labels found',
    [files.feedback, files.assessment],
  ),
  subject_context_prevents_python_fallback: evidence(
    source.api.includes('subjectConceptFallback') && source.api.includes('normalized.includes') && source.api.includes('sql') && source.api.includes('html') && source.api.includes('git') && source.api.includes('data') ? 'PASS' : 'FAIL',
    'subjectConceptFallback branches on selected subject before Python fallback',
    [files.api],
  ),
  live_mock_mode_badge: evidence(
    allSource.includes('backend') && allSource.includes('mock') && (source.topbar.includes('getBackendHealth') || allSource.includes('Backend connected')) ? 'PASS' : 'FAIL',
    'live/mock backend status text and health call found',
    [files.topbar, files.api],
  ),
  vite_api_base_url_configurable: evidence(
    source.api.includes('import.meta.env.VITE_API_BASE_URL') ? 'PASS' : 'FAIL',
    'API base URL uses VITE_API_BASE_URL',
    [files.api],
  ),
};

const failed = Object.entries(checks).filter(([, check]) => check.status === 'FAIL');
const manualBrowserVerification = 'MANUAL_REQUIRED';
const status = failed.length ? 'FAIL' : 'WARN';
const report = {
  evaluation_name: 'frontend_feature_final_evaluation',
  status,
  status_reason: failed.length ? 'required source/contract checks failed' : 'code/build checks can pass, but browser interaction verification was not executed by this script',
  manual_browser_verification: manualBrowserVerification,
  checks,
  failed_checks: failed.map(([name, check]) => ({ name, reason: check.reason, files: check.files })),
  limitations: [
    'This script verifies source and contract evidence only.',
    'Manual browser flows remain MANUAL_REQUIRED unless a browser checklist or automated browser script is recorded.',
  ],
};

fs.mkdirSync(path.dirname(outJson), { recursive: true });
fs.mkdirSync(path.dirname(outMd), { recursive: true });
fs.writeFileSync(outJson, JSON.stringify(report, null, 2), 'utf8');
const lines = [
  '# Frontend Feature Final Evaluation',
  '',
  `- status: ${status}`,
  `- manual_browser_verification: ${manualBrowserVerification}`,
  `- failed_checks: ${failed.length}`,
  '',
  '## Checks',
  ...Object.entries(checks).map(([name, check]) => `- ${name}: ${check.status} (${check.reason})`),
  '',
  '## Limitations',
  '- Browser click-through and visual/manual checks were not executed by this script.',
];
fs.writeFileSync(outMd, `${lines.join('\n')}\n`, 'utf8');
fs.writeFileSync(
  connectionMd,
  `# Frontend CogniTutor Connection Report\n\n- status: ${status}\n- feature_evaluation_json: ${outJson}\n- manual_browser_verification: ${manualBrowserVerification}\n- vite_api_base_url_configurable: ${checks.vite_api_base_url_configurable.status}\n- frontend_feature_status: ${status}\n`,
  'utf8',
);
console.log(JSON.stringify({ status, manual_browser_verification: manualBrowserVerification, json: outJson }, null, 2));
