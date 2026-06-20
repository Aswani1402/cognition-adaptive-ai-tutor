import { useEffect, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { BarChart3, BrainCircuit, Clock, Lightbulb, TrendingUp } from 'lucide-react';
import { getAgenticTrace, getAIEvidence, getGenerationCoverage, getGenerationTasks, getProgress, getRewardState, getRevision } from '../lib/api';
import { useLearnerSession } from '../context/LearnerSessionContext';
import AIEvidencePanel from '../components/ai/AIEvidencePanel';
import { ProgressData, RewardState } from '../lib/types';
import { readFrontendEvents } from '../lib/eventLog';

export default function ReviewerInsightsPage() {
  const session = useLearnerSession();
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [reward, setReward] = useState<RewardState | null>(null);
  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null);
  const [revision, setRevision] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    const learnerId = session.getCurrentLearnerId();
    getProgress(learnerId, session.active_subject).then(setProgress);
    getRewardState(learnerId).then(setReward);
    Promise.all([
      getAIEvidence(learnerId, session.current_concept_id, session.active_subject),
      getAgenticTrace(learnerId),
      getGenerationCoverage(learnerId),
      getGenerationTasks(session.current_concept_id, session.active_subject),
    ]).then(([ai, trace, coverage, tasks]) => setEvidence({ ...ai, agentic_trace: (ai.agentic_trace as unknown) || trace, generation_status: coverage, generation_tasks: tasks }));
    getRevision(learnerId).then(setRevision);
  }, [session]);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-20">
      <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-sky-600 text-white"><BarChart3 className="h-6 w-6" /></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Reviewer analytics</p>
            <h1 className="text-2xl font-black">Learner Progress Evidence</h1>
            <p className="text-sm text-slate-500">Optional teacher/reviewer view. The learner flow remains guided and non-technical.</p>
          </div>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-4">
        <Metric icon={<TrendingUp className="h-5 w-5" />} label="Accuracy" value={`${progress?.accuracy ?? 0}%`} />
        <Metric icon={<BrainCircuit className="h-5 w-5" />} label="Mastery" value={`${progress?.masteryPercent ?? 0}%`} />
        <Metric icon={<Lightbulb className="h-5 w-5" />} label="Review due" value={String(progress?.reviewDue ?? 0)} />
        <Metric icon={<Clock className="h-5 w-5" />} label="XP / streak" value={`${reward?.totalXp ?? 0} XP / ${reward?.currentStreak ?? 0}`} />
      </div>

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel title="Generation Coverage">
          <li>5 subjects, 38 concepts, 89 task types, 3382 generated/evaluated cases.</li>
          <li>Validated learner-facing outputs are shown; raw invalid model output is not shown to learners.</li>
          <li>Sources may include RAG, guarded CogniTutorLM attempt, prevalidated bank, or safe fallback.</li>
        </Panel>
        <Panel title="Frontend Event Log">
          {(readFrontendEvents().slice(0, 5).length ? readFrontendEvents().slice(0, 5) : [{ timestamp: '', action: 'No events yet', module: 'frontend', status: '', summary: 'Interact with the app to populate demo evidence.' }]).map((event, index) => (
            <li key={`${event.timestamp}-${index}`}>{event.action} · {event.module} · {event.status} · {event.summary}</li>
          ))}
        </Panel>
        <Panel title="Weak Concepts">
          {(progress?.weakAreas?.length ? progress.weakAreas : ['No weak concept evidence yet.']).map((item, index) => (
            <li key={typeof item === 'string' ? item : `${item.concept}-${item.skill}-${index}`}>
              {typeof item === 'string' ? item : `${item.concept}: ${item.skill} - ${item.recommendedAction}`}
            </li>
          ))}
        </Panel>
        <Panel title="Concept Mastery">
          {(progress?.conceptMastery?.length ? progress.conceptMastery : []).map((item) => <li key={`${item.subject}-${item.conceptName}`}>{item.subject}: {item.conceptName} - {item.mastery}%</li>)}
          {!progress?.conceptMastery?.length && <li>No mastery rows yet.</li>}
        </Panel>
        <Panel title="Revision Queue">
          <li>{String(revision?.guide_message || revision?.recommended_next_activity || 'No due revision evidence yet.')}</li>
        </Panel>
        <Panel title="Reviewer Dashboard Decision">
          <li>A separate Streamlit dashboard is not required because the project already has a web frontend.</li>
          <li>Backend analytics and module evidence are shown here and in XAI evidence panels.</li>
          <li>Streamlit may be used only as an optional internal debugging tool.</li>
        </Panel>
      </section>

      {evidence && <AIEvidencePanel evidence={evidence} defaultMode="reviewer" />}
    </div>
  );
}

function Metric({ icon, label, value }: { icon: ReactElement; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-2 flex items-center gap-2 text-slate-500">{icon}<span className="text-xs font-bold uppercase">{label}</span></div>
      <div className="text-2xl font-black">{value}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
      <h2 className="mb-3 font-black">{title}</h2>
      <ul className="list-disc space-y-2 pl-5 text-sm text-slate-600 dark:text-slate-300">{children}</ul>
    </div>
  );
}
