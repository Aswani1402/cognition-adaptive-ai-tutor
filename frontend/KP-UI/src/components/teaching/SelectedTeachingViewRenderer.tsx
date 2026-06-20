import { TeachingContent } from '../../lib/types';
import type { ReactNode } from 'react';
import { getConceptDisplayName } from '../../lib/concepts';
import ReadAloudButton from '../common/ReadAloudButton';

export default function SelectedTeachingViewRenderer({ lesson }: { lesson: TeachingContent }) {
  const selected = lesson.selectedView;
  const content = lesson.contentByView?.[selected] || lesson.teachingContent;
  const explanation = content?.beginner_explanation || content?.explanation || content?.concept_intro || lesson.adaptiveExplanation;
  const examples = content?.examples || (content?.example ? [content.example] : []);
  const example = examples[0] || content?.example;
  const code = content?.code || content?.syntax || lesson.workedExample;
  const keyPoints = conciseList(content?.key_points || lesson.keyPoints, 3);
  const commonMistakes = conciseList(content?.common_mistakes || lesson.commonMistakes, 2);
  const why = lesson.whySelected || String(lesson.teachingStrategy?.reason || lesson.xai?.reason || '');

  const views: Record<string, ReactNode> = {
    explanation: <StructuredContent content={content} fallbackExplanation={explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} />,
    explanation_view: <StructuredContent content={content} fallbackExplanation={explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} />,
    definition_view: <StructuredContent content={content} fallbackExplanation={content?.definition || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="definition" />,
    code_view: (
      <div className="space-y-4">
        <GuidedParagraph text={explanation} />
        <pre className="rounded-xl bg-slate-950 p-4 text-sm text-emerald-300 overflow-x-auto"><code>{shortCode(code)}</code></pre>
      </div>
    ),
    simple_example_view: (
      <div className="space-y-4">
        <GuidedParagraph text={explanation} />
        {example && <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-100">{shortText(example, 220)}</p>}
      </div>
    ),
    analogy_view: <GuidedParagraph text={content?.comparison || explanation} />,
    misconception_view: (
      <div className="space-y-3">
        <GuidedParagraph text={explanation} />
        <ul className="list-disc space-y-1 pl-5 text-sm text-rose-700 dark:text-rose-300">
          {commonMistakes.map((item) => <li key={item}>{item}</li>)}
        </ul>
      </div>
    ),
    step_by_step_view: (
      <div className="space-y-3">
        <GuidedParagraph text={explanation} />
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
          {keyPoints.map((item) => <li key={item}>{item}</li>)}
        </ol>
      </div>
    ),
    debug_view: <StructuredContent content={content} fallbackExplanation={content?.debug_explanation || content?.output_tracing_explanation || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="debug" />,
    output_prediction_view: <StructuredContent content={content} fallbackExplanation={content?.output_tracing_explanation || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="output" />,
    transfer_view: <StructuredContent content={content} fallbackExplanation={content?.transfer_context || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="transfer" />,
    challenge_view: <StructuredContent content={content} fallbackExplanation={content?.challenge_context || content?.practice_prompt || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="challenge" />,
    revision_view: <StructuredContent content={content} fallbackExplanation={content?.revision_line || content?.summary || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="revision" />,
    flashcard_view: <StructuredContent content={content} fallbackExplanation={content?.quick_check || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="quick" />,
    mindmap_view: <StructuredContent content={content} fallbackExplanation={content?.summary || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="summary" />,
    voice_script_view: <StructuredContent content={content} fallbackExplanation={lesson.voiceScript || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="explanation" />,
    revision_summary_view: <StructuredContent content={content} fallbackExplanation={content?.revision_line || content?.summary || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="summary" />,
    comparison_view: <StructuredContent content={content} fallbackExplanation={content?.comparison || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="comparison" />,
    real_world_connection_view: <StructuredContent content={content} fallbackExplanation={content?.real_world_use || explanation} examples={examples} code={code} keyPoints={keyPoints} commonMistakes={commonMistakes} focus="real-world" />,
  };

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-10">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">{getConceptDisplayName(lesson.conceptId, content?.title || lesson.conceptName)}</h2>
        <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold uppercase text-slate-500 dark:border-slate-700">
          Current Method: {label(selected)}
        </span>
      </div>
      {views[selected] || (
        <div className="space-y-4">
          <GuidedParagraph text={explanation} />
          {code && <pre className="rounded-xl bg-slate-950 p-4 text-sm text-emerald-300 overflow-x-auto"><code>{shortCode(code)}</code></pre>}
        </div>
      )}
      <div className="mt-4">
        <ReadAloudButton text={`${getConceptDisplayName(lesson.conceptId, lesson.conceptName)}. ${explanation}`} />
      </div>
      <section className="mt-5 rounded-2xl border border-cyan-100 bg-cyan-50 p-4 dark:border-cyan-900/40 dark:bg-cyan-900/20">
        <h3 className="mb-2 text-sm font-black uppercase text-cyan-700 dark:text-cyan-200">Previously learned</h3>
        <ul className="list-disc space-y-1 pl-5 text-sm font-semibold text-cyan-900 dark:text-cyan-100">
          {previousReminders(lesson.conceptId, lesson.subject).map((item) => <li key={item}>{item}</li>)}
        </ul>
      </section>
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
          <h3 className="mb-2 text-sm font-black uppercase text-slate-500">Key points</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700 dark:text-slate-300">
            {keyPoints.map((item) => <li key={item}>{shortText(item, 120)}</li>)}
          </ul>
        </section>
        <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-950">
          <h3 className="mb-2 text-sm font-black uppercase text-slate-500">Example</h3>
          <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">{shortText(example || code, 220)}</p>
        </section>
        <section className="rounded-2xl border border-rose-100 bg-rose-50 p-4 dark:border-rose-900/40 dark:bg-rose-900/10">
          <h3 className="mb-2 text-sm font-black uppercase text-rose-500">Mistakes to avoid</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-rose-700 dark:text-rose-300">
            {commonMistakes.map((item) => <li key={item}>{shortText(item, 120)}</li>)}
          </ul>
        </section>
      </div>
      {why && (
        <div className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm font-semibold text-sky-800 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-200">
          Why this view? {why}
        </div>
      )}
      <div className="mt-6 flex flex-wrap gap-3">
        <a href={`/assessment`} className="rounded-full bg-sky-600 px-5 py-2 text-sm font-bold text-white">Quick Check</a>
        <a href="/notebook" className="rounded-full border border-indigo-200 bg-indigo-50 px-5 py-2 text-sm font-bold text-indigo-700 dark:border-indigo-900/40 dark:bg-indigo-900/20 dark:text-indigo-200">Open Study Guide</a>
        <a href="/tutor/chat" className="rounded-full border border-slate-200 px-5 py-2 text-sm font-bold text-slate-700 dark:border-slate-700 dark:text-slate-200">Ask Tutor</a>
      </div>
    </div>
  );
}

function label(v: string) {
  return v.replace(/_view$/, '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase()) + (v.endsWith('_view') ? ' View' : '');
}

function StructuredContent({
  content,
  fallbackExplanation,
  examples,
  code,
  keyPoints,
  commonMistakes,
  focus,
}: {
  content?: TeachingContent['teachingContent'];
  fallbackExplanation: string;
  examples: string[];
  code: string;
  keyPoints: string[];
  commonMistakes: string[];
  focus?: string;
}) {
  const sections = selectSections(content, fallbackExplanation, examples, code, keyPoints, commonMistakes, focus);

  return (
    <div className="space-y-5">
      {sections.map(([title, value]) => (
        <section key={String(title)} className={focus && String(title).toLowerCase().includes(focus) ? 'rounded-2xl border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-900/40 dark:bg-indigo-900/20' : ''}>
          <h3 className="mb-2 text-sm font-black uppercase tracking-wider text-slate-500">{String(title)}</h3>
          {Array.isArray(value) ? (
            <ul className="list-disc space-y-1 pl-5 text-base leading-7 text-slate-700 dark:text-slate-300">
              {value.slice(0, 6).map((item) => <li key={String(item)}>{shortText(String(item), 140)}</li>)}
            </ul>
          ) : String(title).toLowerCase().includes('code') ? (
            <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-emerald-300"><code>{shortCode(String(value))}</code></pre>
          ) : (
            <GuidedParagraph text={String(value)} />
          )}
        </section>
      ))}
    </div>
  );
}

function selectSections(
  content: TeachingContent['teachingContent'] | undefined,
  fallbackExplanation: string,
  examples: string[],
  code: string,
  keyPoints: string[],
  commonMistakes: string[],
  focus?: string
) {
  const stepItems = content?.step_by_step || keyPoints;
  if (focus === 'definition') return [['Definition', content?.definition || fallbackExplanation], ['Key recall', keyPoints]];
  if (focus === 'debug') return [['Debug focus', content?.debug_explanation || fallbackExplanation], ['Mistake to inspect', commonMistakes], ['Small example', content?.code_or_task_example || code]];
  if (focus === 'output') return [['Trace it', content?.output_tracing_explanation || fallbackExplanation], ['Small example', content?.code_or_task_example || code]];
  if (focus === 'transfer') return [['Transfer prompt', content?.transfer_context || content?.real_world_use || fallbackExplanation], ['One example', examples.slice(0, 1)]];
  if (focus === 'challenge') return [['Challenge prompt', content?.challenge_context || content?.practice_prompt || fallbackExplanation], ['Key recall', keyPoints]];
  if (focus === 'revision' || focus === 'summary') return [['Short recap', content?.revision_line || content?.summary || fallbackExplanation], ['Key recall', keyPoints]];
  if (focus === 'comparison') return [['Analogy / comparison', content?.comparison || fallbackExplanation], ['One example', examples.slice(0, 1)]];
  if (focus === 'real-world') return [['Real-world use', content?.real_world_use || fallbackExplanation], ['One example', examples.slice(0, 1)]];
  if (content?.step_by_step?.length) return [['Step by step', stepItems.slice(0, 5)], ['Quick check', content.quick_check || content.practice_prompt]];
  return [['Guided explanation', fallbackExplanation], ['Key points', keyPoints], ['One example', examples.slice(0, 1).length ? examples.slice(0, 1) : code ? [code] : []]].filter(([, value]) => Array.isArray(value) ? value.length : Boolean(value));
}

function GuidedParagraph({ text }: { text: string }) {
  return <p className="whitespace-pre-wrap text-base leading-7 text-slate-700 dark:text-slate-300">{sentenceLimit(text, 5)}</p>;
}

function sentenceLimit(text: string, max: number) {
  const parts = String(text || '').split(/(?<=[.!?])\s+/).filter(Boolean);
  return (parts.length ? parts.slice(0, max).join(' ') : String(text)).slice(0, 620);
}

function conciseList(items: string[], max: number) {
  return (items || []).map((item) => shortText(String(item), 140)).filter(Boolean).slice(0, max);
}

function shortText(text: string, max: number) {
  const clean = String(text || '').replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max - 1).trim()}...` : clean;
}

function shortCode(code: string) {
  return String(code || '').split('\n').slice(0, 8).join('\n').slice(0, 500);
}

function previousReminders(conceptId: string, subject?: string) {
  const id = conceptId.toUpperCase();
  if (id === 'S1') return ['Data is stored as records.', 'Tables organize related data.', 'Keys help identify rows.'];
  if (id === 'S2') return ['Tables store rows and columns.', 'A database groups related tables.', 'Queries ask the database for data.'];
  if (id === 'P1') return ['A value is information a program can use.', 'Names make values easier to reuse.', 'Programs run instructions in order.'];
  if (id === 'P2') return ['Variables store values by name.', 'Assignment creates or updates a variable.', 'Use clear names for readable code.'];
  if (String(subject || '').toLowerCase().includes('sql')) return ['Tables organize data.', 'Rows are records.', 'Columns describe fields.'];
  return ['Recall the previous definition.', 'Use one small example.', 'Check the expected result.'];
}
