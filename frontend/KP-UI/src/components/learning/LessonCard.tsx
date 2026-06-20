import { Link } from 'react-router-dom';
import { BookOpen, ArrowRight } from 'lucide-react';
import { TeachingContent } from '../../lib/types';

export default function LessonCard({ lesson }: { lesson: TeachingContent }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div className="mb-3 flex items-center gap-2 text-sm font-bold text-sky-600"><BookOpen className="h-4 w-4" /> {lesson.difficulty}</div>
      <h3 className="text-xl font-black">{lesson.conceptName}</h3>
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{lesson.adaptiveExplanation}</p>
      <Link to={`/lesson/${lesson.conceptId}`} className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-sky-600">Start lesson <ArrowRight className="h-4 w-4" /></Link>
    </article>
  );
}
