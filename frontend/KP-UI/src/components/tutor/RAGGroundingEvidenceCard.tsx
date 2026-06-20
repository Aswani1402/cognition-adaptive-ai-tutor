import { CheckCircle2, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';
import { RAGGroundingEvidence } from '../../lib/types';

export default function RAGGroundingEvidenceCard({ evidence }: { evidence: RAGGroundingEvidence }) {
  const supported = evidence.verdict === 'supported';

  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-black">RAG grounding evidence</h3>
          <p className="text-xs text-slate-500">Source support and generation safety</p>
        </div>
        <span className={clsx('inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-black uppercase', supported ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300')}>
          {supported ? <CheckCircle2 className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
          {evidence.verdict.replace('_', ' ')}
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-900">
          <p className="text-xs font-bold uppercase text-slate-500">Support score</p>
          <p className="mt-1 text-2xl font-black">{Math.round(evidence.supportScore * 100)}%</p>
        </div>
        <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-900">
          <p className="text-xs font-bold uppercase text-slate-500">Safe to generate</p>
          <p className="mt-1 text-2xl font-black">{evidence.safeToGenerate ? 'Yes' : 'No'}</p>
        </div>
      </div>

      <div className="mt-4">
        <p className="text-xs font-bold uppercase text-slate-500">Evidence sections used</p>
        <div className="mt-2 flex flex-wrap gap-2">{evidence.evidenceSectionsUsed.map((section) => <span key={section} className="rounded-full bg-sky-50 px-3 py-1 text-xs font-bold text-sky-700 dark:bg-sky-900/30 dark:text-sky-300">{section}</span>)}</div>
      </div>

      {evidence.unsupportedTerms.length > 0 && (
        <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900/40 dark:bg-amber-900/20">
          Unsupported terms: {evidence.unsupportedTerms.join(', ')}
        </div>
      )}

      <div className="mt-4 space-y-2">
        {evidence.retrievedSourceSnippets.map((source) => (
          <div key={`${source.sourceId}-${source.section}`} className="rounded-2xl border border-slate-200 p-3 text-sm dark:border-slate-800">
            <p className="text-xs font-black text-slate-500">{source.sourceId} - {source.section}</p>
            <p className="mt-1 text-slate-700 dark:text-slate-300">{source.snippet}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
