import { NotebookMemory } from './types';

const rawLabels = [
  'weak_answer',
  'wrong_option',
  'wrong_output',
  'syntax_misunderstanding',
  'debug_error',
  'fallback_cumulative',
  'exact_match',
  'mock',
  'Apply C2',
];

const labelMap: Record<string, string> = {
  weak_answer: 'Your answer was too short or unclear. Practice explaining the concept rule with one example.',
  wrong_option: 'You selected an incorrect option. Review the key definition and try one MCQ again.',
  wrong_output: 'Practice tracing the code step by step before writing the output.',
  syntax_misunderstanding: 'Review the syntax rule and complete one syntax practice.',
  debug_error: 'Practice identifying the exact line that causes the error.',
  missing_explanation: 'Your answer had a valid start but missed the explanation or scenario details.',
};

export type LearnerFacingNotebook = NotebookMemory & {
  learner_facing_summary?: string;
  learner_facing_key_points?: string[];
  learner_facing_mistakes?: string[];
  learner_facing_revision_plan?: string[];
  learner_facing_flashcards?: { front: string; back: string }[];
  learner_facing_doubts?: { question: string; answer_preview: string }[];
  learner_facing_practice_queue?: string[];
  practiceQueue?: string[];
  source?: string;
};

export function normalizeNotebookMemory(input: NotebookMemory | LearnerFacingNotebook): LearnerFacingNotebook {
  const record = input as LearnerFacingNotebook;
  const concept = clean(record.conceptId || (record as any).concept_name || 'this concept') || 'this concept';
  const summary = firstClean(
    record.learner_facing_summary,
    record.summary,
    `Review ${concept} with the definition, one example, and one quick practice task.`
  );
  const mistakes = cleanList(record.learner_facing_mistakes || record.mistakes || record.weakPoints || [])
    .map(formatMistakeForLearner)
    .filter(Boolean)
    .slice(0, 5);
  const revisionPlan = cleanList(record.learner_facing_revision_plan || record.revisionPlan || [])
    .map((item) => formatRevisionPlanForLearner(item, concept))
    .slice(0, 5);
  const keyPoints = cleanList(record.learner_facing_key_points || (record as any).keyPoints || record.savedExplanations || [])
    .slice(0, 5);
  const flashcards = normalizeFlashcards(record.learner_facing_flashcards || record.savedFlashcards || [], concept).slice(0, 5);
  const doubts = normalizeDoubts(record.learner_facing_doubts || record.pastDoubts || [], concept).slice(0, 5);
  const practiceQueue = cleanList(record.learner_facing_practice_queue || record.practiceQueue || record.practiceHistory || [])
    .map((item) => formatPractice(item, concept))
    .slice(0, 5);

  return {
    ...record,
    summary,
    learner_facing_summary: summary,
    learner_facing_key_points: keyPoints.length ? keyPoints : [
      `Understand the definition of ${concept}.`,
      `Connect ${concept} to one small example.`,
      'Check the final result before answering.',
    ],
    weakPoints: mistakes,
    mistakes,
    learner_facing_mistakes: mistakes,
    revisionPlan: revisionPlan.length ? revisionPlan : [
      `Review the definition of ${concept}.`,
      `Write one clear example using ${concept}.`,
      'Try one MCQ and one short explanation.',
    ],
    learner_facing_revision_plan: revisionPlan,
    savedFlashcards: flashcards.map((card) => `Q: ${card.front}\nA: ${card.back}`),
    learner_facing_flashcards: flashcards,
    pastDoubts: doubts.map((item) => `Q: ${item.question}\nA: ${item.answer_preview}`),
    learner_facing_doubts: doubts,
    practiceQueue: practiceQueue.length ? practiceQueue : [
      `Try one MCQ about ${concept}.`,
      `Write a short example using ${concept}.`,
      `Explain why ${concept} is useful.`,
    ],
    learner_facing_practice_queue: practiceQueue,
  };
}

