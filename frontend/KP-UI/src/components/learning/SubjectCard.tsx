import type { FC, ReactNode } from 'react';
import { ArrowRight, BookOpen, Code2, Database, FileCode2, GitBranch, Globe, Network } from 'lucide-react';
import clsx from 'clsx';
import { Subject } from '../../lib/types';

const iconMap: Record<string, ReactNode> = {
  Code: <FileCode2 className="w-8 h-8" />,
  Code2: <Code2 className="w-8 h-8" />,
  FileCode2: <FileCode2 className="w-8 h-8" />,
  Database: <Database className="w-8 h-8" />,
  Globe: <Globe className="w-8 h-8" />,
  GitBranch: <GitBranch className="w-8 h-8" />,
  Network: <Network className="w-8 h-8" />,
};

const subjectVisuals: Record<string, { icon: string; color: string; glow: string }> = {
  python: { icon: 'Code2', color: 'bg-sky-600 hover:bg-sky-700', glow: 'bg-sky-500' },
  'sql / database': { icon: 'Database', color: 'bg-indigo-600 hover:bg-indigo-700', glow: 'bg-indigo-500' },
  sql: { icon: 'Database', color: 'bg-indigo-600 hover:bg-indigo-700', glow: 'bg-indigo-500' },
  database: { icon: 'Database', color: 'bg-indigo-600 hover:bg-indigo-700', glow: 'bg-indigo-500' },
  'html/web basics': { icon: 'Globe', color: 'bg-orange-500 hover:bg-orange-600', glow: 'bg-orange-500' },
  html: { icon: 'Globe', color: 'bg-orange-500 hover:bg-orange-600', glow: 'bg-orange-500' },
  git: { icon: 'GitBranch', color: 'bg-pink-600 hover:bg-pink-700', glow: 'bg-pink-500' },
  'data structures': { icon: 'Network', color: 'bg-emerald-600 hover:bg-emerald-700', glow: 'bg-emerald-500' },
  dsa: { icon: 'Network', color: 'bg-emerald-600 hover:bg-emerald-700', glow: 'bg-emerald-500' },
};

function visualFor(subject: Subject) {
  const normalizedName = subject.name.trim().toLowerCase();
  const normalizedId = subject.id.trim().toLowerCase();
  return subjectVisuals[normalizedName] || subjectVisuals[normalizedId] || {
    icon: subject.icon || 'BookOpen',
    color: 'bg-slate-700 hover:bg-slate-800',
    glow: 'bg-slate-500',
  };
}

const SubjectCard: FC<{ subject: Subject; onSelect?: (subject: Subject) => void; loading?: boolean }> = ({ subject, onSelect, loading }) => {
  const isNew = subject.progress === 0;
  const isDone = subject.progress === 100;
  const visual = visualFor(subject);
  const icon = iconMap[visual.icon] || iconMap[subject.icon] || <BookOpen className="w-8 h-8" />;

  return (
    <article className="group relative bg-white dark:bg-slate-950 rounded-3xl border border-slate-200 dark:border-slate-800 p-8 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 flex flex-col h-full overflow-hidden">
      <div className={clsx('absolute top-0 right-0 w-32 h-32 opacity-10 blur-3xl -z-10 rounded-full', visual.glow)} />
      <div className="flex justify-between items-start mb-6">
        <div className={clsx('text-white w-16 h-16 rounded-2xl flex items-center justify-center shadow-lg transform -rotate-3 group-hover:rotate-0 transition-transform', visual.color)}>
          {icon}
        </div>
        <div className={clsx('px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider', isNew ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400' : isDone ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400' : 'bg-indigo-100 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-400')}>
          {isNew ? 'New' : isDone ? 'Mastered' : 'In Progress'}
        </div>
      </div>
      <h3 className="text-2xl font-black mb-1 text-slate-900 dark:text-white">{subject.name}</h3>
      <p className="text-sm font-medium text-slate-500 mb-6">{subject.description || `${subject.totalConcepts} Core Concepts`}</p>
      <div className="mt-auto space-y-6">
        <div>
          <div className="flex justify-between text-sm font-bold mb-2"><span className="text-slate-500">Mastery</span><span>{subject.progress}%</span></div>
          <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden"><div className={clsx('h-full rounded-full', visual.color)} style={{ width: `${subject.progress}%` }} /></div>
        </div>
        <button
          onClick={() => onSelect?.(subject)}
          disabled={loading}
          className={clsx('flex w-full items-center justify-center gap-2 py-4 rounded-2xl text-white font-bold transition-all shadow-sm active:scale-95 group-hover:shadow-lg disabled:cursor-wait disabled:opacity-60', visual.color)}
        >
          {loading ? 'Starting...' : 'Start Guided Session'} <ArrowRight className="w-5 h-5" />
        </button>
      </div>
    </article>
  );
};

export default SubjectCard;
