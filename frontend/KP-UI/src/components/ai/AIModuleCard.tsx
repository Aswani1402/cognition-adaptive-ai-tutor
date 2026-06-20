import type { ReactNode } from 'react';

export default function AIModuleCard({ title, status, children }: { title: string; status?: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-sm font-black uppercase tracking-wide text-slate-700 dark:text-slate-200">{title}</h3>
        {status && <span className="rounded-full bg-slate-100 px-2 py-1 text-[11px] font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{status}</span>}
      </div>
      <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">{children}</div>
    </section>
  );
}
