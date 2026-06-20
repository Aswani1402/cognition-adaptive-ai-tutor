import { EvaluationResult } from '../../lib/types';

export default function EvaluationFusionPanel({ result }: { result: EvaluationResult }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-black">Evaluation fusion</h3>
        <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">{Math.round(result.score * 100)}%</span>
      </div>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{result.feedback}</p>
      <p className="mt-2 text-xs font-semibold text-slate-500">Next: {result.nextAction}</p>
    </section>
  );
}
