export const CONCEPT_NAME_MAP: Record<string, string> = {
  P1: 'Variables',
  P2: 'Data Types',
  P3: 'Conditionals',
  P4: 'Loops',
  P5: 'Functions',
  P6: 'OOP',
  P7: 'Decorators and Generators',
  P8: 'File Handling and I/O',
  H1: 'What is HTML',
  H2: 'HTML Tags and Elements',
  H3: 'Attributes and Links',
  H4: 'Images and Lists',
  H5: 'Forms and Inputs',
  S1: 'Database Basics',
  S2: 'SELECT',
  S3: 'WHERE and Filters',
  S4: 'JOIN',
  S5: 'Indexes',
  S6: 'Window Functions',
  S7: 'CTEs',
  G1: 'Version Control',
  G2: 'Git Repositories',
  G3: 'Commits and History',
  G4: 'Branches',
  G5: 'Merge and Conflict Basics',
  D1: 'Arrays',
  D2: 'Linked Lists',
  D3: 'Stacks',
  D4: 'Queues',
  D5: 'Trees',
};

export function getConceptDisplayName(conceptId?: string | null, backendTopic?: string | null) {
  const topic = String(backendTopic || '').trim();
  if (topic && !looksLikeConceptId(topic)) return topic;
  const id = String(conceptId || topic || '').trim();
  if (!id) return 'Current Concept';
  return CONCEPT_NAME_MAP[id.toUpperCase()] || id.replace(/[-_]/g, ' ');
}

export function looksLikeConceptId(value: string) {
  return /^[A-Z]\d+$/i.test(value.trim()) || /^c\d+$/i.test(value.trim());
}

export function getFallbackPath(subject?: string) {
  const normalized = String(subject || '').toLowerCase();
  if (normalized.includes('html') || normalized.includes('web')) return ['H1', 'H2', 'H3', 'H4', 'H5'];
  if (normalized.includes('sql') || normalized.includes('database')) return ['S1', 'S2', 'S3', 'S4', 'S5'];
  if (normalized.includes('git')) return ['G1', 'G2', 'G3', 'G4', 'G5'];
  if (normalized.includes('data')) return ['D1', 'D2', 'D3', 'D4', 'D5'];
  return ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'];
}

export function cleanLearnerMessage(_error?: unknown) {
  return 'This content is being prepared. Showing saved learning content instead.';
}

export function cleanEvidenceMessage() {
  return 'Unable to load live evidence right now. Showing available learner context.';
}

export function subjectForConcept(conceptId?: string | null) {
  const id = String(conceptId || '').toUpperCase();
  if (id.startsWith('S')) return 'SQL / Database';
  if (id.startsWith('H')) return 'HTML/Web Basics';
  if (id.startsWith('G')) return 'Git';
  if (id.startsWith('D')) return 'Data Structures';
  return 'Python';
}

export function firstConceptForSubject(subject?: string) {
  return getFallbackPath(subject)[0] || 'P1';
}

export function clearLearnerStorage() {
  const exactKeys = [
    'access_token',
    'user_id',
    'learner_id',
    'app_learner_code',
    'user_name',
    'user_email',
    'active_subject',
    'current_concept_id',
    'current_concept_name',
    'current_difficulty',
    'selected_teaching_view',
    'selected_subject',
    'cognitutor_local_progress',
    'cognitutor_saved_note',
    'cognitutor_frontend_event_log',
    'latest_answer_result',
  ];
  const prefixes = [
    'learner_context',
    'reward',
    'notebook',
    'mistake',
    'assessment',
    'progress',
    'xai',
    'current_',
    'cached_',
  ];
  for (const storage of [localStorage, sessionStorage]) {
    exactKeys.forEach((key) => storage.removeItem(key));
    Object.keys(storage).forEach((key) => {
      if (prefixes.some((prefix) => key.startsWith(prefix))) storage.removeItem(key);
    });
  }
}

export function initializeCleanLearner(subject?: string) {
  const activeSubject = subject || '';
  const conceptId = activeSubject ? firstConceptForSubject(activeSubject) : '';
  localStorage.setItem('current_difficulty', 'easy');
  if (activeSubject) localStorage.setItem('active_subject', activeSubject);
  if (conceptId) {
    localStorage.setItem('current_concept_id', conceptId);
    localStorage.setItem('current_concept_name', getConceptDisplayName(conceptId));
  }
  localStorage.setItem('cognitutor_local_progress', JSON.stringify({
    date: new Date().toISOString().slice(0, 10),
    correctAnswers: 0,
    completedQuestions: 0,
    xp: 0,
    streak: 0,
    badges: [],
    concepts: {},
  }));
  localStorage.setItem('cognitutor_clean_start', 'true');
}
