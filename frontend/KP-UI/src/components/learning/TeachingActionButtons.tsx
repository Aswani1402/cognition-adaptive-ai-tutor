import { BookOpen, Code, CornerDownRight, HelpCircle, Lightbulb, PlayCircle } from 'lucide-react';

const actions = [
  { label: 'Explain simpler', icon: Lightbulb },
  { label: 'Give analogy', icon: PlayCircle },
  { label: 'Show code', icon: Code },
  { label: 'Step-by-step', icon: BookOpen },
  { label: 'Common mistake', icon: CornerDownRight },
  { label: 'Ask doubt', icon: HelpCircle },
];

export default function TeachingActionButtons({ onAskDoubt }: { onAskDoubt?: () => void }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {actions.map(({ label, icon: Icon }) => (
        <button key={label} onClick={label === 'Ask doubt' ? onAskDoubt : undefined} className="flex flex-col items-center justify-center p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors gap-2 text-slate-700 dark:text-slate-300">
          <Icon className="w-5 h-5 text-sky-500" />
          <span className="text-sm font-medium">{label}</span>
        </button>
      ))}
    </div>
  );
}
