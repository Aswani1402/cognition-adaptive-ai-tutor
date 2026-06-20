import { NotebookSearchResult } from '../../lib/types';
import type { FC } from 'react';

const LearnerMemoryResultCard: FC<{ result: NotebookSearchResult }> = ({ result }) => {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold uppercase text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300">{result.sourceType}</span>
        <span className="text-xs font-bold text-slate-400">{Math.round(result.score * 100)}% match</span>
      </div>
      <h3 className="font-black">{result.concept}</h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{result.summary}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {result.tags.map((tag) => <span key={tag} className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-300">{tag}</span>)}
      </div>
      <p className="mt-3 text-xs text-slate-400">{result.timestamp}</p>
    </article>
  );
};

export default LearnerMemoryResultCard;
