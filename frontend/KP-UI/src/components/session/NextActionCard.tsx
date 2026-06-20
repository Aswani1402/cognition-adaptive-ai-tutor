import { ArrowRight } from 'lucide-react';
import { NextRecommendedActivity } from '../../lib/types';

export default function NextActionCard({
  action,
  onClick,
  loading,
}: {
  action: NextRecommendedActivity;
  onClick: () => void;
  loading?: boolean;
}) {
  return (
    <section className="rounded-3xl border border-indigo-200 bg-indigo-50 p-5 dark:border-indigo-900/50 dark:bg-indigo-900/20">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-wider text-indigo-700 dark:text-indigo-300">Next guided step</p>
          <h3 className="mt-1 text-lg font-black text-slate-900 dark:text-white">{action.label}</h3>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{action.reason}</p>
        </div>
        <button
          onClick={onClick}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-600/20 transition hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
        >
          {loading ? 'Preparing...' : action.label} <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}
