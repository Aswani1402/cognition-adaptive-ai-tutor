import { useEffect, useMemo, useState, type FC } from 'react';
import { AlertCircle, FileCode2, Target, CheckCircle2, RefreshCw, Layers, Sparkles } from 'lucide-react';
import { AssessmentQuestion, MistakeReview } from '../lib/types';
import { getMistakeReview, getSimilarQuestion } from '../lib/api';
import MistakeReviewCard from '../components/assessment/MistakeReviewCard';
import AssessmentRenderer from '../components/assessment/AssessmentRenderer';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';

const defaultSubjectFilters = ['All', 'Python', 'SQL / Database', 'HTML/Web Basics', 'Git', 'Data Structures'];
const typeFilters = ['All', 'Debug', 'Output prediction', 'Syntax', 'Concept'];

export default function MistakesPage() {
  const session = useLearnerSession();
  const [mistakes, setMistakes] = useState<MistakeReview[]>([]);
  const [similarQuestion, setSimilarQuestion] = useState<AssessmentQuestion | null>(null);
  const [similarLoadingId, setSimilarLoadingId] = useState<string | null>(null);
  const [similarMessage, setSimilarMessage] = useState('');
  const [subjectFilter, setSubjectFilter] = useState('All');
  const [typeFilter, setTypeFilter] = useState('All');

  useEffect(() => {
    getMistakeReview(session.getCurrentLearnerId()).then((res) => {
      const cleanStart = localStorage.getItem('cognitutor_clean_start') === 'true';
      const local = JSON.parse(localStorage.getItem('cognitutor_local_progress') || '{}') as { completedQuestions?: number };
      setMistakes(cleanStart && !local.completedQuestions ? [] : res ?? []);
    });
  }, [session]);

  const trySimilar = async (mistake: MistakeReview) => {
    setSimilarLoadingId(mistake.mistakeId);
    setSimilarMessage('');
    const question = await getSimilarQuestion({
      learner_id: session.getCurrentLearnerId(),
      concept_id: mistake.conceptId,
      concept_name: mistake.conceptName,
      subject: mistake.subject,
      weakness: mistake.misconceptionDetected || mistake.mistakeType,
      question_type: mistake.questionType,
      difficulty: 'medium',
    });
    setSimilarQuestion(question);
    setSimilarMessage(question ? '' : 'No similar question available yet.');
    setSimilarLoadingId(null);
  };

  const subjectFilters = useMemo(() => {
    const active = session.active_subject;
    return active ? Array.from(new Set(['All', active, ...defaultSubjectFilters.filter((s) => s !== active)])) : defaultSubjectFilters;
  }, [session.active_subject]);

  const filteredMistakes = useMemo(() => {
    return mistakes.filter((m) => {
      if (!isUnresolvedMistake(m)) return false;
      const subjectMatch = subjectFilter === 'All' || m.subject === subjectFilter;
      const typeMatch = typeFilter === 'All' || m.questionType.toLowerCase() === typeFilter.toLowerCase();
      return subjectMatch && typeMatch;
    });
  }, [mistakes, subjectFilter, typeFilter]);

  return (
    <div className="max-w-5xl mx-auto w-full pb-20 space-y-6">
      <header className="bg-rose-50 dark:bg-rose-900/10 rounded-3xl p-8 border border-rose-100 dark:border-rose-900/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-rose-500 flex items-center justify-center text-white"><AlertCircle className="w-8 h-8" /></div>
          <div>
            <h1 className="text-3xl font-black">Review Mistakes</h1>
            <p className="text-rose-700 dark:text-rose-300 font-medium">Clear your backlog of {filteredMistakes.length} unresolved mistakes.</p>
          </div>
        </div>
        <button disabled={!filteredMistakes.length} className="px-8 py-3 bg-rose-600 hover:bg-rose-700 text-white rounded-full font-bold flex items-center gap-2 disabled:opacity-50"><RefreshCw className="w-4 h-4" /> Practice All</button>
      </header>

      <div className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-slate-500"><Layers className="w-4 h-4" /> Subject filter</div>
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">{subjectFilters.map((s) => <FilterButton key={s} active={subjectFilter === s} onClick={() => setSubjectFilter(s)}>{s}</FilterButton>)}</div>
        <div className="flex items-center gap-2 text-sm text-slate-500 mt-3"><Layers className="w-4 h-4" /> Question type filter</div>
        <div className="flex gap-2 overflow-x-auto scrollbar-hide">{typeFilters.map((s) => <FilterButton key={s} active={typeFilter === s} onClick={() => setTypeFilter(s)}>{s}</FilterButton>)}</div>
      </div>

      <div className="space-y-6">
        {filteredMistakes.map((mistake) => (
          <div key={mistake.mistakeId} className="space-y-4">
            <MistakeReviewCard mistake={mistake} />
            <div className="bg-white dark:bg-slate-950 p-6 sm:p-8 rounded-3xl border border-slate-200 dark:border-slate-800 flex flex-col md:flex-row gap-8 items-start shadow-sm">
            <div className="flex-1 w-full space-y-4">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-bold uppercase">{mistake.subject} · {getConceptDisplayName(mistake.conceptId, mistake.conceptName)} · {mistake.questionType}</span>
                <span className="text-sm font-bold text-slate-500 flex items-center gap-1.5"><Target className="w-4 h-4" /> {getConceptDisplayName(mistake.conceptId, mistake.conceptName)}</span>
                <Badge>{mistake.mistakeType}</Badge>
                <Badge>{mistake.severity}</Badge>
              </div>
              <p className="font-semibold">Question: {mistake.prompt}</p>
              <AnswerBox title="Learner answer" tone="rose">{mistake.learnerAnswer}</AnswerBox>
              <div className="bg-sky-50 dark:bg-sky-900/10 p-4 rounded-2xl border border-sky-100 dark:border-sky-900/30">
                <p className="text-sm font-bold text-sky-800 dark:text-sky-300 mb-2 flex items-center gap-2"><Sparkles className="w-4 h-4" /> Feedback</p>
                <p className="text-sm">{mistake.feedback}</p>
                <p className="text-sm mt-2"><strong>Expected answer:</strong> {mistake.expectedAnswer}</p>
                <p className="text-sm mt-2"><strong>Misconception:</strong> {mistake.misconceptionDetected}</p>
              </div>
            </div>
            <div className="w-full md:w-auto flex flex-col gap-3 shrink-0">
              <button onClick={() => trySimilar(mistake)} disabled={similarLoadingId === mistake.mistakeId} className="w-full px-6 py-3.5 bg-sky-600 hover:bg-sky-700 text-white rounded-xl font-bold text-sm flex items-center justify-center gap-2 disabled:opacity-60"><FileCode2 className="w-4 h-4" /> {similarLoadingId === mistake.mistakeId ? 'Loading...' : 'Try similar question'}</button>
              <button className="w-full px-6 py-3.5 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-900/40 rounded-xl font-bold text-sm">Mark as learned</button>
            </div>
            </div>
          </div>
        ))}

        {similarQuestion && (
          <div className="rounded-3xl border border-sky-200 bg-sky-50 p-5 dark:border-sky-900/40 dark:bg-sky-900/10">
            <h2 className="mb-4 text-xl font-black">Similar aligned question</h2>
            <AssessmentRenderer question={similarQuestion} onComplete={() => undefined} />
          </div>
        )}
        {similarMessage && <p className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">{similarMessage}</p>}

        {filteredMistakes.length === 0 && <div className="text-center py-20 bg-slate-50 dark:bg-slate-950 rounded-3xl border border-slate-200 dark:border-slate-800 border-dashed"><CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" /><h3 className="text-xl font-bold mb-2">No unresolved mistakes yet. Great work!</h3><p className="text-slate-500">Correct and resolved records are hidden from the learner view.</p></div>}
      </div>
    </div>
  );
}

const FilterButton: FC<{ active: boolean; onClick: () => void; children: string }> = ({ active, onClick, children }) => {
  return <button onClick={onClick} className={`px-4 py-2 rounded-full font-bold text-sm shrink-0 ${active ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900' : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'}`}>{children}</button>;
};

function Badge({ children }: { children: string }) {
  return <span className="px-2 py-1 text-xs rounded-md bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-900/30">{children}</span>;
}

function AnswerBox({ title, tone, children }: { title: string; tone: 'rose'; children: string }) {
  return <div className="bg-rose-50 dark:bg-rose-900/10 p-4 rounded-2xl border border-rose-100 dark:border-rose-900/30"><p className="text-sm font-bold text-rose-800 dark:text-rose-300 mb-2">{title}</p><div className="font-mono text-sm text-rose-700 dark:text-rose-400">{children}</div></div>;
}

function isUnresolvedMistake(mistake: MistakeReview) {
  const raw = mistake as MistakeReview & Record<string, unknown>;
  const learnerAnswer = String(mistake.learnerAnswer || raw.learner_answer || '').trim().toLowerCase();
  const expectedAnswer = String(mistake.expectedAnswer || raw.expected_answer || raw.correct_answer || '').trim().toLowerCase();
  const feedback = String(mistake.feedback || '').toLowerCase();
  const misconception = String(mistake.misconceptionDetected || raw.misconception || '').trim().toLowerCase();
  const score = Number(raw.score ?? raw.mastery_score ?? Number.NaN);
  const isCorrect = raw.is_correct === true || raw.correct === true;
  if (isCorrect) return false;
  if (!Number.isNaN(score) && score >= 0.8) return false;
  if (feedback.includes('correct')) return false;
  if (misconception === 'none') return false;
  if (learnerAnswer && expectedAnswer && learnerAnswer === expectedAnswer) return false;
  const mistakeType = String(mistake.mistakeType || raw.mistake_type || '').toLowerCase();
  const realTypes = ['wrong_option', 'weak_answer', 'syntax_misunderstanding', 'wrong_output', 'incomplete_answer'];
  return realTypes.some((type) => mistakeType.includes(type)) || Boolean(misconception && misconception !== 'none') || (!Number.isNaN(score) && score < 0.8);
}
