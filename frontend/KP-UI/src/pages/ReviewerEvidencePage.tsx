import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Activity, AlertTriangle, FileText, RefreshCw, Server, ShieldCheck } from 'lucide-react';
import { getApiBaseUrl, getAIEvidence, getBackendHealth, getReviewerEvidence } from '../lib/api';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { readFrontendEvents } from '../lib/eventLog';

type LoadState = 'loading' | 'ready' | 'error';

type EvidenceState = {
  reviewer: Record<string, unknown>;
  ai: Record<string, unknown>;
  health: Awaited<ReturnType<typeof getBackendHealth>>;
};

const unavailableMessage = 'Reviewer evidence is not available yet. Run backend evidence report or check backend connection.';

export default function ReviewerEvidencePage() {
  const session = useLearnerSession();
  const [state, setState] = useState<LoadState>('loading');
  const [data, setData] = useState<EvidenceState | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setState('loading');
    setError('');
    const learnerId = session.getCurrentLearnerId();
    try {
      const health = await getBackendHealth();
      const [reviewerResult, aiResult] = await Promise.allSettled([
        getReviewerEvidence(learnerId, session.current_concept_id, session.active_subject),
        getAIEvidence(learnerId, session.current_concept_id, session.active_subject),
      ]);
      setData({
        health,
        reviewer: reviewerResult.status === 'fulfilled' ? safeRecord(reviewerResult.value) : {},
        ai: aiResult.status === 'fulfilled' ? safeRecord(aiResult.value) : {},
      });
      if (reviewerResult.status === 'rejected' && aiResult.status === 'rejected') {
        setError(unavailableMessage);
        setState('error');
      } else {
        setState('ready');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : unavailableMessage);
      setData(null);
      setState('error');
    }
  }, [session]);

  useEffect(() => {
    load();
  }, [load]);

  const evidence = useMemo(() => ({ ...(data?.ai || {}), ...(data?.reviewer || {}) }), [data]);
  const reports = evidenceList(evidence.evaluation_reports || evidence.report_links || evidence.reports);
  const modules = moduleSummary(evidence);
  const rag = safeRecord(evidence.rag_metrics || evidence.rag || evidence.rag_evidence);
  const evaluator = safeRecord(evidence.answer_evaluator_summary || evidence.evaluation_fusion || evidence.evaluator_summary);
  const policy = safeRecord(evidence.policy_safety_summary || evidence.policy_rl || evidence.policy_update);
  const runtime = safeRecord(evidence.runtime_source_verification);
  const frontendEvents = readFrontendEvents().slice(0, 4);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-20">
      <header className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="flex gap-3">
            <div className="grid h-12 w-12 place-items-center rounded-xl bg-slate-900 text-white dark:bg-white dark:text-slate-900">
              <FileText className="h-6 w-6" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Internal reviewer evidence</p>
              <h1 className="text-2xl font-black">Backend Evidence Report</h1>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                This page shows internal evidence, not learner UI.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-sky-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60"
            disabled={state === 'loading'}
          >
            <RefreshCw className={`h-4 w-4 ${state === 'loading' ? 'animate-spin' : ''}`} />
            Retry
          </button>
        </div>
      </header>

      {state === 'loading' && (
        <Notice tone="neutral" icon={<Activity className="h-5 w-5" />} title="Loading reviewer evidence">
          Checking backend status and available evidence routes.
        </Notice>
      )}

      {state === 'error' && (
        <Notice tone="warning" icon={<AlertTriangle className="h-5 w-5" />} title="Evidence unavailable">
          {error || unavailableMessage}
        </Notice>
      )}

      {state !== 'loading' && !data?.health.connected && (
        <Notice tone="warning" icon={<AlertTriangle className="h-5 w-5" />} title="Backend connection">
          {unavailableMessage}
        </Notice>
      )}

      <section className="grid gap-4 lg:grid-cols-2">
        <Panel title="Backend Status" icon={<Server className="h-5 w-5" />}>
          <InfoRow label="Status" value={data?.health.connected ? 'Live backend connected' : data?.health.detail || 'Backend not connected'} />
          <InfoRow label="API base" value={getApiBaseUrl() || 'Not configured'} />
          <InfoRow label="Learner ID" value={session.getCurrentLearnerId() || 'No learner session'} />
          <InfoRow label="Active subject" value={session.active_subject || 'Not selected'} />
          <InfoRow label="Current concept" value={session.current_concept_name || session.current_concept_id || 'Not selected'} />
        </Panel>

        <Panel title="Runtime Source Verification" icon={<ShieldCheck className="h-5 w-5" />}>
          {Object.keys(runtime).length ? (
            <KeyValueList data={runtime} />
          ) : (
            <>
              <InfoRow label="Reviewer route" value={Object.keys(data?.reviewer || {}).length ? 'Available or fallback response returned' : 'No response yet'} />
              <InfoRow label="AI evidence route" value={Object.keys(data?.ai || {}).length ? 'Available or fallback response returned' : 'No response yet'} />
              <InfoRow label="Frontend events" value={frontendEvents.length ? `${frontendEvents.length} recent events found` : 'No frontend events yet'} />
            </>
          )}
        </Panel>

        <Panel title="Module Status Summary">
          {modules.length ? (
            <div className="grid gap-2 sm:grid-cols-2">
              {modules.map((item) => <StatusLine key={item.name} name={item.name} status={item.status} detail={item.detail} />)}
            </div>
          ) : (
            <Empty text="No module status summary is available yet." />
          )}
        </Panel>

        <Panel title="Evaluation Report Links / Status">
          {reports.length ? (
            <ul className="space-y-2 text-sm">
              {reports.slice(0, 12).map((report, index) => (
                <li key={`${report.name}-${index}`} className="rounded-xl bg-slate-50 p-3 font-semibold dark:bg-slate-900">
                  {report.href ? <a className="text-sky-700 dark:text-sky-300" href={report.href}>{report.name}</a> : report.name}
                  {report.status && <span className="ml-2 text-xs text-slate-500">{report.status}</span>}
                </li>
              ))}
            </ul>
          ) : (
            <Empty text="No evaluation report links were returned by the backend." />
          )}
        </Panel>

        <Panel title="RAG Metrics">
          {Object.keys(rag).length ? <KeyValueList data={rag} /> : <Empty text="No RAG metrics available yet." />}
        </Panel>

        <Panel title="Answer Evaluator Summary">
          {Object.keys(evaluator).length ? <KeyValueList data={evaluator} /> : <Empty text="No answer evaluator summary available yet." />}
        </Panel>

        <Panel title="Policy / RL Safety Summary">
          {Object.keys(policy).length ? <KeyValueList data={policy} /> : <Empty text="No policy or RL safety summary available yet." />}
        </Panel>

        <Panel title="Frontend / Backend Connection Evidence">
          <InfoRow label="Frontend route" value="/reviewer/evidence" />
          <InfoRow label="Backend routes used" value="/reviewer/evidence/{learner_id}, /ai/evidence/{learner_id}, /openapi.json" />
          <InfoRow label="Recent frontend event" value={frontendEvents[0] ? `${frontendEvents[0].action} / ${frontendEvents[0].module} / ${frontendEvents[0].status}` : 'No recent frontend event'} />
          <div className="mt-3 flex flex-wrap gap-2">
            <Link className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold dark:border-slate-700" to="/progress">Progress</Link>
            <Link className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold dark:border-slate-700" to="/settings">Settings</Link>
            <Link className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold dark:border-slate-700" to="/revision">Revision</Link>
          </div>
        </Panel>
      </section>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <h2 className="mb-4 flex items-center gap-2 font-black">
        {icon}
        {title}
      </h2>
      {children}
    </section>
  );
}

