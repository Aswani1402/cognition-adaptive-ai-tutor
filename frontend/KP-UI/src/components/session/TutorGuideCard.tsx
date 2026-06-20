import { Bot, Sparkles } from 'lucide-react';
import clsx from 'clsx';

export default function TutorGuideCard({
  message,
  step,
  reason,
  mode = 'backend',
}: {
  message: string;
  step: string;
  reason?: string;
  mode?: 'backend' | 'mock';
}) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex gap-4">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-lg shadow-indigo-600/20">
          <Bot className="h-7 w-7" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="font-black text-slate-900 dark:text-white">Cogni</p>
            <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{step}</span>
            <span className={clsx('rounded-full px-2.5 py-1 text-xs font-bold', mode === 'backend' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300')}>
              {mode === 'backend' ? 'Backend connected' : 'Mock Mode'}
            </span>
          </div>
          <p className="text-sm font-semibold leading-6 text-slate-700 dark:text-slate-200">{message}</p>
          {reason && (
            <p className="mt-3 inline-flex items-start gap-2 rounded-2xl bg-indigo-50 px-3 py-2 text-xs font-medium text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-200">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {reason}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
