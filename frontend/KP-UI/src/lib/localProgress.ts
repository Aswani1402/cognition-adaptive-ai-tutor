import type { CodeSubmitResult, RewardState } from './types';

const KEY = 'cognitutor_local_progress';

type LocalProgress = {
  date: string;
  correctAnswers: number;
  completedQuestions: number;
  xp: number;
  streak: number;
  badges: string[];
  concepts: Record<string, number>;
};

const today = () => new Date().toISOString().slice(0, 10);

export function readLocalProgress(): LocalProgress {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<LocalProgress>;
    const isToday = parsed.date === today();
    return {
      date: today(),
      correctAnswers: isToday ? Number(parsed.correctAnswers || 0) : 0,
      completedQuestions: isToday ? Number(parsed.completedQuestions || 0) : 0,
      xp: isToday ? Number(parsed.xp || 0) : 0,
      streak: Number(parsed.streak || 0),
      badges: Array.isArray(parsed.badges) ? parsed.badges : [],
      concepts: isToday && parsed.concepts ? parsed.concepts : {},
    };
  } catch {
    return { date: today(), correctAnswers: 0, completedQuestions: 0, xp: 0, streak: 0, badges: [], concepts: {} };
  }
}

export function recordAnswerProgress(result: CodeSubmitResult, conceptId?: string) {
  const correct = result.correct || result.score >= 0.8;
  const current = readLocalProgress();
  const next: LocalProgress = {
    ...current,
    completedQuestions: current.completedQuestions + 1,
    correctAnswers: current.correctAnswers + (correct ? 1 : 0),
    xp: current.xp + (correct ? 10 : 2),
    streak: correct || current.completedQuestions > 0 ? Math.max(1, current.streak) : current.streak,
    badges: current.badges,
    concepts: { ...current.concepts },
  };
  if (correct && conceptId) next.concepts[conceptId] = Math.min(100, (next.concepts[conceptId] || 0) + 25);
  if (next.correctAnswers >= 1 && !next.badges.includes('First Correct Answer')) next.badges.push('First Correct Answer');
  if (next.correctAnswers >= 2 && !next.badges.includes('Two in a Row')) next.badges.push('Two in a Row');
  localStorage.setItem(KEY, JSON.stringify(next));
  localStorage.setItem('cognitutor_clean_start', 'false');
  localStorage.setItem('latest_answer_result', JSON.stringify({
    score: result.score,
    correct: result.correct,
    conceptId,
    feedback: result.feedback,
    nextAction: result.recommended_next_activity?.label || result.nextAction,
    timestamp: new Date().toISOString(),
  }));
  window.dispatchEvent(new CustomEvent('cognitutor-progress-updated', { detail: next }));
  return next;
}

export function mergeRewardWithLocal(reward: RewardState): RewardState {
  const local = readLocalProgress();
  if (localStorage.getItem('cognitutor_clean_start') === 'true' && local.completedQuestions === 0) {
    return {
      ...reward,
      totalXp: 0,
      xpAwardedToday: 0,
      currentStreak: 0,
      dailyGoalCompleted: false,
      badges: [],
    };
  }
  return {
    ...reward,
    totalXp: Math.max(reward.totalXp, local.xp),
    xpAwardedToday: Math.max(reward.xpAwardedToday, local.xp),
    currentStreak: Math.max(reward.currentStreak, local.completedQuestions > 0 ? Math.max(1, local.streak) : local.streak),
    dailyGoalCompleted: reward.dailyGoalCompleted || local.completedQuestions > 0 || local.xp >= reward.dailyGoalXp,
    badges: Array.from(new Set([...(reward.badges || []), ...local.badges])),
  };
}