function Notice({ title, tone, icon, children }: { title: string; tone: 'neutral' | 'warning'; icon: ReactNode; children: ReactNode }) {
  const classes = tone === 'warning'
    ? 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100'
    : 'border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200';
  return (
    <div className={`flex gap-3 rounded-2xl border p-4 ${classes}`}>
      <div className="mt-0.5">{icon}</div>
      <div>
        <p className="font-black">{title}</p>
        <p className="text-sm font-semibold">{children}</p>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="mb-3">
      <p className="text-xs font-black uppercase text-slate-500">{label}</p>
      <p className="break-words text-sm font-semibold text-slate-800 dark:text-slate-100">{formatValue(value)}</p>
    </div>
  );
}

function StatusLine({ name, status, detail }: { name: string; status: string; detail?: string }) {
  return (
    <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-800">
      <p className="font-bold">{name}</p>
      <p className="text-sm text-slate-600 dark:text-slate-300">{status}</p>
      {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="rounded-xl bg-slate-50 p-4 text-sm font-semibold text-slate-600 dark:bg-slate-900 dark:text-slate-300">{text}</p>;
}

function KeyValueList({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="space-y-3">
      {Object.entries(data).slice(0, 12).map(([key, value]) => <InfoRow key={key} label={key.replaceAll('_', ' ')} value={value} />)}
    </div>
  );
}

function safeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function evidenceList(value: unknown): { name: string; href?: string; status?: string }[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (typeof item === 'string') return { name: item };
    const record = safeRecord(item);
    return {
      name: String(record.name || record.title || record.path || record.href || 'Report'),
      href: record.href ? String(record.href) : undefined,
      status: record.status ? String(record.status) : undefined,
    };
  });
}

function moduleSummary(evidence: Record<string, unknown>) {
  const explicit = evidenceList(evidence.module_status_summary).map((item) => ({ name: item.name, status: item.status || 'available', detail: item.href }));
  if (explicit.length) return explicit;
  const modules = [
    ['Knowledge tracing', evidence.kt],
    ['Behaviour', evidence.behaviour],
    ['Concept dependency', evidence.concept_dependency],
    ['Adaptive path', evidence.adaptive_path],
    ['Teaching strategy', evidence.teaching_strategy],
    ['Policy / RL', evidence.policy_rl],
    ['RAG', evidence.rag],
    ['Generation', evidence.llm_generation || evidence.generation_status],
    ['Agentic trace', evidence.agentic_trace],
    ['Personalization', evidence.personalization],
    ['Retention / revision', evidence.retention || evidence.revision_update],
    ['Evaluation fusion', evidence.evaluation_fusion],
    ['Reward', evidence.reward],
  ];
  return modules.map(([name, value]) => {
    const record = safeRecord(value);
    return {
      name: String(name),
      status: String(record.status || (Object.keys(record).length ? 'available' : 'missing')),
      detail: record.reason ? String(record.reason) : undefined,
    };
  });
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null || value === '') return 'Not available';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : 'Not available';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) {
    if (!value.length) return 'None';
    return value.map((item) => typeof item === 'object' ? JSON.stringify(item) : String(item)).join(', ');
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
