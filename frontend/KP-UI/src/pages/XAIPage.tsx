import { useEffect, useState } from 'react';
import { BrainCircuit } from 'lucide-react';
import { getAgenticTrace, getAIEvidence, getGenerationCoverage, getGenerationTasks, getXAI } from '../lib/api';
import { XAIReflection } from '../lib/types';
import XAIReflectionPanel from '../components/tutor/XAIReflectionPanel';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import AIEvidencePanel from '../components/ai/AIEvidencePanel';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { cleanEvidenceMessage, getConceptDisplayName } from '../lib/concepts';
import { mockXAIReflection } from '../lib/mockData';
import { readLocalProgress } from '../lib/localProgress';
import { logFrontendEvent } from '../lib/eventLog';

export default function XAIPage() {
  const [reflection, setReflection] = useState<XAIReflection | null>(null);
  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null);
  const session = useLearnerSession();

  useEffect(() => {
    logFrontendEvent({ action: 'xai_opened', module: 'xai', status: 'started', summary: 'XAI opened' });
    const learnerId = session.getCurrentLearnerId();
    const conceptId = session.current_concept_id;
    getXAI(learnerId, conceptId).then(setReflection).catch(() => setReflection({
      ...mockXAIReflection,
      learnerId,
      conceptId: conceptId || 'current',
      teachingViewReason: cleanEvidenceMessage(),
      difficultyReason: 'The tutor uses the latest available mastery and behaviour signals.',
      nextActionReason: 'Continue with revision or practice using saved learner context.',
    }));
    Promise.all([
      getAIEvidence(learnerId, conceptId, session.active_subject),
      getAgenticTrace(learnerId),
      getGenerationCoverage(learnerId),
      getGenerationTasks(conceptId, session.active_subject),
    ]).then(([ai, trace, coverage, tasks]) => setEvidence({ ...ai, agentic_trace: (ai.agentic_trace as unknown) || trace, generation_status: coverage, generation_tasks: tasks }))
      .catch(() => setEvidence({
        mastery: 'Available from latest session when live evidence is delayed.',
        behaviour_signal: 'Uses confidence, time, hints, and answer changes when available.',
        selected_next_action: 'Continue guided practice',
        reason: cleanEvidenceMessage(),
        concept: getConceptDisplayName(conceptId, session.current_concept_name),
      }));
  }, [session.active_subject, session.current_concept_id]);

  const localProgress = readLocalProgress();
  const latestAnswer = localStorage.getItem('latest_answer_result');

  if (localProgress.completedQuestions === 0 && !latestAnswer) {
    return (
      <div className="mx-auto w-full max-w-4xl space-y-6 pb-20">
        <CogniGuideCard {...getCogniMessage({ page: 'xai' })} />
        <section className="rounded-3xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-950">
          <BrainCircuit className="mx-auto mb-4 h-10 w-10 text-violet-500" />
          <h1 className="text-2xl font-black">No completed assessment yet</h1>
          <p className="mt-2 text-sm font-semibold text-slate-500">XAI explanation will appear after you answer a question. No old mastery or mistake evidence is shown for a clean learner session.</p>
          <a href="/assessment" className="mt-5 inline-flex rounded-full bg-sky-600 px-5 py-2 text-sm font-bold text-white">Start a quick check</a>
        </section>
      </div>
    );
  }

  if (!reflection) {
    return <LoadingSkeleton title="Loading XAI reflection" description="Preparing explanation and grounding evidence." />;
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-20">
      <CogniGuideCard {...getCogniMessage({ page: 'xai' })} />
      <header className="rounded-3xl border border-violet-200 bg-gradient-to-r from-violet-600 to-sky-600 p-6 text-white">
        <div className="flex items-center gap-3">
          <BrainCircuit className="h-8 w-8" />
          <div>
            <h1 className="text-3xl font-black">XAI Reflection Panel</h1>
            <p className="text-sm text-white/85">Why the tutor selected this strategy, difficulty, and next action.</p>
          </div>
        </div>
      </header>
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <XAIReflectionPanel reflection={reflection} />
        <section className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
          <h2 className="mb-3 text-lg font-black">Safe fallback summary</h2>
          <ul className="space-y-2 text-sm font-semibold text-slate-600 dark:text-slate-300">
            <li>Mastery: latest available learner context</li>
            <li>Behaviour signal: time, confidence, hints, answer changes</li>
            <li>Next action: guided practice or revision</li>
            <li>Grounding: concept resources and saved notebook memory when live evidence is delayed</li>
          </ul>
        </section>
      </div>
      {evidence && <AIEvidencePanel evidence={evidence} defaultMode="reviewer" />}
    </div>
  );
}
