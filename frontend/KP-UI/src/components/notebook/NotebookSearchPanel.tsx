import { FormEvent, useState } from 'react';
import { Search } from 'lucide-react';
import { searchNotebook } from '../../lib/api';
import { NotebookSearchResult } from '../../lib/types';
import EmptyState from '../common/EmptyState';
import ErrorState from '../common/ErrorState';
import LoadingSkeleton from '../common/LoadingSkeleton';
import LearnerMemoryResultCard from './LearnerMemoryResultCard';
import { useLearnerSession } from '../../context/LearnerSessionContext';

export default function NotebookSearchPanel({ learnerId }: { learnerId?: string }) {
  const session = useLearnerSession();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<NotebookSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoading(true);
    setError('');
    try {
      setResults(await searchNotebook(learnerId || session.getCurrentLearnerId(), query));
    } catch {
      setError('Notebook search failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
      <form onSubmit={submit} className="flex gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} className="w-full rounded-2xl border border-slate-200 bg-slate-50 py-3 pl-10 pr-3 text-sm dark:border-slate-800 dark:bg-slate-900" placeholder="Search summaries, mistakes, doubts..." />
        </div>
        <button className="rounded-2xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white">Search</button>
      </form>
      <div className="mt-4 space-y-3">
        {loading && <LoadingSkeleton title="Searching memory" description="Checking summaries, mistakes, and doubts." />}
        {error && <ErrorState message={error} />}
        {!loading && !error && results.length === 0 && <EmptyState title="No search results yet" description="Try a concept, mistake, or doubt keyword." />}
        {!loading && !error && results.map((result) => <LearnerMemoryResultCard key={result.id} result={result} />)}
      </div>
    </section>
  );
}
