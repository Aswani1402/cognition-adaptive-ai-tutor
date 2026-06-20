import clsx from 'clsx';
import { GuidedActivityType } from '../../lib/types';

const steps: { type: GuidedActivityType; label: string }[] = [
  { type: 'subject_selection', label: 'Subject' },
  { type: 'teaching', label: 'Teach' },
  { type: 'assessment', label: 'Check' },
  { type: 'feedback', label: 'Feedback' },
  { type: 'reward', label: 'Reward' },
];

export default function SessionProgressTimeline({ current }: { current: GuidedActivityType }) {
  const currentIndex = Math.max(0, steps.findIndex((step) => step.type === current));

  return (
    <nav className="rounded-3xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="grid grid-cols-5 gap-2">
        {steps.map((step, index) => (
          <div key={step.type} className="min-w-0">
            <div className={clsx('h-2 rounded-full', index <= currentIndex ? 'bg-indigo-600' : 'bg-slate-200 dark:bg-slate-800')} />
            <p className={clsx('mt-2 truncate text-center text-xs font-bold', index <= currentIndex ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-400')}>
              {step.label}
            </p>
          </div>
        ))}
      </div>
    </nav>
  );
}
