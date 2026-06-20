import { useMemo, useState } from 'react';
import { Terminal, Copy, PlayCircle } from 'lucide-react';
import clsx from 'clsx';
import { getAIEvidence, getDemoRun, getGenerationCoverage, getRewardState } from '../lib/api';
import { DemoRunData, RewardState } from '../lib/types';
import AIEvidencePanel from '../components/ai/AIEvidencePanel';
import GenerationCoverageCard from '../components/ai/GenerationCoverageCard';

const profiles = ['beginner', 'average', 'strong'] as const;

type Tab = 'selectedView' | 'assessment' | 'xai' | 'notebook' | 'reward' | 'backend' | 'rag' | 'decision' | 'evaluation' | 'rl' | 'doubt';

export default function DemoPage() {
  const [profile, setProfile] = useState<(typeof profiles)[number]>('beginner');
  const [tab, setTab] = useState<Tab>('evaluation');
  const [ran, setRan] = useState(false);
  const [demoRun, setDemoRun] = useState<DemoRunData | null>(null);
  const [rewardState, setRewardState] = useState<RewardState | null>(null);
  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null);
  const [coverage, setCoverage] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const runDemo = async () => {
    setLoading(true);
    const learnerId = localStorage.getItem('learner_id') || '';
    const [run, rewards, ai, gen] = await Promise.all([getDemoRun(profile), getRewardState(learnerId), getAIEvidence(learnerId, localStorage.getItem('current_concept_id') || undefined, localStorage.getItem('active_subject') || undefined), getGenerationCoverage(learnerId)]);
    setDemoRun(run);
    setRewardState(rewards);
    setEvidence(ai);
    setCoverage(gen);
    setRan(true);
    setLoading(false);
  };

  const payload = useMemo(() => {
    const run = demoRun;
    return {
      selectedView: run?.selectedView ?? 'Run demo to load selected view',
      assessment: run?.assessmentJson ?? {},
      xai: run?.xaiReason ?? 'Run demo to load XAI reason',
      notebook: run?.notebookMemory ?? {},
      reward: rewardState ?? {},
      backend: run?.backendJson ?? {},
      rag: run?.ragSource ?? 'Run demo to load RAG source',
      decision: run?.decisionOutput ?? {},
      evaluation: run?.evaluationOutput ?? {},
      rl: run?.rlOutput ?? {},
      doubt: { source: 'getDemoRun', ragSource: run?.ragSource, nextAction: run?.decisionOutput },
    };
  }, [demoRun, rewardState]);

  const content = JSON.stringify(payload[tab], null, 2);

  return (
    <div className="max-w-7xl mx-auto w-full pb-20 space-y-6">
      <header className="rounded-3xl border border-cyan-200 bg-gradient-to-r from-cyan-500 to-sky-600 p-6 text-white">
        <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3"><Terminal className="h-8 w-8" /><div><h1 className="text-2xl font-black">Demo Mode Controls</h1><p className="text-cyan-50">Reviewer-only panel for inspecting tutor outputs. Sanvia remains comparison-only.</p></div></div>
          <button onClick={runDemo} disabled={loading} className="inline-flex items-center gap-2 rounded-xl bg-white/20 px-4 py-2 text-sm font-semibold disabled:opacity-60"><PlayCircle className="h-4 w-4" />{loading ? 'Running...' : 'Run reviewer demo'}</button>
        </div>
      </header>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <p className="mb-2 text-xs font-bold uppercase text-slate-500">Learner profile</p>
        <div className="flex gap-2">{profiles.map((p) => <button key={p} onClick={() => setProfile(p)} className={clsx('rounded-full px-3 py-1.5 text-sm font-semibold', profile === p ? 'bg-sky-600 text-white' : 'bg-slate-100 dark:bg-slate-800')}>{p}</button>)}</div>
        <p className="mt-2 text-xs text-slate-500">Active profile: {profile} {ran ? '(last run complete)' : ''}</p>
      </div>
      {evidence && <AIEvidencePanel evidence={evidence} defaultMode="reviewer" />}
      {coverage && <GenerationCoverageCard coverage={coverage} />}

      <div className="rounded-3xl border border-slate-200 bg-slate-950 p-0 dark:border-slate-800">
        <div className="flex flex-wrap gap-1 border-b border-slate-800 p-2">{(Object.keys(payload) as Tab[]).map((t) => <button key={t} onClick={() => setTab(t)} className={clsx('rounded-lg px-3 py-1.5 text-xs font-bold uppercase', tab === t ? 'bg-sky-500 text-white' : 'text-slate-300 hover:bg-slate-800')}>{t}</button>)}</div>
        <div className="flex items-center justify-between border-b border-slate-800 px-4 py-2 text-xs text-slate-400"><span>{tab}.json</span><button onClick={() => navigator.clipboard.writeText(content)} className="inline-flex items-center gap-1"><Copy className="h-3 w-3" />Copy</button></div>
        <pre className="max-h-[520px] overflow-auto p-4 text-xs text-slate-200"><code>{content}</code></pre>
      </div>
    </div>
  );
}
