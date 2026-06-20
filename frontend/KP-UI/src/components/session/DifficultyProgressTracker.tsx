import clsx from 'clsx';
import { Difficulty, DifficultyProgress } from '../../lib/types';

const levels: Difficulty[] = ['easy', 'medium', 'hard'];

export default function DifficultyProgressTracker({ conceptName, progress, currentDifficulty }: { conceptName: string; progress?: DifficultyProgress; currentDifficulty: Difficulty }) {
  const state = progress || {
    easy: currentDifficulty === 'easy' ? 'current' : 'passed',
    medium: currentDifficulty === 'medium' ? 'current' : currentDifficulty === 'hard' ? 'passed' : 'locked',
    hard: currentDifficulty === 'hard' ? 'current' : 'locked',
  } satisfies DifficultyProgress;
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-black text-slate-900 dark:text-white">{conceptName}</p>
        <p className="text-xs font-bold uppercase text-slate-500">Difficulty progression</p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {levels.map((level) => (
          <div key={level} className={clsx('rounded-2xl border px-3 py-2 text-center text-sm font-black capitalize',
            state[level] === 'passed' && 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-900/20 dark:text-emerald-300',
            state[level] === 'current' && 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-900 dark:bg-indigo-900/20 dark:text-indigo-300',
            state[level] === 'locked' && 'border-slate-200 bg-slate-50 text-slate-400 dark:border-slate-800 dark:bg-slate-900',
            state[level] === 'retry' && 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900 dark:bg-amber-900/20 dark:text-amber-300',
            state[level] === 'review_due' && 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-900 dark:bg-sky-900/20 dark:text-sky-300'
          )}>
            {level} {state[level] === 'passed' ? '✓' : state[level] === 'locked' ? '🔒' : state[level] === 'retry' ? '↻' : '•'}
          </div>
        ))}
      </div>
    </section>
  );
}
