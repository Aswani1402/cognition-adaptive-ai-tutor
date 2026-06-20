import {
  AdaptivePathRecommendation,
  AdaptiveSession,
  AssessmentQuestion,
  AuthResult,
  CodeRunOutput,
  CodeSubmitResult,
  ConceptNode,
  DoubtFollowUpResult,
  DoubtRequest,
  DoubtResponse,
  Flashcard,
  LearnerProfile,
  LessonResult,
  MindMap,
  MistakeReview,
  NotebookMemory,
  NotebookSearchResult,
  ProgressData,
  ProgressionResult,
  PuzzleActivity,
  RewardState,
  Subject,
  SubjectSelectionResult,
  TeachingContent,
  XAIReflection,
  DemoRunData,
  RetentionPrediction,
} from './types';
import * as mockData from './mockData';
import { cognitutorProductPacketFixture } from '../fixtures/cognitutorProductPacket';
import { getConceptDisplayName } from './concepts';
import { recordAnswerProgress } from './localProgress';
import { logFrontendEvent } from './eventLog';
import { normalizeNotebookMemory } from './notebookNormalize';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const isDev = import.meta.env.DEV;
const REQUEST_TIMEOUT_MS = 10000;
const selectedSubject = () => localStorage.getItem('active_subject') || '';
const selectedConceptId = () => localStorage.getItem('current_concept_id') || '';
const selectedConceptName = () => localStorage.getItem('current_concept_name') || '';
const selectedDifficulty = () => localStorage.getItem('current_difficulty') || 'easy';
const normalizeViewId = (view?: string) => (view === 'explanation_view' ? 'explanation' : view);
const subjectConceptFallback = (subject: string) => {
  const normalized = subject.toLowerCase();
  if (normalized.includes('sql') || normalized.includes('database')) return { id: 'S1', name: 'Database Basics' };
  if (normalized.includes('html') || normalized.includes('web')) return { id: 'H1', name: 'What is HTML' };
  if (normalized.includes('git')) return { id: 'G1', name: 'Version Control' };
  if (normalized.includes('data')) return { id: 'D1', name: 'Arrays' };
  return { id: 'P1', name: 'Variables' };
};

function cleanConceptTitle(title: string) {
  const clean = String(title || '').replace(/\s+/g, ' ').trim();
  return clean.toLowerCase().startsWith('what is ') ? clean.slice(8).trim() : clean;
}

function sentencePreview(value: unknown, maxChars = 240) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  if (!text) return '';
  const first = text.split(/(?<=[.!?])\s+/).slice(0, 2).join(' ');
  return first.length > maxChars ? `${first.slice(0, maxChars - 3).trim()}...` : first;
}

function subjectFallbackPattern(subject: string, conceptName: string) {
  const normalized = subject.toLowerCase();
  if (normalized.includes('git')) {
    return {
      correct: conceptName.toLowerCase().includes('version control')
        ? 'Version control records changes over time so you can track history, restore earlier versions, and collaborate safely.'
        : `${conceptName} helps manage project history and collaboration in Git.`,
      outputCode: 'Repository state: app.py is modified but not staged.\nCommand: git status',
      output: 'git status shows app.py under changes not staged for commit.',
      debugCode: 'git add .\ngit commit -m "Update app"\ngit push origin wrong-branch',
      debugFix: 'git push origin main',
      codingPrompt: `Write a safe Git command sequence that uses ${conceptName} during a normal project change.`,
    };
  }
  if (normalized.includes('sql') || normalized.includes('database')) {
    return {
      correct: `${conceptName} helps organize or query structured data.`,
      outputCode: 'SELECT name FROM students WHERE active = 1;',
      output: 'Names of active students are returned.',
      debugCode: 'SELEC name FROM students;',
      debugFix: 'SELECT name FROM students;',
      codingPrompt: `Write a short SQL example that demonstrates ${conceptName}.`,
    };
  }
  if (normalized.includes('html') || normalized.includes('web')) {
    return {
      correct: `${conceptName} helps structure content on a web page.`,
      outputCode: '<h1>Hello</h1>',
      output: 'A main heading that displays Hello.',
      debugCode: '<a href="page.html">Open',
      debugFix: '<a href="page.html">Open</a>',
      codingPrompt: `Write a short HTML snippet that demonstrates ${conceptName}.`,
    };
  }
  return {
    correct: `${conceptName} is a rule or pattern used in ${subject || 'the selected subject'}.`,
    outputCode: 'value = 10\nprint(value)',
    output: '10',
    debugCode: '2score = 10\nprint(2score)',
    debugFix: 'score2 = 10\nprint(score2)',
    codingPrompt: `Write a short example that demonstrates ${conceptName}.`,
  };
}

function voiceScriptText(value: unknown): string {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    return String(record.script || '');
  }
  return String(value);
}

