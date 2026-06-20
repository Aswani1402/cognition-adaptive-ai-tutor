import { CogniMood, cogniScripts, correctByDifficulty } from './cogniScripts';
import { Difficulty } from '../../lib/types';

export type CogniContext = {
  page: string;
  activityType?: string;
  difficulty?: Difficulty;
  score?: number;
  label?: string;
  mistakeType?: string;
  weakestSkill?: string;
  timeGapCategory?: string;
  selectedView?: string;
  nextAction?: string;
  backendConnected?: boolean;
  mockFallbackUsed?: boolean;
  backendMessage?: string;
};

export function getCogniMessage(context: CogniContext): { message: string; mood: CogniMood; stepLabel: string; actionHint: string } {
  if (context.backendMessage && !context.mockFallbackUsed) {
    return { message: context.backendMessage, mood: 'happy', stepLabel: label(context), actionHint: context.nextAction || '' };
  }
  if (context.backendConnected === false || context.mockFallbackUsed) {
    return { message: cogniScripts.mock_mode, mood: 'warning', stepLabel: 'Mock Mode', actionHint: 'Backend fallback is active' };
  }
  if (context.timeGapCategory === 'days' || context.timeGapCategory === 'weeks') {
    return { message: context.timeGapCategory === 'weeks' ? cogniScripts.returning_learner.weeks : cogniScripts.returning_learner.days, mood: 'revision', stepLabel: 'Returning learner', actionHint: 'Revision comes first' };
  }
  if (context.mistakeType?.includes('syntax')) return { message: cogniScripts.hint.syntax, mood: 'thinking', stepLabel: 'Syntax support', actionHint: 'Fix syntax before retry' };
  if (context.weakestSkill === 'output_prediction') return { message: cogniScripts.hint.output, mood: 'thinking', stepLabel: 'Output tracing', actionHint: 'Trace line by line' };
  if (typeof context.score === 'number') {
    if (context.score >= 0.8) return { message: correctByDifficulty(context.difficulty), mood: context.difficulty === 'hard' ? 'celebrating' : 'success', stepLabel: 'Level passed', actionHint: context.nextAction || 'Move forward' };
    if (context.score >= 0.45) return { message: cogniScripts.answer_partial, mood: 'revision', stepLabel: 'Almost there', actionHint: 'Revise and retry' };
    return { message: cogniScripts.answer_wrong, mood: 'encouragement', stepLabel: 'Retry support', actionHint: 'Reteach another way' };
  }
  if (context.nextAction?.includes('next_concept')) return { message: cogniScripts.difficulty_progression.hard_to_next_concept, mood: 'celebrating', stepLabel: 'Concept complete', actionHint: 'Next topic unlocked' };
  if (context.page === 'login') return { message: cogniScripts.auth.login, mood: 'happy', stepLabel: 'Login', actionHint: 'Continue your journey' };
  if (context.page === 'register') return { message: cogniScripts.auth.register, mood: 'happy', stepLabel: 'Register', actionHint: 'Create your learner profile' };
  if (context.page === 'subjects') return { message: cogniScripts.subject_selection.first_time, mood: 'thinking', stepLabel: 'Choose subject', actionHint: 'Pick one subject only' };
  if (context.activityType === 'flashcard_revision') return { message: cogniScripts.flashcard.start, mood: 'revision', stepLabel: 'Flashcards', actionHint: 'Recall key points' };
  if (context.activityType === 'mindmap_revision') return { message: cogniScripts.mindmap.start, mood: 'thinking', stepLabel: 'Mindmap', actionHint: 'See the full concept' };
  if (context.activityType === 'assessment') return { message: cogniScripts.assessment_intro.quick_check, mood: 'thinking', stepLabel: 'Quick check', actionHint: 'Answer and I will adapt' };
  if (context.activityType === 'teaching') return { message: teaching(context.difficulty), mood: 'happy', stepLabel: `${context.difficulty || 'easy'} teaching`, actionHint: 'Learn one view first' };
  if (context.page === 'xai') return { message: cogniScripts.xai.reason, mood: 'thinking', stepLabel: 'Why this?', actionHint: 'Review tutor reasoning' };
  if (context.page === 'rewards') return { message: cogniScripts.rewards.streak, mood: 'celebrating', stepLabel: 'Rewards', actionHint: 'Keep momentum' };
  return { message: cogniScripts.encouragement, mood: 'encouragement', stepLabel: label(context), actionHint: context.nextAction || '' };
}

function teaching(difficulty?: Difficulty) {
  if (difficulty === 'medium') return cogniScripts.teaching.start_medium;
  if (difficulty === 'hard') return cogniScripts.teaching.start_hard;
  return cogniScripts.teaching.start_easy;
}

function label(context: CogniContext) {
  return context.activityType?.replaceAll('_', ' ') || context.page;
}
