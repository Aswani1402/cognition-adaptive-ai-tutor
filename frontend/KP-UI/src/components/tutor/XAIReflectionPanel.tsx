import { Brain, GitBranch, GraduationCap, Scale, Sparkles } from 'lucide-react';
import type { ReactNode } from 'react';
import { XAIReflection } from '../../lib/types';
import RAGGroundingEvidenceCard from './RAGGroundingEvidenceCard';

export default function XAIReflectionPanel({ reflection }: { reflection: XAIReflection }) {
  return (
    <section className="space-y-4">
      <div className="rounded-3xl border border-violet-200 bg-violet-50 p-5 dark:border-violet-900/40 dark:bg-violet-900/20">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-violet-600 dark:text-violet-300" />
          <h2 className="text-xl font-black">XAI reflection</h2>
          <span className="ml-auto rounded-full bg-white px-3 py-1 text-xs font-bold text-violet-700 dark:bg-slate-950 dark:text-violet-300">{reflection.surrogateModel}</span>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Reason icon={<Brain className="h-4 w-4" />} title="Teaching view" body={reflection.teachingViewReason} />
          <Reason icon={<Scale className="h-4 w-4" />} title="Difficulty" body={reflection.difficultyReason} />
          <Reason icon={<GraduationCap className="h-4 w-4" />} title="Promotion" body={reflection.promotionReason} />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
          <h3 className="mb-3 flex items-center gap-2 font-black"><GitBranch className="h-4 w-4 text-sky-500" /> Top model factors</h3>
          <div className="space-y-3">
            {reflection.topFactors.map((factor) => (
              <div key={factor.factor}>
                <div className="flex justify-between gap-3 text-sm font-bold"><span>{factor.factor}</span><span>{Math.round(factor.weight * 100)}%</span></div>
                <div className="mt-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800"><div className="h-2 rounded-full bg-sky-500" style={{ width: `${Math.round(factor.weight * 100)}%` }} /></div>
                <p className="mt-1 text-xs text-slate-500">{factor.impact}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <h3 className="font-black">Counterfactual</h3>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{reflection.counterfactual}</p>
          </div>
          <div className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <h3 className="font-black">Teacher evidence</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-300">{reflection.teacherEvidence.map((item) => <li key={item}>{item}</li>)}</ul>
            <p className="mt-3 rounded-2xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-200">Next action: {reflection.nextActionReason}</p>
          </div>
        </div>
      </div>

      <RAGGroundingEvidenceCard evidence={reflection.ragEvidence} />
    </section>
  );
}

function Reason({ icon, title, body }: { icon: ReactNode; title: string; body: string }) {
  return (
    <div className="rounded-2xl bg-white p-4 dark:bg-slate-950">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-black">{icon}{title}</h3>
      <p className="text-sm text-slate-600 dark:text-slate-300">{body}</p>
    </div>
  );
}
