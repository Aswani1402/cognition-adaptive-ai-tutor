import { AssessmentQuestion } from '../../../lib/types';
import type { ReactNode } from 'react';

function FieldList({ title, items }: { title: string; items?: unknown[] }) {
  const values = (items || []).map(String).filter(Boolean);
  if (!values.length) return null;
  return (
    <div>
      <p className="text-xs font-black uppercase text-slate-500">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm font-semibold text-slate-700 dark:text-slate-200">
        {values.slice(0, 4).map((item, index) => <li key={`${title}-${index}`}>{clipText(item, 160)}</li>)}
      </ul>
    </div>
  );
}

function CodeBlock({ code }: { code?: string }) {
  if (!code) return null;
  return <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-100"><code>{code}</code></pre>;
}

function BaseQuestionCard({ question, label, children }: { question: AssessmentQuestion; label: string; children?: ReactNode }) {
  const constraints = Array.isArray(question.constraints) ? question.constraints : [];
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="mb-3 flex flex-wrap gap-2 text-xs font-black uppercase">
        <span className="rounded-md bg-white px-2 py-1 text-slate-600 dark:bg-slate-800 dark:text-slate-200">{label}</span>
        <span className="rounded-md bg-sky-50 px-2 py-1 text-sky-700 dark:bg-sky-900/30 dark:text-sky-200">{question.concept_name || question.sourceConcept}</span>
        <span className="rounded-md bg-emerald-50 px-2 py-1 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-200">{question.evaluation_mode || 'rubric'}</span>
      </div>
      {question.title && <h3 className="mb-2 text-lg font-black text-slate-900 dark:text-white">{question.title}</h3>}
      {question.instructions && <p className="mb-3 text-sm font-semibold leading-6 text-slate-700 dark:text-slate-200">{clipText(question.instructions, 320)}</p>}
      <FieldList title="Requirements" items={constraints} />
      {children}
      {(question.hint || question.hidden_hint) && <p className="mt-3 text-xs font-bold text-amber-700 dark:text-amber-300">Hint available after you click Need a hint?</p>}
      {question.grounding_source_label && <p className="mt-3 text-xs font-bold text-slate-500">Source: {question.grounding_source_label}</p>}
    </div>
  );
}

export function MCQQuestionCard({ question }: { question: AssessmentQuestion }) {
  return (
    <BaseQuestionCard question={question} label="MCQ">
      {!question.options?.length && (
        <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm font-bold text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-100">
          MCQ options not available.
        </p>
      )}
    </BaseQuestionCard>
  );
}

export function DebugQuestionCard({ question }: { question: AssessmentQuestion }) {
  return (
    <BaseQuestionCard question={question} label="Debug">
      <CodeBlock code={question.buggyCode || question.starterCode || question.code || question.code_snippet} />
    </BaseQuestionCard>
  );
}

export function OutputPredictionCard({ question }: { question: AssessmentQuestion }) {
  return (
    <BaseQuestionCard question={question} label="Output Prediction">
      <CodeBlock code={question.code || question.code_snippet || question.starterCode} />
      {question.expectedOutput && <p className="mt-3 text-xs font-bold text-slate-500">Expected output is shown after submit.</p>}
    </BaseQuestionCard>
  );
}

export function SyntaxCompletionCard({ question }: { question: AssessmentQuestion }) {
  return (
    <BaseQuestionCard question={question} label="Syntax Completion">
      <CodeBlock code={question.code || question.starterCode} />
    </BaseQuestionCard>
  );
}

export function CodeWritingCard({ question }: { question: AssessmentQuestion }) {
  return (
    <BaseQuestionCard question={question} label="Coding">
      <CodeBlock code={question.starterCode} />
      {question.expectedOutput && <p className="mt-3 text-sm font-semibold text-slate-600 dark:text-slate-300">Expected behavior/output: {question.expectedOutput}</p>}
    </BaseQuestionCard>
  );
}

export function DragOrderQuestionCard({ question }: { question: AssessmentQuestion }) {
  return <BaseQuestionCard question={question} label="Order Puzzle" />;
}

export function MatchPairsQuestionCard({ question }: { question: AssessmentQuestion }) {
  return <BaseQuestionCard question={question} label="Matching Puzzle" />;
}

export function FillBlankQuestionCard({ question }: { question: AssessmentQuestion }) {
  return <BaseQuestionCard question={question} label="Fill Blank" />;
}

export function ChallengeQuestionCard({ question }: { question: AssessmentQuestion }) {
  return <BaseQuestionCard question={question} label="Challenge" />;
}

export function TransferQuestionCard({ question }: { question: AssessmentQuestion }) {
  const label = String(question.taskType || question.questionType || '').includes('real_world') ? 'Real-world application' : 'Transfer';
  return <BaseQuestionCard question={question} label={label} />;
}

export function ShortExplanationCard({ question }: { question: AssessmentQuestion }) {
  return <BaseQuestionCard question={question} label="Explanation" />;
}

function clipText(value: string, maxChars: number) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  return text.length > maxChars ? `${text.slice(0, maxChars - 3).trim()}...` : text;
}