export function formatMistakeForLearner(value: unknown): string {
  const text = clean(value);
  const lowered = text.toLowerCase();
  if (!text || lowered === 'none' || lowered.startsWith('correct. your answer matches')) return '';
  for (const [raw, mapped] of Object.entries(labelMap)) {
    if (lowered.includes(raw)) return mapped;
  }
  return text;
}

export function formatRevisionPlanForLearner(value: unknown, concept: string): string {
  const text = clean(value);
  const lowered = text.toLowerCase();
  if (!text) return '';
  if (lowered.includes('output')) return `Predict the output of one short ${concept} example.`;
  if (lowered.includes('syntax')) return `Complete one syntax practice for ${concept}.`;
  if (lowered.includes('debug')) return `Fix one small ${concept} debugging task.`;
  if (lowered.includes('transfer')) return `Try one transfer task using ${concept} in a real situation.`;
  return text;
}

export function normalizeFlashcards(values: unknown[], concept: string) {
  const cards = values.flatMap((value) => {
    if (value && typeof value === 'object' && 'front' in value) {
      const card = value as { front?: unknown; back?: unknown };
      return [{ front: clean(card.front), back: clean(card.back) }];
    }
    const text = clean(value);
    if (!text) return [];
    const match = text.match(/^Q:\s*(.*?)\s*A:\s*(.*)$/is);
    if (match) return [{ front: clean(match[1]), back: clean(match[2]) }];
    if (text.endsWith('?')) return [{ front: text, back: `Review the core idea of ${concept}.` }];
    return [{ front: `What should I remember about ${concept}?`, back: text }];
  }).filter((card) => card.front && card.back);
  return dedupeCards(cards.length ? cards : [{ front: `What is ${concept}?`, back: `${concept} is the current concept you are studying.` }]);
}

export function normalizeDoubts(values: unknown[], concept: string) {
  return dedupeBy(values.flatMap((value) => {
    if (value && typeof value === 'object' && 'question' in value) {
      const item = value as { question?: unknown; answer_preview?: unknown };
      return [{ question: cleanDoubt(item.question, concept), answer_preview: clean(item.answer_preview) || `Review one example of ${concept}.` }];
    }
    const text = clean(value);
    if (!text) return [];
    const match = text.match(/^Q:\s*(.*?)\s*A:\s*(.*)$/is);
    if (match) return [{ question: cleanDoubt(match[1], concept), answer_preview: clean(match[2]) || `Review one example of ${concept}.` }];
    return [{ question: cleanDoubt(text, concept), answer_preview: `Review the definition and one example of ${concept}.` }];
  }), (item) => item.question);
}

function formatPractice(value: unknown, concept: string) {
  const text = clean(value);
  if (!text) return '';
  if (text.toLowerCase().includes('mcq')) return `Try one MCQ about ${concept}.`;
  return text;
}

function cleanDoubt(value: unknown, concept: string) {
  const text = clean(value);
  if (!text || text.toLowerCase() === 'what is this concept?') return `What is ${concept}?`;
  return text;
}

function clean(value: unknown) {
  let text = String(value ?? '').replace(/\s+/g, ' ').trim();
  rawLabels.forEach((raw) => {
    text = text.replace(new RegExp(raw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '');
  });
  text = text.replace(/\bC\d+\b/g, 'the current concept').replace(/\s+/g, ' ').trim();
  if (['none', 'null', 'undefined'].includes(text.toLowerCase())) return '';
  if (text.toLowerCase().startsWith('correct. your answer matches')) return '';
  return text;
}

function firstClean(...values: unknown[]) {
  for (const value of values) {
    const text = clean(value);
    if (text) return text;
  }
  return '';
}

function cleanList(values: unknown[]) {
  return dedupe(values.map(clean).filter(Boolean));
}

function dedupe(values: string[]) {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = value.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function dedupeCards(values: { front: string; back: string }[]) {
  return dedupeBy(values, (item) => `${item.front.toLowerCase()}|${item.back.toLowerCase()}`);
}

function dedupeBy<T>(values: T[], keyFn: (item: T) => string) {
  const seen = new Set<string>();
  return values.filter((value) => {
    const key = keyFn(value).toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