function authHeaders() {
  const token = localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export class ApiError extends Error {
  status?: number;
  body?: unknown;

  constructor(message: string, status?: number, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function backendMessage(body: unknown, fallbackMessage: string) {
  if (body && typeof body === 'object') {
    const data = body as Record<string, unknown>;
    const detail = data.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((item) => typeof item === 'object' && item ? String((item as Record<string, unknown>).msg || JSON.stringify(item)) : String(item)).join('; ');
    }
    if (typeof data.reason === 'string') return data.reason;
    if (typeof data.message === 'string') return data.message;
  }
  return fallbackMessage;
}

function unwrapApiResponse<T>(json: unknown, fallback: T): T {
  if (!json || typeof json !== 'object') return fallback;
  if (Array.isArray(json)) return json as T;
  const data = json as Record<string, unknown>;
  if (data.status === 'error') throw new ApiError(backendMessage(data, 'Backend returned an error'), 200, data);
  if ('data' in data) return data.data as T;
  return data as T;
}

function logBackendRequest(url: string) {
  if (isDev) console.log('[API] backend request:', url);
}

function logBackendResponse(path: string, status: number, body: unknown) {
  if (!isDev) return;
  console.log('[API] backend response:', { path, status });
  const message = backendMessage(body, '');
  if (message) console.log('[API] backend error detail:', message);
}

function logMockFallback(reason: unknown) {
  if (isDev) console.log('[API] mock fallback used:', reason);
}

function hasAuthenticatedLearner() {
  const learnerId = localStorage.getItem('learner_id') || '';
  return Boolean(localStorage.getItem('access_token') || learnerId);
}

function currentLearnerId() {
  return localStorage.getItem('learner_id') || '';
}

function mustUseBackend(path: string) {
  return path.startsWith('/auth/');
}

function backendUnavailable(path: string, reason: unknown): Error {
  if (reason instanceof ApiError) return reason;
  const detail = reason instanceof Error ? reason.message : String(reason);
  return new Error(`${API_BASE_URL ? 'Backend unavailable' : 'Backend URL missing'} for ${path}: ${detail}`);
}

function safeFallbackNotice() {
  return 'This content is being prepared. Showing saved learning content instead.';
}

async function parseResponseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function fetchWithTimeout(url: string, init?: RequestInit) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function apiGet<T>(path: string, fallback: T): Promise<T> {
  if (!API_BASE_URL) {
    await delay(180);
    logMockFallback('VITE_API_BASE_URL is missing');
    if (mustUseBackend(path)) throw backendUnavailable(path, 'VITE_API_BASE_URL is missing');
    return fallback;
  }
  const url = `${API_BASE_URL}${path}`;
  logBackendRequest(url);
  try {
    const res = await fetchWithTimeout(url, { headers: authHeaders() });
    const body = await parseResponseBody(res);
    logBackendResponse(path, res.status, body);
    if (!res.ok) throw new ApiError(backendMessage(body, `GET ${path} failed: ${res.status}`), res.status, body);
    return unwrapApiResponse<T>(body, fallback);
  } catch (error) {
    logMockFallback(error);
    console.warn('[api] Falling back to mock data:', error);
    if (mustUseBackend(path)) throw backendUnavailable(path, error);
    return fallback;
  }
}

export async function apiPost<T>(path: string, payload: unknown, fallback: T): Promise<T> {
  if (!API_BASE_URL) {
    await delay(220);
    logMockFallback('VITE_API_BASE_URL is missing');
    if (mustUseBackend(path)) throw backendUnavailable(path, 'VITE_API_BASE_URL is missing');
    return fallback;
  }
  const url = `${API_BASE_URL}${path}`;
  logBackendRequest(url);
  try {
    const res = await fetchWithTimeout(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(payload),
    });
    const body = await parseResponseBody(res);
    logBackendResponse(path, res.status, body);
    if (!res.ok) throw new ApiError(backendMessage(body, `POST ${path} failed: ${res.status}`), res.status, body);
    return unwrapApiResponse<T>(body, fallback);
  } catch (error) {
    logMockFallback(error);
    console.warn('[api] Falling back to mock data:', error);
    if (mustUseBackend(path)) throw backendUnavailable(path, error);
    return fallback;
  }
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export async function getBackendHealth(): Promise<{ connected: boolean; mode: 'backend' | 'missing' | 'error'; detail: string }> {
  if (!API_BASE_URL) {
    await delay(100);
    logMockFallback('VITE_API_BASE_URL is missing');
    return { connected: false, mode: 'missing', detail: 'Live evidence is not available right now. Showing saved learning content.' };
  }

  const url = `${API_BASE_URL}/openapi.json`;
  logBackendRequest(url);
  try {
    const res = await fetchWithTimeout(url, { headers: authHeaders() });
    if (!res.ok) throw new Error(`GET /openapi.json failed: ${res.status}`);
    return { connected: true, mode: 'backend', detail: 'Live backend' };
  } catch (error) {
    logMockFallback(error);
    return { connected: false, mode: 'error', detail: error instanceof Error ? error.message : 'Backend error' };
  }
}

export async function registerUser(payload: unknown): Promise<AuthResult> {
  const raw = payload as Record<string, unknown>;
  return apiPost('/auth/register', {
    name: String(raw.name || raw.full_name || raw.display_name || '').trim(),
    email: String(raw.email || '').trim().toLowerCase(),
    password: String(raw.password || ''),
    goal: String(raw.goal || raw.learning_goal || '').trim(),
    learning_goal: String(raw.learning_goal || raw.goal || '').trim(),
    level: String(raw.level || raw.skill_level || '').trim().toLowerCase(),
    skill_level: String(raw.skill_level || raw.level || '').trim().toLowerCase(),
    preferred_subject: String(raw.preferred_subject || raw.goal || '').trim(),
  }, mockData.mockAuthResult);
}

export async function loginUser(payload: unknown): Promise<AuthResult> {
  const raw = payload as Record<string, unknown>;
  return apiPost('/auth/login', {
    email: String(raw.email || '').trim().toLowerCase(),
    password: String(raw.password || ''),
  }, mockData.mockAuthResult);
}

export function logoutUser(): void {
  ['access_token', 'user_id', 'learner_id', 'app_learner_code', 'user_name', 'user_email', 'active_subject', 'current_concept_id', 'current_concept_name', 'current_difficulty', 'selected_teaching_view'].forEach((key) => localStorage.removeItem(key));
}

export async function getLearnerContext(learnerId: string): Promise<LearnerProfile> {
  const emptyProfile = {
    learner_id: learnerId,
    display_name: localStorage.getItem('user_name') || 'Learner',
    goal: '',
    level: 'beginner',
    preferred_subject: '',
    active_subject: selectedSubject(),
    current_concept_id: selectedConceptId(),
    current_concept_name: selectedConceptName(),
  };
  const data = await apiGet<Record<string, unknown>>(
    `/learner/context/${learnerId}`,
    emptyProfile as unknown as Record<string, unknown>
  );
  const profile = (data.learner_profile || data.profile || data) as Record<string, unknown>;
  const revision = (data.revision_due_summary || {}) as Record<string, unknown>;
  return {
    ...(profile as Partial<LearnerProfile>),
    learnerId: String(data.learnerId || data.learner_id || profile.learner_id || learnerId),
    userId: String(profile.user_id || ''),
    displayName: String(profile.display_name || 'Learner'),
    goal: String(profile.goal || ''),
    level: (profile.level as LearnerProfile['level']) || 'beginner',
    preferredSubject: String(profile.preferred_subject || profile.active_subject || ''),
    currentStreak: 0,
    totalXp: 0,
    activeSubject: String(profile.active_subject || profile.current_domain || ''),
    currentConceptId: String(profile.current_concept_id || ''),
    currentConceptName: String(profile.current_concept_name || ''),
    returningRevisionNeeded: Boolean(data.returning_revision_needed || Number(revision.due_count || 0) > 0),
    guideMessage: String(data.guide_message || 'Hi, I am Cogni. I will guide your next learning step.'),
  };
}

export async function selectSubject(learnerId: string, subject: string): Promise<SubjectSelectionResult> {
  const first = subjectConceptFallback(subject);
  const fallback = {
    status: 'success',
    auto_flow: true,
    active_subject: subject,
    current_concept_id: first.id,
    current_concept_name: first.name,
    current_difficulty: 'easy',
    next_route: `/lesson/${first.id}`,
    guide_message: `Great choice! I'll start from the first ${subject} concept for you.`,
    backend_connected: false,
  };
  return apiPost('/learner/select-subject', { learner_id: learnerId, subject }, fallback);
}

export async function getSubjectProgress(learnerId: string): Promise<Record<string, unknown>> {
  return apiGet(`/learner/subject-progress/${learnerId}`, { learner_id: learnerId, subjects: [] });
}

export async function getSubjects(): Promise<Subject[]> {
  const data = await apiGet<Subject[] | { subjects?: Subject[] }>('/subjects', mockData.mockSubjects);
  return Array.isArray(data) ? data : data.subjects || mockData.mockSubjects;
}

export async function getLearningPath(learnerIdOrSubject: string, subjectArg?: string): Promise<ConceptNode[]> {
  const learnerId = subjectArg ? learnerIdOrSubject : currentLearnerId();
  const subjectId = subjectArg || learnerIdOrSubject || selectedSubject() || 'Selected Subject';
  const fallback = mockData.mockLearningPath
    .filter((node) => node.subjectId === subjectId)
    .map((node) => ({ ...node, name: getConceptDisplayName(node.id, node.name) }));
  const data = await apiGet<ConceptNode[] | { path?: ConceptNode[]; nodes?: ConceptNode[] }>(
    `/path/${learnerId}/${encodeURIComponent(subjectId)}`,
    fallback.length ? fallback : mockData.mockLearningPath.map((node) => ({ ...node, subjectId, name: getConceptDisplayName(node.id, node.name) }))
  );
  const nodes = Array.isArray(data) ? data : data.path || data.nodes || fallback;
  return nodes.map((node) => ({ ...node, name: getConceptDisplayName(node.id, node.name) }));
}

export async function getAdaptiveSession(learnerId: string): Promise<AdaptiveSession> {
  return apiGet(`/tutor/adaptive-session/${learnerId}`, {
    learner_id: learnerId,
    auto_flow: true,
    guide_message: 'Let’s learn this concept first.',
    current_activity: { type: 'teaching', frontend_component: 'SelectedTeachingViewRenderer', payload: {} },
    next_recommended_activity: { type: 'assessment', label: 'Try a quick check', reason: 'Check understanding after teaching' },
    backend_connected: false,
  });
}

function lessonFallback(conceptId: string, view?: string, reason = safeFallbackNotice()): TeachingContent {
  const subject = selectedSubject();
  const first = subjectConceptFallback(subject);
  const conceptName = getConceptDisplayName(conceptId, selectedConceptName() || (conceptId === first.id ? first.name : ''));
  const selectedView = normalizeViewId(view) || normalizeViewId(mockData.mockLesson.selectedView) || 'explanation';
  const fallback: TeachingContent = {
    ...mockData.mockLesson,
    conceptId,
    conceptName,
    selectedView,
    requestedView: view,
    backendConnected: false,
    mockFallbackUsed: true,
    backendStatusReason: reason,
    fallbackViewNames: [
      'explanation',
      'definition_view',
      'simple_example_view',
      'step_by_step_view',
      'analogy_view',
      'code_view',
      'misconception_view',
      'debug_view',
      'output_prediction_view',
      'transfer_view',
      'challenge_view',
      'revision_view',
      'flashcard_view',
      'mindmap_view',
      'voice_script_view',
    ],
  };

  const viewText: Record<string, Partial<TeachingContent>> = {
    definition_view: {
      adaptiveExplanation: `${fallback.conceptName} is the current ${subject || 'selected subject'} concept. Start with its meaning, then connect it to one example.`,
      workedExample: subject.toLowerCase().includes('sql') ? 'SELECT name FROM students;' : `${fallback.conceptName}: one small example`,
    },
    simple_example_view: {
      adaptiveExplanation: `Use one small ${fallback.conceptName} example before adding complexity.`,
      workedExample: subject.toLowerCase().includes('sql') ? 'SELECT * FROM students;' : `${fallback.conceptName} example`,
    },
    step_by_step_view: {
      adaptiveExplanation: `First define ${fallback.conceptName}, then inspect an example, then try a short check.`,
      workedExample: subject.toLowerCase().includes('sql') ? '1. Choose columns. 2. Name the table. 3. Add filters if needed.' : `1. Define ${fallback.conceptName}. 2. Try an example.`,
    },
    code_view: {
      adaptiveExplanation: `${fallback.conceptName} becomes clearer when the example and result are shown together.`,
      workedExample: subject.toLowerCase().includes('sql') ? 'SELECT name FROM students WHERE age > 18;' : `${fallback.conceptName} practice snippet`,
    },
    analogy_view: {
      adaptiveExplanation: `${fallback.conceptName} is a building block inside ${subject || 'this subject'} work.`,
      workedExample: `${fallback.conceptName} helps solve one practical task.`,
    },
    misconception_view: {
      adaptiveExplanation: `Common mistake: using ${fallback.conceptName} syntax without checking what it means.`,
      workedExample: `Review the meaning of ${fallback.conceptName} before answering.`,
    },
    debug_view: {
      adaptiveExplanation: `Debug ${fallback.conceptName} by finding the wrong assumption before changing code or syntax.`,
      workedExample: `Find the issue in a small ${fallback.conceptName} example, then explain the fix.`,
    },
    output_prediction_view: {
      adaptiveExplanation: `Predict the result of a small ${fallback.conceptName} example before checking the answer.`,
      workedExample: `Trace one ${fallback.conceptName} example and write the expected output.`,
    },
    transfer_view: {
      adaptiveExplanation: `Apply ${fallback.conceptName} in a slightly different ${subject || 'subject'} situation.`,
      workedExample: `Transfer the same idea to a new but related task.`,
    },
    challenge_view: {
      adaptiveExplanation: `Use ${fallback.conceptName} in a harder task that combines definition, example, and reasoning.`,
      workedExample: `Solve a multi-step ${fallback.conceptName} challenge.`,
    },
    revision_view: {
      adaptiveExplanation: `Review the key rule for ${fallback.conceptName}, then test it with one quick check.`,
      workedExample: `Revision prompt: explain ${fallback.conceptName} in one sentence.`,
    },
    flashcard_view: {
      adaptiveExplanation: `Use flashcards to recall the definition, example, and common mistake for ${fallback.conceptName}.`,
      workedExample: `Front: What is ${fallback.conceptName}? Back: Give the core rule and one example.`,
    },
    mindmap_view: {
      adaptiveExplanation: `Connect ${fallback.conceptName} to its definition, examples, mistakes, and next practice task.`,
      workedExample: `Center: ${fallback.conceptName}; branches: definition, example, mistake, practice.`,
    },
    voice_script_view: {
      adaptiveExplanation: `Voice overview for ${fallback.conceptName}: explain the idea, give one example, then ask a quick check.`,
      workedExample: `Listen for the main rule, then repeat it with your own example.`,
    },
  };

  return { ...fallback, ...viewText[selectedView] };
}

function normalizeLessonPayload(data: Record<string, unknown>, conceptId: string, requestedView?: string): TeachingContent {
  const frontendResponse = (data.frontend_response || {}) as Record<string, unknown>;
  const teaching = (data.teaching || frontendResponse.teaching || {}) as Record<string, unknown>;
  const resources = (data.concept_resources || data.resources || teaching.concept_resources || {}) as Record<string, unknown>;
  const teachingContent = (data.teaching_content || data.teachingContent || teaching.teaching_content || teaching.content || resources) as TeachingContent['teachingContent'];
  const selectedView = normalizeViewId(String(data.selected_view || data.selectedView || teaching.selected_view || requestedView || mockData.mockLesson.selectedView)) || 'explanation';
  const fallbackViews = data.fallback_views || data.fallbackViewNames || data.available_views || teaching.available_views;
  const contentByView = (data.content_by_view || data.contentByView || teaching.content_by_view || {}) as TeachingContent['contentByView'];
  const examples = Array.isArray(teachingContent?.examples) ? teachingContent.examples.map(String) : [];
  const keyPoints = Array.isArray(teachingContent?.key_points) ? teachingContent.key_points.map(String) : Array.isArray(data.keyPoints) ? data.keyPoints.map(String) : Array.isArray(resources.key_points) ? (resources.key_points as unknown[]).map(String) : mockData.mockLesson.keyPoints;
  const commonMistakes = Array.isArray(teachingContent?.common_mistakes) ? teachingContent.common_mistakes.map(String) : Array.isArray(data.commonMistakes) ? data.commonMistakes.map(String) : Array.isArray(resources.common_mistakes) ? (resources.common_mistakes as unknown[]).map(String) : mockData.mockLesson.commonMistakes;

  const normalizedSubject = String(data.subject || selectedSubject());
  const activeSubject = selectedSubject();
  if (activeSubject && normalizedSubject && activeSubject.toLowerCase() !== normalizedSubject.toLowerCase()) {
    throw new Error(`Subject mismatch: active subject is ${activeSubject}, backend returned ${normalizedSubject}`);
  }
  return {
    conceptId: String(data.concept_id || data.conceptId || conceptId),
    conceptName: getConceptDisplayName(conceptId, String(data.concept_name || data.conceptName || teachingContent?.title || '')),
    difficulty: (data.difficulty as TeachingContent['difficulty']) || selectedDifficulty() as TeachingContent['difficulty'],
    explanationMode: String(data.explanation_mode || data.explanationMode || 'adaptive'),
    selectedView,
    requestedView: normalizeViewId(String(data.requested_view || requestedView || selectedView)),
    adaptiveExplanation: String(teachingContent?.beginner_explanation || teachingContent?.explanation || teachingContent?.concept_intro || data.adaptiveExplanation || data.adaptive_explanation || resources.explanation || ''),
    fallbackViewNames: Array.isArray(fallbackViews) ? fallbackViews.map((view) => normalizeViewId(String(view)) || String(view)) : [],
    keyPoints,
    commonMistakes,
    workedExample: String(teachingContent?.code_or_task_example || teachingContent?.code || teachingContent?.syntax || teachingContent?.example || examples[0] || data.workedExample || data.worked_example || resources.example || ''),
    whySelected: String((data.teaching_strategy as Record<string, unknown> | undefined)?.reason || (data.xai as Record<string, unknown> | undefined)?.reason || data.reason || data.whySelected || data.why_selected || ''),
    nextActivity: String(data.nextActivity || data.next_activity || 'quiz'),
    subject: normalizedSubject,
    difficultyProgress: data.difficulty_progress as TeachingContent['difficultyProgress'],
    teachingContent: {
      ...teachingContent,
      key_points: keyPoints,
      common_mistakes: commonMistakes,
      examples,
    },
    contentByView,
    ragEvidence: (data.rag_evidence || data.rag || frontendResponse.rag_evidence) as Record<string, unknown> | undefined,
    teachingStrategy: (data.teaching_strategy || frontendResponse.teaching_strategy) as Record<string, unknown> | undefined,
    xai: (data.xai || data.xai_reason || frontendResponse.xai) as Record<string, unknown> | undefined,
    generationStatus: String(data.generation_status || data.status || ''),
    voiceScript: voiceScriptText(data.voice_script || data.teaching_voice_script),
    backendConnected: true,
    mockFallbackUsed: Boolean(data.fallback_used),
    backendStatusReason: data.reason ? String(data.reason) : 'Backend connected',
  };
}

export async function getLesson(
  learnerIdOrConceptId: string,
  conceptIdOrOptions?: string | { view?: string; learnerId?: string; difficulty?: string; subject?: string },
  maybeOptions?: { view?: string; learnerId?: string; difficulty?: string; subject?: string }
): Promise<TeachingContent> {
  const conceptId = typeof conceptIdOrOptions === 'string' ? conceptIdOrOptions : learnerIdOrConceptId;
  const options = typeof conceptIdOrOptions === 'string' ? maybeOptions : conceptIdOrOptions;
  const learnerId = options?.learnerId || currentLearnerId();
  const subject = options?.subject || selectedSubject();
  const params = new URLSearchParams();
  if (options?.view) params.set('view', options.view);
  if (options?.difficulty) params.set('difficulty', options.difficulty);
  if (subject) params.set('subject', subject);
  const query = params.toString() ? `?${params.toString()}` : '';
  const path = `/lesson/${learnerId}/${conceptId}${query}`;

  if (!API_BASE_URL) {
    await delay(180);
    logMockFallback('VITE_API_BASE_URL is missing');
    return lessonFallback(conceptId, options?.view, 'VITE_API_BASE_URL is missing');
  }

  const url = `${API_BASE_URL}${path}`;
  logBackendRequest(url);
  try {
    const res = await fetchWithTimeout(url, { headers: authHeaders() });
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    const data = unwrapApiResponse<Record<string, unknown>>(await res.json(), {});
    return normalizeLessonPayload(data, conceptId, options?.view);
  } catch (lessonError) {
    logMockFallback(lessonError);
    const sessionPath = `/tutor/adaptive-session/${learnerId}`;
    const sessionUrl = `${API_BASE_URL}${sessionPath}`;
    logBackendRequest(sessionUrl);
    try {
      const res = await fetchWithTimeout(sessionUrl, { headers: authHeaders() });
      if (!res.ok) throw new Error(`GET ${sessionPath} failed: ${res.status}`);
      const data = unwrapApiResponse<Record<string, unknown>>(await res.json(), {});
      const teaching = (data.teaching || data) as Record<string, unknown>;
      return normalizeLessonPayload({ ...teaching, selected_view: options?.view || teaching.selected_view }, conceptId, options?.view);
    } catch (sessionError) {
      logMockFallback(sessionError);
      return lessonFallback(conceptId, options?.view, `${lessonError instanceof Error ? lessonError.message : 'Lesson request failed'}; adaptive-session fallback failed`);
    }
  }
}

export async function getAssessment(
  learnerIdOrConceptId: string,
  conceptIdOrOptions?: string | { difficulty?: string; subject?: string },
  maybeOptions?: { difficulty?: string; subject?: string }
): Promise<AssessmentQuestion[]> {
  const learnerId = typeof conceptIdOrOptions === 'string' ? learnerIdOrConceptId : currentLearnerId();
  const conceptId = typeof conceptIdOrOptions === 'string' ? conceptIdOrOptions : learnerIdOrConceptId;
  const options = typeof conceptIdOrOptions === 'string' ? maybeOptions : conceptIdOrOptions;
  const params = new URLSearchParams();
  if (options?.difficulty) params.set('difficulty', options.difficulty);
  if (options?.subject || selectedSubject()) params.set('subject', options?.subject || selectedSubject());
  const query = params.toString() ? `?${params.toString()}` : '';
  const subj = options?.subject || selectedSubject();
  const first = subjectConceptFallback(subj);
  const conceptName = selectedConceptName() || first.name;
  const pattern = subjectFallbackPattern(subj, cleanConceptTitle(conceptName));
  const assessmentTypes = ['mcq', 'debug_task', 'output_prediction', 'transfer_question', 'challenge_question', 'explanation_check', 'syntax_completion', 'coding_prompt', 'code_reasoning_task', 'fill_in_the_blank', 'true_or_false', 'practice_question', 'transfer_task', 'real_world_application_question', 'debug_challenge', 'output_prediction_challenge', 'multi_step_challenge'];
  const assessmentFallback: AssessmentQuestion[] = assessmentTypes.map((type, index) => ({
    questionId: `${conceptId}-fallback-${type}`,
    taskType: type,
    questionType: type,
    difficulty: index < 4 ? 'easy' : index < 10 ? 'medium' : 'hard',
    prompt: type === 'real_world_application_question' ? `Scenario: A team is using ${cleanConceptTitle(conceptName)} in a real ${subj || 'subject'} task. How does it help?` : type === 'fill_in_the_blank' ? `Fill in the blank: ${cleanConceptTitle(conceptName)} means ____.` : type === 'true_or_false' ? `${cleanConceptTitle(conceptName)} should be understood through examples and feedback.` : type === 'coding_prompt' ? pattern.codingPrompt : `Practice ${cleanConceptTitle(conceptName)} with ${type.replaceAll('_', ' ')}.`,
    options: type === 'mcq' ? [pattern.correct, `It is unrelated to ${subj || 'this subject'}.`, 'It should be memorized without examples.', 'It only matters after work is finished.'] : type === 'true_or_false' ? ['True', 'False'] : undefined,
    correctAnswer: type === 'true_or_false' ? 'True' : type === 'mcq' ? pattern.correct : type.includes('debug') ? pattern.debugFix : type.includes('output') ? pattern.output : cleanConceptTitle(conceptName),
    code: type.includes('output') ? pattern.outputCode : undefined,
    buggyCode: type.includes('debug') ? pattern.debugCode : undefined,
    expectedOutput: type.includes('output') ? pattern.output : undefined,
    blanks: type === 'fill_in_the_blank' ? [{ id: 'answer', label: 'Meaning', answer: conceptName }] : undefined,
    hint: `Use the current ${conceptName} packet.`,
    sourceConcept: conceptId,
    subject: subj,
    concept_name: conceptName,
  }));
  const data = await apiGet<AssessmentQuestion[] | { questions?: AssessmentQuestion[]; assessment?: AssessmentQuestion[]; assessment_bank?: AssessmentQuestion[] }>(
    `/assessment/${learnerId}/${conceptId}${query}`,
    assessmentFallback
  );
  const rawQuestions = Array.isArray(data) ? data : data.questions || data.assessment || data.assessment_bank || assessmentFallback;
  const seen = new Set<string>();
  return rawQuestions.map((item, index) => normalizeQuestion(item, conceptId, subj, index)).filter((item) => {
    if (seen.has(item.questionId)) return false;
    seen.add(item.questionId);
    return true;
  });
}

function normalizeQuestion(item: AssessmentQuestion | Record<string, unknown>, conceptId: string, subject: string, index: number): AssessmentQuestion {
  const q = item as Record<string, unknown>;
  const rawComponent = String(q.frontendComponent || q.frontend_component || q.component || '');
  const questionType = canonicalQuestionType(String(q.taskType || q.task_type || q.questionType || q.question_type || q.type || ''), rawComponent);
  const options = normalizeQuestionOptions(q, questionType);
  const correctAnswer = normalizeCorrectAnswer(q, options);
  const prompt = String(q.prompt || q.question || q.question_text || fallbackPrompt(questionType, conceptId, subject));
  return {
    ...(item as AssessmentQuestion),
    questionId: String(q.questionId || q.question_id || q.id || `${conceptId}-${questionType}-${index}`),
    taskType: questionType,
    questionType,
    difficulty: (q.difficulty as AssessmentQuestion['difficulty']) || (selectedDifficulty() as AssessmentQuestion['difficulty']),
    prompt,
    title: q.title ? String(q.title) : undefined,
    instructions: q.instructions ? String(q.instructions) : q.instruction ? String(q.instruction) : fallbackInstruction(questionType),
    instruction: q.instruction ? String(q.instruction) : q.instructions ? String(q.instructions) : fallbackInstruction(questionType),
    constraints: Array.isArray(q.constraints) ? q.constraints.map(String) : undefined,
    expected_answer: q.expected_answer,
    expected_idea: q.expected_idea || q.expected_answer || q.correct_answer,
    rubric: q.rubric,
    evaluation_mode: q.evaluation_mode ? String(q.evaluation_mode) : undefined,
    generated_source: q.generated_source ? String(q.generated_source) : undefined,
    grounding_source_label: q.grounding_source_label ? String(q.grounding_source_label) : undefined,
    frontend_component: normalizeFrontendComponent(q, questionType),
    frontendComponent: normalizeFrontendComponent(q, questionType),
    puzzle_type: q.puzzle_type ? String(q.puzzle_type) : undefined,
    correct_order: Array.isArray(q.correct_order) ? q.correct_order.map(String) : undefined,
    code: q.code ? String(q.code) : q.code_snippet ? String(q.code_snippet) : undefined,
    code_snippet: q.code_snippet ? String(q.code_snippet) : q.code ? String(q.code) : undefined,
    starterCode: q.starterCode ? String(q.starterCode) : q.starter_code ? String(q.starter_code) : undefined,
    buggyCode: q.buggyCode ? String(q.buggyCode) : q.buggy_code ? String(q.buggy_code) : undefined,
    expectedOutput: q.expectedOutput ? String(q.expectedOutput) : q.expected_output ? String(q.expected_output) : undefined,
    options: questionType === 'mcq' && (!options || options.length < 4) ? fallbackOptions(q, correctAnswer) : options,
    correctAnswer,
    hint: q.hint ? String(q.hint).split(/(?<=[.!?])\s+/).slice(0, 2).join(' ') : undefined,
    hidden_hint: q.hidden_hint ? String(q.hidden_hint) : q.hint ? String(q.hint) : undefined,
    sourceConcept: String(q.sourceConcept || q.source_concept || q.concept_id || conceptId),
    concept_id: String(q.concept_id || conceptId),
    concept_name: getConceptDisplayName(String(q.concept_id || conceptId), String(q.concept_name || selectedConceptName())),
    subject: String(q.subject || subject),
  };
}

function fallbackPrompt(questionType: string, conceptId: string, subject: string) {
  const concept = getConceptDisplayName(conceptId, selectedConceptName());
  if (questionType === 'output_prediction') return `What is the output of this ${subject || 'subject'} snippet?`;
  if (questionType === 'debug_task') return `Find and fix the bug in this ${concept} task.`;
  if (questionType === 'syntax_completion') return `Complete the missing syntax for ${concept}.`;
  if (questionType === 'transfer_question') return `Use ${concept} in a concrete real-world situation and explain why it is useful.`;
  if (questionType === 'challenge_question') return `Solve a multi-step ${concept} challenge and explain the reasoning.`;
  if (questionType === 'puzzle') return `Puzzle: order or match the steps for ${concept}.`;
  return `Answer this ${concept} question.`;
}

function fallbackInstruction(questionType: string) {
  if (questionType === 'mcq') return 'Choose one option.';
  if (questionType === 'output_prediction') return 'Write only the exact output.';
  if (questionType === 'debug_task') return 'Fix the code and briefly name the issue.';
  if (questionType === 'coding_prompt') return 'Write code that satisfies every requirement.';
  if (questionType === 'transfer_question') return 'Include the scenario answer and a short explanation.';
  return 'Answer clearly and specifically.';
}

function fallbackOptions(q: Record<string, unknown>, correctAnswer?: string) {
  const correct = correctAnswer || String(q.expected_answer || q.correct_answer || 'The concept stores or organizes information.');
  return [
    correct,
    'It is unrelated to the current concept.',
    'It should be memorized without using examples.',
    'It only matters after the topic is finished.',
  ].slice(0, 4);
}

function canonicalQuestionType(rawType: string, frontendComponent?: string) {
  const raw = String(rawType || '').toLowerCase();
  const component = String(frontendComponent || '').toLowerCase();
  if (component === 'mcqquestioncard' || raw === 'mcq' || raw === 'multiple_choice') return 'mcq';
  if (component === 'debugquestioncard' || raw === 'debug' || raw === 'debug_task') return 'debug_task';
  if (component === 'outputpredictioncard' || raw === 'output_prediction') return 'output_prediction';
  if (component === 'syntaxcompletioncard' || raw === 'syntax' || raw === 'syntax_completion') return 'syntax_completion';
  if (component === 'codewritingcard' || raw === 'code_writing' || raw === 'coding_question' || raw === 'coding_prompt') return 'coding_prompt';
  if (component === 'fillblankcard' || raw === 'fill_blank' || raw === 'fill_in_the_blank') return 'fill_in_the_blank';
  if (component === 'transferquestioncard' || raw === 'transfer') return 'transfer_question';
  if (component === 'challengequestioncard' || raw === 'challenge') return 'challenge_question';
  if (component === 'puzzlequestioncard' || raw === 'code_puzzle' || raw === 'arrange_steps' || raw === 'drag_order') return 'puzzle';
  if (raw === 'true_false') return 'true_or_false';
  return raw || 'practice_question';
}

function normalizeFrontendComponent(q: Record<string, unknown>, questionType: string) {
  const explicit = q.frontendComponent || q.frontend_component || q.component;
  if (explicit) return String(explicit);
  const map: Record<string, string> = {
    mcq: 'MCQQuestionCard',
    true_or_false: 'MCQQuestionCard',
    debug_task: 'DebugQuestionCard',
    debug_challenge: 'DebugQuestionCard',
    output_prediction: 'OutputPredictionCard',
    output_prediction_challenge: 'OutputPredictionCard',
    syntax_completion: 'SyntaxCompletionCard',
    coding_prompt: 'CodeWritingCard',
    coding_question: 'CodeWritingCard',
    code_reasoning_task: 'CodeWritingCard',
    fill_in_the_blank: 'FillBlankCard',
    transfer_question: 'TransferQuestionCard',
    transfer_task: 'TransferQuestionCard',
    real_world_application_question: 'TransferQuestionCard',
    challenge_question: 'ChallengeQuestionCard',
    multi_step_challenge: 'ChallengeQuestionCard',
    puzzle: 'PuzzleQuestionCard',
  };
  return map[questionType] || 'GenericQuestionCard';
}

function normalizeQuestionOptions(q: Record<string, unknown>, questionType: string) {
  const raw = q.options || q.choices || q.answer_options || q.mcq_options;
  if (questionType === 'true_or_false') return ['True', 'False'];
  if (!Array.isArray(raw)) return undefined;
  return raw
    .map((option) => {
      if (typeof option === 'object' && option) {
        const record = option as Record<string, unknown>;
        return String(record.text || record.label || record.value || record.option || record.id || '');
      }
      return String(option);
    })
    .map((option) => option.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
    .map((option) => option.length > 180 ? `${option.slice(0, 179).trim()}...` : option);
}

function normalizeCorrectAnswer(q: Record<string, unknown>, options?: string[]) {
  const explicit = q.correctAnswer ?? q.correct_answer ?? q.answer ?? q.expected_answer ?? q.correct_option ?? q.correct_option_id ?? q.correct_option_index;
  if (explicit === undefined || explicit === null) return undefined;
  if (typeof explicit === 'number' && options?.[explicit]) return options[explicit];
  if (typeof explicit === 'string' && /^\d+$/.test(explicit) && options?.[Number(explicit)]) return options[Number(explicit)];
  if (typeof explicit === 'object') {
    const record = explicit as Record<string, unknown>;
    return String(record.answer || record.text || record.value || JSON.stringify(record));
  }
  const text = String(explicit).replace(/\s+/g, ' ').trim();
  if (options?.length) {
    const matching = options.find((option) => option === text || text.includes(option) || option.includes(text));
    if (matching) return matching;
    if (text.length > 180) return options[0];
  }
  return text;
}

export async function submitAnswer(payload: unknown): Promise<CodeSubmitResult> {
  const raw = payload as Record<string, unknown>;
  const normalized = {
    learner_id: currentLearnerId() || raw.learnerId,
    concept_id: raw.conceptId || raw.concept_id,
    concept_name: raw.conceptName || raw.concept_name,
    subject: raw.subject || selectedSubject(),
    domain: raw.domain || raw.subject || selectedSubject(),
    difficulty: raw.difficulty || selectedDifficulty(),
    question_id: raw.questionId || raw.question_id,
    question_type: raw.questionType || raw.taskType || 'mcq',
    task_type: raw.taskType || raw.questionType || 'mcq',
    answer: raw.answer ?? raw.learnerAnswer ?? '',
    question: raw.question || raw,
    confidence: raw.confidence ?? 0.5,
    time_taken_sec: raw.time_taken_sec ?? 0,
    time_taken: raw.time_taken ?? raw.time_taken_sec ?? 0,
    hint_used: raw.hint_used ?? false,
    hint_count: raw.hint_count ?? 0,
    option_change_count: raw.option_change_count ?? 0,
    option_changes: raw.option_changes ?? raw.option_change_count ?? 0,
    answer_change_count: raw.answer_change_count ?? 0,
    answer_changes: raw.answer_changes ?? raw.answer_change_count ?? 0,
    run_code_count: raw.run_code_count ?? 0,
    code_runs: raw.code_runs ?? raw.run_code_count ?? 0,
    attempt_count: raw.attempt_count ?? 1,
    attempts: raw.attempts ?? raw.attempt_count ?? 1,
    wrong_attempt_count: raw.wrong_attempt_count ?? 0,
  };
  if (isDev) console.log('[submitAnswer payload]', normalized);
  logFrontendEvent({ action: 'answer_submitted', module: 'assessment', status: 'started', summary: String(normalized.question_type) });
  const data = await apiPost<Record<string, unknown>>(
    '/answer/submit',
    normalized,
    mockData.mockSubmitResult as unknown as Record<string, unknown>
  );
  const score = Number(data.score ?? mockData.mockSubmitResult.score);
  const correct = Boolean(data.correct ?? data.is_correct ?? score >= 0.8);
  const positiveMascot = 'Great answer. You understood this concept correctly. Let’s move to the next level.';
  const result = {
    ...mockData.mockSubmitResult,
    ...data,
    correct,
    score,
    feedback: String(data.feedback || (correct ? 'Correct. You understood this concept.' : mockData.mockSubmitResult.feedback)),
    correct_answer: data.correct_answer ? String(data.correct_answer) : data.answer_key ? String(data.answer_key) : undefined,
    learner_answer: raw.answer !== undefined ? String(raw.answer) : undefined,
    explanation: data.explanation ? String(data.explanation) : undefined,
    feedback_type: data.feedback_type ? String(data.feedback_type) : undefined,
    source: data.source ? String(data.source) : undefined,
    generation_source: data.generation_source ? String(data.generation_source) : undefined,
    mascot_script: correct || score >= 0.8 ? positiveMascot : String(data.mascot_script || data.voice_script || 'That answer needs one fix. Review the key idea, then try a similar question.'),
    recommended_teaching_view: data.recommended_teaching_view ? String(data.recommended_teaching_view) : data.recommended_view ? String(data.recommended_view) : undefined,
    recommended_next_activity: (data.recommended_next_activity || data.next_recommended_activity || data.next_activity) as CodeSubmitResult['recommended_next_activity'],
    runOutput: { stdout: '', stderr: '', errorType: null, errorMessage: null, timedOut: false, blocked: false },
  } as CodeSubmitResult;
  recordAnswerProgress(result, String(normalized.concept_id || 'current'));
  logFrontendEvent({ action: 'answer_submitted', module: 'assessment', status: correct ? 'correct' : 'needs_review', summary: `score ${score}` });
  return result;
}

export async function getSimilarQuestion(payload: Record<string, unknown>): Promise<AssessmentQuestion | null> {
  const learnerId = String(payload.learner_id || payload.learnerId || currentLearnerId());
  const conceptId = String(payload.concept_id || payload.conceptId || selectedConceptId());
  const data = await apiPost<Record<string, unknown>>('/question/similar', {
    learner_id: learnerId,
    concept_id: conceptId,
    concept_name: payload.concept_name || selectedConceptName(),
    subject: payload.subject || selectedSubject(),
    difficulty: payload.difficulty || selectedDifficulty(),
    exclude_question_ids: payload.exclude_question_ids || payload.excludeQuestionIds || [],
    previous_question_id: payload.previous_question_id || payload.question_id,
    question_type: payload.question_type,
  }, {});
  const question = (data.question || data.similar_question || data) as Record<string, unknown>;
  return Object.keys(question).length ? normalizeQuestion(question, conceptId, String(payload.subject || selectedSubject()), 0) : null;
}

export async function runCode(payload: unknown): Promise<CodeRunOutput> {
  logFrontendEvent({ action: 'code_run', module: 'code_console', status: 'started', summary: 'Learner ran code' });
  const data = await apiPost<Record<string, unknown>>(
    '/code/run',
    payload,
    mockData.mockRunOutput as unknown as Record<string, unknown>
  );
  return {
    status: data.status === 'error' ? 'error' : 'success',
    runOutput: {
      stdout: String(data.stdout ?? (data.runner_output as Record<string, unknown> | undefined)?.stdout ?? ''),
      stderr: String(data.stderr || (data.runner_output as Record<string, unknown> | undefined)?.stderr || ''),
      blocked: Boolean(data.safety_error || (data.runner_output as Record<string, unknown> | undefined)?.blocked_reason),
      timedOut: Boolean((data.runner_output as Record<string, unknown> | undefined)?.timed_out),
      errorType: data.safety_error ? 'safety_error' : null,
      errorMessage: data.safety_error ? String(data.safety_error) : null,
    },
  };
}

export async function getHint(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  logFrontendEvent({ action: 'hint_requested', module: 'hint', status: 'started', summary: String(payload.question_type || payload.question_id || 'hint') });
  return apiPost('/hint/predict', {
    learner_id: currentLearnerId(),
    subject: selectedSubject(),
    concept_id: selectedConceptId(),
    concept_name: selectedConceptName(),
    difficulty: selectedDifficulty(),
    ...payload,
  }, {
    status: 'success',
    hint_type: 'guided_hint',
    hint_level: Number(payload.hint_count || 0) + 1,
    hint_text: 'Review the key idea for this concept, then try one smaller step.',
    reveal_answer: false,
    next_hint_available: true,
  });
}

export async function askDoubt(payload: DoubtRequest): Promise<DoubtResponse> {
  logFrontendEvent({ action: 'doubt_asked', module: 'doubt', status: 'started', summary: payload.doubtText.slice(0, 120) });
  const normalized = {
    learner_id: payload.learnerId,
    doubt_text: payload.doubtText,
    subject: payload.domain,
    concept_id: payload.currentConceptId,
    concept_name: payload.currentConceptName,
    domain: payload.domain,
    current_teaching_view: payload.currentTeachingView,
    difficulty: payload.difficulty,
  };
  const data = await apiPost<Record<string, unknown>>(
    '/doubt/ask',
    normalized,
    { ...mockData.mockDoubtResponse, doubtText: payload.doubtText } as unknown as Record<string, unknown>
  );
  const rawExample = data.example;
  const normalizedExample = rawExample && typeof rawExample === 'object'
    ? rawExample as DoubtResponse['example']
    : rawExample
      ? { title: `${payload.currentConceptName} example`, code: String(rawExample), explanation: String(data.answer || '') }
      : undefined;
  const rawFollowUp = data.follow_up_check as Record<string, unknown> | undefined;
  const normalizedFollowUp = rawFollowUp?.question && typeof rawFollowUp.question === 'object'
    ? {
        questionType: String(rawFollowUp.question_type || 'explanation_check'),
        question: String((rawFollowUp.question as Record<string, unknown>).question || 'Explain the idea in your own words.'),
        correctAnswer: String((rawFollowUp.answer_key as Record<string, unknown> | undefined)?.answer || (rawFollowUp.question as Record<string, unknown>).answer || ''),
      }
    : data.follow_up_check as DoubtResponse['followUpCheck'];
  return {
    ...mockData.mockDoubtResponse,
    status: String(data.status || 'success'),
    learnerId: payload.learnerId,
    doubtText: payload.doubtText,
    doubtType: String(data.intent || 'concept_doubt'),
    conceptId: payload.currentConceptId,
    conceptName: payload.currentConceptName,
    domain: payload.domain,
    ragGrounded: Boolean((data.rag_grounding as Record<string, unknown> | undefined)?.rag_grounded),
    answer: String(data.answer || mockData.mockDoubtResponse.answer),
    example: normalizedExample,
    sourceSectionsUsed: ((data.rag_grounding as Record<string, unknown> | undefined)?.source_sections as string[] | undefined) || [],
    retrievedContextSummary: Array.isArray((data.rag_grounding as Record<string, unknown> | undefined)?.source_sections)
      ? `Grounded in ${((data.rag_grounding as Record<string, unknown>).source_sections as string[]).join(', ')}.`
      : String(data.retrieved_context_summary || 'Grounded in the current concept resources.'),
    voiceScript: voiceScriptText(data.voice_script || data.doubt_explanation_voice_script),
    followUpCheck: normalizedFollowUp,
    memoryUpdateSuggestion: {
      weakConcept: payload.currentConceptName,
      weakQuestionType: payload.currentTeachingView || 'concept_doubt',
      mistakeType: String(data.doubt_type || data.intent || 'doubt'),
    },
  };
}

export async function submitDoubtFollowUp(payload: unknown): Promise<DoubtFollowUpResult> {
  return apiPost('/doubt/followup', payload, mockData.mockDoubtFollowUpResult);
}

export async function getNotebook(learnerId: string): Promise<NotebookMemory> {
  const data = await apiGet(`/notebook/${learnerId}`, mockData.mockNotebook);
  return normalizeNotebookMemory(data);
}

export async function saveNotebookNote(payload: Record<string, unknown>): Promise<{ saved: boolean; already_saved?: boolean; note_id?: string | number; status?: string; error?: string }> {
  const data = await apiPost<Record<string, unknown>>('/notebook/save', {
    learner_id: currentLearnerId() || payload.learner_id || payload.learnerId,
    subject: payload.subject || selectedSubject(),
    concept_id: payload.concept_id || payload.conceptId || selectedConceptId(),
    concept_name: payload.concept_name || payload.conceptName || selectedConceptName(),
    note_type: payload.note_type || payload.noteType || 'saved_note',
    title: payload.title || 'Saved note',
    content: payload.content || '',
    source_page: payload.source_page || payload.sourcePage || 'frontend',
    related_question_id: payload.related_question_id || payload.relatedQuestionId,
    mistake_type: payload.mistake_type || payload.mistakeType,
    weak_skill: payload.weak_skill || payload.weakSkill,
  }, { saved: false, error: safeFallbackNotice() });
  return {
    saved: Boolean(data.saved),
    already_saved: Boolean(data.already_saved),
    note_id: data.note_id as string | number | undefined,
    status: String(data.status || (data.saved ? 'saved' : 'error')),
    error: data.reason ? String(data.reason) : undefined,
  };
}

export async function askNotebookGuide(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return apiPost('/notebook/guide/ask', {
    learner_id: currentLearnerId() || payload.learner_id || payload.learnerId,
    subject: payload.subject || selectedSubject(),
    concept_id: payload.concept_id || payload.conceptId || selectedConceptId(),
    concept_name: payload.concept_name || payload.conceptName || selectedConceptName(),
    question: payload.question || payload.prompt || payload.doubt_text,
  }, {
    answer: `Review ${selectedConceptName() || 'the current concept'} using saved notes, mistakes, and the current concept resource.`,
    sources_used: ['frontend_fallback'],
    learner_memory_used: false,
  });
}

export async function searchNotebook(learnerId: string, query: string): Promise<NotebookSearchResult[]> {
  const normalized = query.trim().toLowerCase();
  const fallback = normalized
    ? mockData.mockNotebookSearchResults.filter((item) =>
        [item.concept, item.summary, item.sourceType, ...item.tags].join(' ').toLowerCase().includes(normalized)
      )
    : mockData.mockNotebookSearchResults;
  const data = await apiGet<NotebookSearchResult[] | { results?: NotebookSearchResult[]; matches?: NotebookSearchResult[] }>(
    `/learner/notebook/search/${learnerId}?q=${encodeURIComponent(query)}&top_k=5`,
    fallback
  );
  return Array.isArray(data) ? data : data.results || data.matches || fallback;
}

export async function getProgress(learnerId: string, subject?: string): Promise<ProgressData> {
  const suffix = subject || selectedSubject();
  const emptyProgress: ProgressData = {
    hasProgressData: false,
    sourceLabel: 'No progress yet',
    currentLevel: 1,
    totalXP: 0,
    currentStreak: 0,
    conceptsMastered: 0,
    accuracy: 0,
    averageConfidence: 0,
    reviewDue: 0,
    xpToday: 0,
    masteryPercent: 0,
    subjectProgress: [{ subjectName: suffix || 'Selected subject', progressPercentage: 0, masteredConcepts: 0, totalConcepts: 0, color: '#0284c7' }],
    conceptMastery: [],
    weakAreas: [],
    xpHistory: [],
    streakCalendar: [],
  };
  const data = await apiGet<ProgressData | Record<string, unknown>>(
    `/learner/progress/${learnerId}${suffix ? `?subject=${encodeURIComponent(suffix)}` : ''}`,
    emptyProgress
  );
  return { ...emptyProgress, ...(data as Partial<ProgressData>) };
}

export async function getStreakXP(learnerId: string): Promise<RewardState> {
  return getRewardState(learnerId);
}

export async function getMistakeReview(learnerId: string): Promise<MistakeReview[]> {
  const data = await apiGet<MistakeReview[] | { mistakes?: MistakeReview[] }>(
    `/mistakes/${learnerId}`,
    mockData.mockMistakeReview
  );
  return Array.isArray(data) ? data : data.mistakes || mockData.mockMistakeReview;
}

export async function getMistakes(learnerId: string): Promise<MistakeReview[]> {
  return getMistakeReview(learnerId);
}

export async function getWeaknessPractice(learnerId: string, conceptId?: string): Promise<AssessmentQuestion[]> {
  const activeConcept = conceptId || selectedConceptId() || subjectConceptFallback(selectedSubject()).id;
  return getAssessment(learnerId, activeConcept, { subject: selectedSubject(), difficulty: selectedDifficulty() });
}

export async function getRewardState(learnerId: string): Promise<RewardState> {
  const emptyReward: RewardState = {
    totalXp: 0,
    xpAwardedToday: 0,
    currentLevel: 1,
    nextLevelXp: 100,
    dailyGoalXp: 30,
    dailyGoalCompleted: false,
    currentStreak: 0,
    longestStreak: 0,
    streakUpdated: false,
    badges: [],
    levelName: 'Level 1',
  };
  const data = await apiGet<Record<string, unknown>>(`/reward/${learnerId}`, emptyReward as unknown as Record<string, unknown>);
  const reward = (data.reward_gamification || data) as Record<string, unknown>;
  const xp = (reward.xp || {}) as Record<string, unknown>;
  const streak = (reward.streak || {}) as Record<string, unknown>;
  return {
    ...emptyReward,
    totalXp: Number(xp.total_xp || data.totalXp || emptyReward.totalXp),
    xpAwardedToday: Number(xp.daily_xp || data.xpAwardedToday || emptyReward.xpAwardedToday),
    currentLevel: Number(xp.current_level || data.currentLevel || emptyReward.currentLevel),
    currentStreak: Number(streak.current_streak || data.currentStreak || emptyReward.currentStreak),
    longestStreak: Number(streak.longest_streak || data.longestStreak || emptyReward.longestStreak),
  };
}

export async function getXAI(learnerIdOrConceptId: string, conceptId?: string): Promise<XAIReflection> {
  const params = new URLSearchParams();
  if (conceptId) params.set('concept_id', conceptId);
  if (selectedSubject()) params.set('subject', selectedSubject());
  const query = params.toString() ? `?${params.toString()}` : '';
  const data = await apiGet<Record<string, unknown>>(
    `/xai/${learnerIdOrConceptId}${query}`,
    { ...mockData.mockXAIReflection, conceptId: learnerIdOrConceptId } as unknown as Record<string, unknown>
  );
  return {
    ...mockData.mockXAIReflection,
    ...(data as Partial<XAIReflection>),
    conceptId: String(data.conceptId || data.concept_id || learnerIdOrConceptId),
  };
}

export async function getDemoRun(profile: string): Promise<DemoRunData> {
  return apiGet(`/tutor/adaptive-session/${encodeURIComponent(profile)}`, { ...mockData.mockDemoRunData, profile });
}

export async function getPuzzleActivities(learnerIdOrConceptId: string, conceptIdArg?: string, subjectArg?: string): Promise<PuzzleActivity[]> {
  const learnerId = conceptIdArg ? learnerIdOrConceptId : currentLearnerId();
  const conceptId = conceptIdArg || learnerIdOrConceptId;
  const subject = subjectArg || selectedSubject();
  const baseFallback = mockData.mockPuzzleActivities.filter((activity) => activity.conceptId === conceptId);
  const fallback = (baseFallback.length ? baseFallback : []).concat([
    { id: `${conceptId}-debug`, conceptId, type: 'debug', title: 'Debug challenge', prompt: 'Find and fix the issue in this aligned task.', code: '2score = 10\nprint(2score)', solution: 'score2 = 10', hint: 'Check naming or syntax rules.', xp: 10 },
    { id: `${conceptId}-output`, conceptId, type: 'predict_output', title: 'Output prediction', prompt: 'Predict the result before running it.', code: 'value = 10\nprint(value)', solution: '10', hint: 'Trace the code line by line.', xp: 10 },
    { id: `${conceptId}-transfer`, conceptId, type: 'challenge', title: 'Transfer task', prompt: 'Use the same idea in a new situation.', code: '', solution: selectedConceptName() || conceptId, hint: 'Name the rule first.', xp: 15 },
    { id: `${conceptId}-multi`, conceptId, type: 'logic', title: 'Multi-step challenge', prompt: 'Explain the rule, example, and common mistake.', code: '', solution: selectedConceptName() || conceptId, hint: 'Break it into three parts.', xp: 15 },
  ]);
  const data = await apiGet<PuzzleActivity[] | { activities?: PuzzleActivity[] }>(
    `/puzzle/${learnerId}/${conceptId}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`,
    fallback.length ? fallback : mockData.mockPuzzleActivities
  );
  return Array.isArray(data) ? data : data.activities || fallback || mockData.mockPuzzleActivities;
}

export async function getChallenges(learnerIdOrConceptId: string, conceptIdArg?: string, subjectArg?: string): Promise<PuzzleActivity[]> {
  return getPuzzleActivities(learnerIdOrConceptId, conceptIdArg, subjectArg);
}

export async function getFlashcards(learnerIdOrConceptId: string, conceptId?: string, subjectArg?: string): Promise<Flashcard[]> {
  const subject = subjectArg || selectedSubject();
  const activeConcept = conceptId || selectedConceptId() || learnerIdOrConceptId;
  const title = getConceptDisplayName(activeConcept, selectedConceptName() || subjectConceptFallback(subject).name);
  const fallback: Flashcard[] = [
    { id: `fc-${activeConcept}-1`, conceptId: activeConcept, card_type: 'concept_recall_flashcard', front: `What is ${title}?`, back: subject.toLowerCase().includes('sql') ? 'It is a database concept used to store or retrieve organized data.' : `${title} is a core concept in ${subject || 'the selected subject'}.`, explanation: 'Recall the definition before solving.', difficulty: 'easy', due: true },
    { id: `fc-${activeConcept}-2`, conceptId: activeConcept, card_type: 'misconception_flashcard', front: 'What mistake should you avoid?', back: 'Do not use syntax without checking the concept meaning and expected result.', explanation: 'This card targets common mistakes.', difficulty: 'medium', due: true },
    { id: `fc-${activeConcept}-3`, conceptId: activeConcept, card_type: 'example_flashcard', front: 'What example proves the rule?', back: `Use one small ${title} example and explain the result.`, explanation: 'Example card.', difficulty: 'easy', due: true },
    { id: `fc-${activeConcept}-4`, conceptId: activeConcept, card_type: 'debug_flashcard', front: 'What should you check while debugging?', back: 'Check the exact rule, syntax, and expected output.', explanation: 'Debug card.', difficulty: 'medium', due: true },
    { id: `fc-${activeConcept}-5`, conceptId: activeConcept, card_type: 'personal_flashcards', front: 'What should I personally review?', back: `Review ${title} and one previous mistake.`, explanation: 'Personal review card.', difficulty: 'medium', due: true },
    { id: `fc-${activeConcept}-6`, conceptId: activeConcept, card_type: 'syntax_flashcard', front: 'What syntax or rule matters?', back: 'Name the rule before using it.', explanation: 'Syntax card.', difficulty: 'medium', due: true },
    { id: `fc-${activeConcept}-7`, conceptId: activeConcept, card_type: 'flashcard', front: 'What is the quick recap?', back: `${title}: definition, example, mistake, next practice.`, explanation: 'Generic recap card.', difficulty: 'easy', due: true },
    { id: `fc-${activeConcept}-8`, conceptId: activeConcept, card_type: 'spaced_repetition_card', front: `Spaced review: summarize ${title}.`, back: `Recall the definition, one example, and one common mistake for ${title}.`, explanation: 'Spaced repetition card.', difficulty: 'easy', due: true },
  ];
  const path = conceptId
    ? `/flashcards/${learnerIdOrConceptId}/${conceptId}`
    : `/flashcards/${learnerIdOrConceptId}`;
  const data = await apiGet<Flashcard[] | { flashcards?: Flashcard[] }>(
    `${path}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`,
    fallback.length ? fallback : mockData.mockFlashcards
  );
  const cards = Array.isArray(data) ? data : data.flashcards || fallback || mockData.mockFlashcards;
  return cards.flatMap((card, idx) => shortenFlashcard(card, getConceptDisplayName(card.conceptId || activeConcept, title), idx));
}

export async function getMindmap(conceptId: string, subjectArg?: string): Promise<MindMap> {
  const subject = subjectArg || selectedSubject();
  const title = getConceptDisplayName(conceptId, selectedConceptName() || subjectConceptFallback(subject).name);
  return apiGet(`/mindmap/${conceptId}${subject ? `?subject=${encodeURIComponent(subject)}` : ''}`, {
    conceptId,
    title,
    center: title,
    nodes: [
      { id: 'definition', title: 'Definition', body: `${title} is part of ${subject || 'the selected subject'} learning.`, color: '#2563eb', x: 50, y: 16 },
      { id: 'examples', title: 'Examples', body: subject.toLowerCase().includes('sql') ? 'SELECT name FROM students;' : `A small ${title} example`, color: '#16a34a', x: 82, y: 32 },
      { id: 'key_points', title: 'Key Points', body: `Understand ${title}; try one example; check the result.`, color: '#7c3aed', x: 78, y: 72 },
      { id: 'mistakes', title: 'Common Mistakes', body: 'Do not memorize syntax without meaning.', color: '#e11d48', x: 22, y: 72 },
      { id: 'use', title: 'Real-world Use', body: `${title} appears in practical ${subject || 'subject'} tasks.`, color: '#0891b2', x: 18, y: 32 },
    ],
  });
}

function shortenFlashcard(card: Flashcard, title: string, index: number): Flashcard[] {
  const cleanTitle = cleanConceptTitle(title);
  let front = String(card.front || `What is ${cleanTitle}?`).split(/[.\n]/)[0].trim();
  front = front.replace(/what is\s+what is\s+/i, 'What is ');
  if (/^what is\s+/i.test(front)) {
    front = `What is ${cleanTitle.toLowerCase()}?`;
  }
  const rawBack = String(card.back || card.explanation || '');
  const parts = rawBack
    .split(/\n|\. |; /)
    .map((item) => item.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)
    .slice(0, 2);
  const back = sentencePreview(parts.join('. '), 260) || `${cleanTitle} is the current concept. Review the definition, one example, and one common mistake.`;
  return [{
    ...card,
    id: card.id || `fc-${card.conceptId || cleanTitle}-${index}`,
    front: front.length > 90 ? `What is the key idea of ${cleanTitle}?` : front || `What is ${cleanTitle}?`,
    back,
    conceptId: card.conceptId || cleanTitle,
  }];
}

export async function getAudioOverview(voiceType = 'teaching_voice_script'): Promise<Record<string, unknown>> {
  const subject = selectedSubject() || 'Python';
  const concept = selectedConceptName() || subjectConceptFallback(subject).name;
  const difficulty = selectedDifficulty();
  const fallback = {
    status: 'success',
    voice_script: {
      task_type: voiceType,
      script: `Cogni audio overview for ${concept}. Review the definition, one example, one mistake, and the next practice step.`,
      audio_ready: true,
      estimated_duration_sec: 35,
      voice_sections: {
        opening: `Welcome to ${concept}.`,
        explanation: `This is a spoken ${voiceType.replaceAll('_', ' ')}.`,
        example: `Use one aligned ${concept} example.`,
        check_prompt: 'Explain the rule in your own words.',
        closing: 'Continue with the next guided task.',
      },
    },
    audio_overview: {
      status: 'success',
      script: `Cogni audio overview for ${concept}. Review the definition, one example, one mistake, and the next practice step.`,
      audio_ready: true,
      concept_name: concept,
      difficulty,
      source_level: `${difficulty}_content`,
    },
  };
  return apiPost('/cognitutor/audio-overview', {
    domain: subject,
    concept,
    difficulty,
    teaching_view: 'definition_view',
    voice_type: voiceType,
  }, fallback);
}

export async function getCogniTutorFrontendPacket(): Promise<Record<string, unknown>> {
  const subject = selectedSubject() || 'Python';
  const concept = selectedConceptName() || subjectConceptFallback(subject).name;
  return apiPost('/cognitutor/frontend-packet', {
    learner_id: currentLearnerId(),
    domain: subject,
    concept,
    difficulty: selectedDifficulty(),
    teaching_view: 'definition_view',
  }, cognitutorProductPacketFixture);
}

export async function getAdaptivePathRecommendation(learnerId: string, conceptId: string): Promise<AdaptivePathRecommendation> {
  return apiGet(`/adaptive-path/${learnerId}`, { ...mockData.mockAdaptivePathRecommendation, learnerId, conceptId });
}

export async function getProgressionResult(learnerId: string, conceptId?: string): Promise<ProgressionResult> {
  return apiGet(`/progression/${learnerId}${conceptId ? `/${conceptId}` : ''}`, mockData.mockProgressionResult);
}

export async function getLessonResult(learnerId: string, conceptId?: string): Promise<LessonResult> {
  return apiGet(`/lesson-result/${learnerId}${conceptId ? `/${conceptId}` : ''}`, mockData.mockLessonResult);
}

export async function getRevision(learnerId: string): Promise<Record<string, unknown>> {
  return apiGet(`/revision/${learnerId}`, {
    auto_flow: true,
    learner_id: learnerId,
    guide_message: "Welcome back! It's been a while, so let's revise before continuing.",
    current_activity: { type: 'flashcard_revision', frontend_component: 'FlashcardDeck', payload: {} },
    next_recommended_activity: { type: 'assessment', label: 'Try a quick check', reason: 'Confirm revision is active' },
  });
}

export async function getRetentionPrediction(learnerId: string): Promise<RetentionPrediction> {
  const data = await apiGet<Record<string, unknown>>(`/retention/${learnerId}`, {
    learnerId,
    conceptId: 'current',
    retentionProbability: 0.72,
    reviewDueInDays: 2,
    riskLevel: 'medium',
  });
  return {
    learnerId: String(data.learnerId || data.learner_id || learnerId),
    conceptId: String(data.conceptId || data.concept_id || 'current'),
    retentionProbability: Number(data.retentionProbability || data.retention_probability || 0.72),
    reviewDueInDays: Number(data.reviewDueInDays || data.review_due_in_days || 2),
    riskLevel: (data.riskLevel || data.risk_level || 'medium') as RetentionPrediction['riskLevel'],
  };
}

export async function getAIEvidence(learnerId: string, conceptId?: string, subject?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (conceptId) params.set('concept_id', conceptId);
  if (subject || selectedSubject()) params.set('subject', subject || selectedSubject());
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiGet(`/ai/evidence/${learnerId}${query}`, {});
}

export async function getReviewerEvidence(learnerId: string, conceptId?: string, subject?: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams();
  if (conceptId) params.set('concept_id', conceptId);
  if (subject || selectedSubject()) params.set('subject', subject || selectedSubject());
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiGet(`/reviewer/evidence/${learnerId}${query}`, {
    status: 'warning',
    fallback_used: true,
    message: 'Reviewer evidence is not available yet. Run backend evidence report or check backend connection.',
    module_status_summary: [],
    evaluation_reports: [],
  });
}

export async function getGenerationCoverage(learnerId: string): Promise<Record<string, unknown>> {
  return apiGet(`/generation/coverage/${learnerId}`, {});
}

export async function getGenerationTasks(conceptId?: string, subject?: string): Promise<Record<string, unknown>> {
  const activeConcept = conceptId || selectedConceptId() || 'current';
  const activeSubject = subject || selectedSubject();
  return apiGet(`/generation/tasks/${encodeURIComponent(activeConcept)}${activeSubject ? `?subject=${encodeURIComponent(activeSubject)}` : ''}`, {});
}

export async function getAgenticTrace(learnerId: string): Promise<Record<string, unknown>> {
  return apiGet(`/agentic/trace/${learnerId}`, {});
}

export async function getPersonalization(learnerId: string): Promise<Record<string, unknown>> {
  return apiGet(`/learner/personalization/${learnerId}`, {});
}
