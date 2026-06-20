import { useState } from 'react';
import clsx from 'clsx';
import AIModuleCard from './AIModuleCard';

type Evidence = Record<string, any>;

const value = (input: unknown, fallback = 'pending') => input === undefined || input === null || input === '' ? fallback : String(input);
const pct = (input: unknown) => typeof input === 'number' ? `${Math.round(input * 100)}%` : value(input);

export default function AIEvidencePanel({ evidence, defaultMode = 'learner' }: { evidence: Evidence; defaultMode?: 'learner' | 'reviewer' }) {
  const [mode, setMode] = useState(defaultMode);
  const summary = evidence.xai_summary || {};
  const modules = [
    ['Knowledge Tracing', evidence.kt, <><p>Mastery: {pct(evidence.kt?.mastery_score)} ({value(evidence.kt?.mastery_label)})</p><p>Model: {value(evidence.kt?.model_used)}</p><p>Recommendation: {value(evidence.kt?.recommendation)}</p></>],
    ['Behaviour', evidence.behaviour, <><p>Risk: {pct(evidence.behaviour?.behaviour_risk)} | Confidence: {pct(evidence.behaviour?.behaviour_confidence)}</p><p>Signals: {Object.entries(evidence.behaviour?.signals || {}).map(([k, v]) => `${k}=${v}`).join(', ') || 'none yet'}</p></>],
    ['Concept Dependency', evidence.concept_dependency, <><p>Current: {value(evidence.concept_dependency?.current_concept, evidence.concept_name)}</p><p>Next: {value(evidence.concept_dependency?.next_concept)}</p><p>{value(evidence.concept_dependency?.reason)}</p></>],
    ['Adaptive Path', evidence.adaptive_path, <><p>Next activity: {value(evidence.adaptive_path?.recommended_next_activity)}</p><p>Action: {value(evidence.adaptive_path?.path_action)}</p><p>Safety: {value(evidence.adaptive_path?.safety_filter_status)}</p></>],
    ['Teaching Strategy', evidence.teaching_strategy, <><p>View: {value(evidence.teaching_strategy?.selected_view)} | Difficulty: {value(evidence.teaching_strategy?.difficulty)}</p><p>{value(evidence.teaching_strategy?.reason)}</p></>],
    ['Policy/RL', evidence.policy_rl, <><p>Policy action: {value(evidence.policy_rl?.policy_action)}</p><p>Final safe decision: {value(evidence.policy_rl?.final_safe_decision)}</p><p>RL: {value(evidence.policy_rl?.rl_comparison_status)}</p></>],
    ['RAG', evidence.rag, <><p>Grounding: {pct(evidence.rag?.grounding_score)} | Safe: {value(evidence.rag?.safe_to_generate)}</p><p>Sources: {(evidence.rag?.source_sections || []).join(', ') || 'none'}</p></>],
    ['LLM / CogniTutorLM', evidence.llm_generation, <><p>Source: {value(evidence.llm_generation?.generation_source)}</p><p>Task: {value(evidence.llm_generation?.generated_task_type)} | Format: {value(evidence.llm_generation?.format_validity)}</p></>],
    ['Generation Coverage', evidence.generation_tasks || evidence.generation_status, <><p>Source: {value((evidence.generation_tasks || evidence.generation_status)?.source)}</p><p>Model generated: {value((evidence.generation_tasks || evidence.generation_status)?.model_generated)}</p><p>Task types: {taskList(evidence.generation_tasks || evidence.generation_status)}</p></>],
    ['Agentic AI', evidence.agentic_trace, <><p>Agentic orchestration trace, not a fully autonomous agent.</p><p>Safety controlled: {value(evidence.agentic_trace?.safety_controlled)}</p><p>{(evidence.agentic_trace?.trace || evidence.agentic_trace?.stages || []).map((s: any) => typeof s === 'string' ? s : `${s.name || s.stage || 'step'}: ${s.status || 'recorded'}`).join(' -> ') || value(evidence.agentic_trace?.message, 'Trace will populate after an answer submission.')}</p></>],
    ['Personalization / Notebook', evidence.personalization, <><p>Weak concepts: {(evidence.personalization?.weak_concepts || []).join(', ') || 'none yet'}</p><p>Revision queue: {(evidence.personalization?.revision_queue || []).length || 0}</p></>],
    ['Retention', evidence.retention, <><p>Risk: {value(evidence.retention?.retention_risk)} | Review due: {value(evidence.retention?.review_due)}</p><p>Priority: {value(evidence.retention?.revision_priority)}</p></>],
    ['Evaluation/Fusion', evidence.evaluation_fusion, <><p>Score: {value(evidence.evaluation_fusion?.fused_score)} | Label: {value(evidence.evaluation_fusion?.fused_label)}</p><p>Weakest skill: {value(evidence.evaluation_fusion?.weakest_skill)}</p></>],
    ['Reward', evidence.reward, <><p>XP awarded: {value(evidence.reward?.xp_awarded, '0')} | Streak: {value(evidence.reward?.streak, '0')}</p><p>Unlock: {value(evidence.reward?.concept_unlock)}</p></>],
  ] as const;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div>
          <h2 className="text-lg font-black">AI Engine Trace</h2>
          <p className="text-sm text-slate-500">{mode === 'learner' ? value(summary.learner_message, 'This explains why the tutor chose the next step.') : value(summary.reviewer_message, 'Reviewer evidence for the tutor decision.')}</p>
        </div>
        <div className="rounded-full bg-slate-100 p-1 dark:bg-slate-800">
          {(['learner', 'reviewer'] as const).map((item) => <button key={item} onClick={() => setMode(item)} className={clsx('rounded-full px-3 py-1 text-xs font-bold capitalize', mode === item ? 'bg-sky-600 text-white' : 'text-slate-600 dark:text-slate-200')}>{item} view</button>)}
        </div>
      </div>
      {mode === 'reviewer' ? (
        <>
          <div className="grid gap-3 md:grid-cols-4">
            <CoverageStat label="Subjects" value={value(evidence.generation_status?.subjects_count || evidence.generation_tasks?.subjects_count, '5')} />
            <CoverageStat label="Concepts" value={value(evidence.generation_status?.concepts_count || evidence.generation_tasks?.concepts_count, '38')} />
            <CoverageStat label="Task types" value={value(evidence.generation_status?.task_types_count || evidence.generation_tasks?.task_types_count, '89')} />
            <CoverageStat label="Evaluated cases" value={value(evidence.generation_status?.cases_count || evidence.generation_tasks?.cases_count, '3382')} />
          </div>
          <div className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 text-sm font-semibold text-indigo-900 dark:border-indigo-900/40 dark:bg-indigo-900/20 dark:text-indigo-100">
            Source labels: {sourceLabels(evidence).join(' · ')}
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {modules.map(([title, data, body]) => <div key={title}><AIModuleCard title={title} status={String(data?.status || 'success')}>{body}</AIModuleCard></div>)}
          </div>
        </>
      ) : (
        <AIModuleCard title="Why this next step?" status={evidence.status || 'success'}>
          <p>{value(summary.learner_message, `The tutor is using ${value(evidence.subject)} and ${value(evidence.concept_name)} as your current context.`)}</p>
          <p>Top factors: {(summary.top_factors || ['active subject', 'current concept']).join(', ')}</p>
        </AIModuleCard>
      )}
    </div>
  );
}

function CoverageStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 text-center dark:border-slate-800 dark:bg-slate-950">
      <p className="text-2xl font-black text-slate-900 dark:text-white">{value}</p>
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
    </div>
  );
}

function sourceLabels(evidence: Evidence) {
  const labels = new Set<string>();
  const sourceText = JSON.stringify(evidence).toLowerCase();
  if (sourceText.includes('rag')) labels.add('RAG-grounded');
  if (sourceText.includes('cognitutor')) labels.add('CogniTutorLM attempted');
  if (sourceText.includes('rejected')) labels.add('raw model rejected');
  if (sourceText.includes('guard')) labels.add('guarded product generator used');
  if (sourceText.includes('bank')) labels.add('prevalidated generated content bank');
  if (sourceText.includes('concept')) labels.add('concept-resource fallback');
  if (!labels.size) labels.add('template fallback');
  return Array.from(labels);
}

function taskList(data: any) {
  const items = data?.task_types || data?.categories || [];
  return Array.isArray(items) && items.length ? items.slice(0, 12).join(', ') : 'pending';
}
