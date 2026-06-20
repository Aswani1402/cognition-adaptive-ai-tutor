import CogniParrot from './CogniParrot';
import { CogniMood } from './cogniScripts';

export default function CogniGuideCard({
  message,
  mood = 'happy',
  stepLabel,
  actionHint,
  action,
  compact = false,
}: {
  message: string;
  mood?: CogniMood;
  stepLabel?: string;
  actionHint?: string;
  action?: { label: string; onClick: () => void };
  compact?: boolean;
}) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center gap-4">
        <CogniParrot mood={mood} size={compact ? 'sm' : 'md'} />
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <p className="font-black text-slate-900 dark:text-white">Cogni</p>
            {stepLabel && <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{stepLabel}</span>}
          </div>
          <p className="text-sm font-semibold leading-6 text-slate-700 dark:text-slate-200">{message}</p>
          {actionHint && <p className="mt-1 text-xs font-medium text-slate-500">{actionHint}</p>}
        </div>
        {action && <button onClick={action.onClick} className="rounded-2xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white">{action.label}</button>}
      </div>
    </section>
  );
}
