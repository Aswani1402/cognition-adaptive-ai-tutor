import { MistakeReview } from '../../lib/types';
import { getConceptDisplayName } from '../../lib/concepts';

export default function MistakeReviewCard({ mistake }: { mistake: MistakeReview }) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-white p-5 shadow-sm dark:border-rose-900/40 dark:bg-slate-900">
      <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase text-rose-600"><span>{mistake.subject}</span><span>·</span><span>{getConceptDisplayName(mistake.conceptId, mistake.conceptName)}</span><span>·</span><span>{mistake.questionType}</span></div>
      <p className="font-semibold">{mistake.prompt}</p>
      <p className="mt-2 text-sm"><strong>Your answer:</strong> {mistake.learnerAnswer}</p>
      <p className="text-sm"><strong>{isExactTask(mistake.questionType) ? 'Expected answer' : 'Expected idea'}:</strong> {clean(mistake.expectedAnswer) || 'Use the concept rule and the specific requirement from the prompt.'}</p>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{clean(mistake.feedback) || 'Review what was missing, then try one similar question.'}</p>
      <p className="mt-1 text-xs text-slate-500">Focus area: {clean(mistake.misconceptionDetected || mistake.mistakeType) || 'needs review'}</p>
      <button className="mt-3 rounded-xl bg-sky-600 px-3 py-2 text-sm font-semibold text-white">Try similar question</button>
    </div>
  );
}

function isExactTask(type: string) {
  return /mcq|output|syntax|blank|true/i.test(type || '');
}

function clean(value: unknown) {
  let text = String(value || '').replace(/\s+/g, ' ').trim();
  const map: Record<string, string> = {
    weak_answer: 'answer too short or unclear',
    wrong_option: 'incorrect option',
    wrong_output: 'output tracing issue',
    syntax_misunderstanding: 'syntax rule issue',
    debug_error: 'debugging issue',
    none: '',
  };
  Object.entries(map).forEach(([raw, friendly]) => {
    text = text.replace(new RegExp(`\\b${raw}\\b`, 'gi'), friendly);
  });
  return text.trim();
}
