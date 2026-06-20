import { Inbox } from 'lucide-react';

export default function EmptyState({ title, description, actionLabel, onAction }: { title: string; description: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="rounded-3xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/40 p-10 text-center">
      <Inbox className="mx-auto mb-4 h-10 w-10 text-slate-400" />
      <h3 className="text-lg font-bold">{title}</h3>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
      {actionLabel && onAction && (
        <button onClick={onAction} className="mt-4 rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white">{actionLabel}</button>
      )}
    </div>
  );
}
