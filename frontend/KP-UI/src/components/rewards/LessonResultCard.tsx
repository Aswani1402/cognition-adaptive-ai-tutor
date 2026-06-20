import { LessonResult } from '../../lib/types';
import { Link } from 'react-router-dom';
import { useLearnerSession } from '../../context/LearnerSessionContext';

export default function LessonResultCard({ result }: { result: LessonResult }) {
  const session = useLearnerSession();
  const challengeRoute = session.current_concept_id ? `/puzzle/${session.current_concept_id}` : '/subjects';

  return (
    <div className="rounded-3xl border border-emerald-200 bg-white p-6 dark:border-emerald-900/40 dark:bg-slate-900">
      <h3 className="text-xl font-black">Lesson Result</h3>
      <p className="mt-1 text-sm text-slate-500">Score: {(result.score * 100).toFixed(0)}% | XP gained: {result.xpAwarded}</p>
      <p className="mt-2 text-sm">Correct: {result.correctCount} | Partial: {result.partialCount} | Wrong: {result.wrongCount}</p>
      <p className="mt-2 text-sm">Weak areas: {result.weakAreas.join(', ') || 'None'}</p>
      <p className="mt-2 text-sm font-semibold text-emerald-700 dark:text-emerald-300">Next: {result.nextAction}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to="/progress" className="rounded-xl bg-sky-600 px-3 py-2 text-sm font-semibold text-white">Continue</Link>
        <Link to="/mistakes" className="rounded-xl border border-rose-300 px-3 py-2 text-sm font-semibold text-rose-700 dark:border-rose-900/40 dark:text-rose-300">Review mistakes</Link>
        <Link to={challengeRoute} className="rounded-xl border border-violet-300 px-3 py-2 text-sm font-semibold text-violet-700 dark:border-violet-900/40 dark:text-violet-300">Try challenge</Link>
      </div>
    </div>
  );
}
