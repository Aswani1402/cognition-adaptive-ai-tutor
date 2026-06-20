import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Brain, Check, Crown, Lock, Puzzle, Sparkles, Swords, Target, Trophy } from 'lucide-react';
import clsx from 'clsx';
import { getLearningPath, getProgressionResult } from '../lib/api';
import { ConceptNode, ProgressionResult } from '../lib/types';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName, getFallbackPath } from '../lib/concepts';

const statusStyle: Record<string, { shell: string; pill: string; label: string }> = {
  mastered: { shell: 'from-[#2FC26E] to-[#26AE62] shadow-[#2FC26E]/30', pill: 'bg-[#DCF9E8] text-[#15803D]', label: 'Mastered' },
  completed: { shell: 'from-[#2FC26E] to-[#26AE62] shadow-[#2FC26E]/30', pill: 'bg-[#DCF9E8] text-[#15803D]', label: 'Completed' },
  current: { shell: 'from-[#21B8F9] to-[#198FE6] shadow-[#21B8F9]/30 ring-4 ring-[#21B8F9]/25', pill: 'bg-[#DDF5FF] text-[#0369A1]', label: 'Current' },
  unlocked: { shell: 'from-[#7B61FF] to-[#6448EE] shadow-[#7B61FF]/30', pill: 'bg-[#EEE9FF] text-[#5B43D6]', label: 'Unlocked' },
  review_due: { shell: 'from-[#FF9E2C] to-[#F08800] shadow-[#FF9E2C]/30', pill: 'bg-[#FFF1DC] text-[#B45309]', label: 'Review' },
  challenge: { shell: 'from-[#FF6B8A] to-[#F24F75] shadow-[#FF6B8A]/30', pill: 'bg-[#FFE3EA] text-[#BE123C]', label: 'Challenge' },
  locked: { shell: 'from-slate-300 to-slate-400 dark:from-slate-700 dark:to-slate-800 shadow-slate-300/20', pill: 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-300', label: 'Locked' },
};

function iconFor(node: ConceptNode) {
  if (node.status === 'locked') return <Lock className="h-6 w-6" />;
  if (node.status === 'mastered' || node.status === 'completed') return <Check className="h-6 w-6" />;
  if (node.type === 'challenge') return <Swords className="h-6 w-6" />;
  if (node.type === 'revision') return <Brain className="h-6 w-6" />;
  if (node.type === 'practice') return <Puzzle className="h-6 w-6" />;
  if (node.type === 'boss') return <Crown className="h-6 w-6" />;
  return <Target className="h-6 w-6" />;
}

function progressRing(node: ConceptNode) {
  if (node.status === 'mastered' || node.status === 'completed') return 100;
  if (node.status === 'current') return 62;
  if (node.status === 'review_due') return 76;
  if (node.status === 'unlocked') return 18;
  return 0;
}

export default function LearningPathPage() {
  const { subjectId } = useParams();
  const navigate = useNavigate();
  const [nodes, setNodes] = useState<ConceptNode[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [progression, setProgression] = useState<ProgressionResult | null>(null);
  const session = useLearnerSession();

  useEffect(() => {
    const subject = session.active_subject || subjectId;
    if (!subject) {
      navigate('/subjects');
      return;
    }
    const learnerId = session.getCurrentLearnerId();
    Promise.all([getLearningPath(learnerId, subject), getProgressionResult(learnerId, session.current_concept_id || subject)])
      .then(([data, progressionResult]) => {
      const base = data.length ? data : getFallbackNodes(subject);
      const named = base.map((node, index) => ({
        ...node,
        name: getConceptDisplayName(node.id, node.name),
        status: node.status || (index === 0 ? 'current' : 'locked'),
      })) as ConceptNode[];
      const enriched = [...named, { id: 'boss-1', name: 'Unit Boss Battle', subjectId: subject, status: 'locked', type: 'boss', difficulty: 'hard', dependsOn: [named[named.length - 1]?.id || ''] } as ConceptNode];
      setNodes(enriched);
      setProgression(progressionResult);
      setActive(enriched.find((n) => n.status === 'current')?.id ?? enriched[0]?.id ?? null);
      setLoading(false);
    }).catch(() => {
      const fallback = getFallbackNodes(subject);
      setNodes(fallback);
      setProgression({ currentConcept: fallback[0].id, currentDifficulty: 'easy', passed: false, nextDifficulty: 'medium', conceptCleared: false, nextConceptUnlocked: fallback[1]?.id || null, message: 'This content is being prepared. Showing saved learning content instead.' });
      setActive(fallback[0].id);
      setLoading(false);
    });
  }, [navigate, subjectId, session.active_subject, session.current_concept_id]);

  const indexed = useMemo(() => nodes.map((node, idx) => ({ node, idx, offset: (idx % 2 === 0 ? -1 : 1) * 70 })), [nodes]);

  if (loading) {
    return <div className="grid h-[55vh] place-items-center text-slate-500">Loading your learning journey...</div>;
  }

  return (
    <div className="mx-auto w-full max-w-3xl pb-32">
      <header className="mb-6 rounded-[28px] border border-[#B6F0CD] bg-gradient-to-r from-[#2FC26E] via-[#21B8F9] to-[#7B61FF] p-6 text-white shadow-xl shadow-sky-500/15">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="inline-flex items-center gap-1 rounded-full bg-white/20 px-3 py-1 text-xs font-bold uppercase tracking-wider"><Sparkles className="h-3.5 w-3.5" /> Adaptive Unit</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight">{session.active_subject || subjectId || 'Selected Subject'} Path</h1>
            <p className="mt-1 text-sm text-white/90">Progressive lesson ladder with review and challenge nodes.</p>
          </div>
          <div className="rounded-2xl bg-white/15 px-4 py-3 text-center backdrop-blur-sm">
            <p className="text-xs font-semibold uppercase">Milestone</p>
            <p className="text-lg font-black">Unit 1</p>
          </div>
        </div>
      </header>

      <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800 dark:border-emerald-900/40 dark:bg-emerald-900/20 dark:text-emerald-200">
        {progression?.message || 'Continue your adaptive path.'}
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {['mastered', 'current', 'review_due', 'challenge'].map((k) => (
          <div key={k} className={clsx('rounded-xl px-3 py-2 text-center text-xs font-bold', statusStyle[k].pill)}>{statusStyle[k].label}</div>
        ))}
      </div>

      <div className="relative rounded-[28px] border border-slate-200 bg-white/80 p-6 shadow-sm backdrop-blur dark:border-slate-800 dark:bg-slate-900/70">
        <div className="pointer-events-none absolute bottom-8 left-1/2 top-8 w-3 -translate-x-1/2 rounded-full bg-slate-100 dark:bg-slate-800" />

        <div className="space-y-8">
          {indexed.map(({ node, idx, offset }) => {
            const style = statusStyle[node.status] ?? statusStyle.locked;
            const isActive = active === node.id;
            const isLocked = node.status === 'locked';
            const isCurrent = node.status === 'current';
            const isCompleted = node.status === 'mastered' || node.status === 'completed' || node.status === 'review_due';
            const canStart = isCurrent;
            const canReview = isCurrent || isCompleted;
            const canAssess = isCurrent;
            return (
              <div key={node.id} className="relative flex items-center justify-center">
                <button
                  onClick={() => setActive(node.id)}
                  aria-disabled={isLocked}
                  className={clsx(
                    'relative z-10 grid h-[86px] w-[86px] place-items-center rounded-full bg-gradient-to-b text-white shadow-xl transition hover:scale-105',
                    style.shell,
                    node.status === 'current' && 'animate-[pathCurrent_2s_ease-in-out_infinite]',
                    node.status === 'unlocked' && 'animate-[pathUnlock_2.8s_ease-in-out_infinite]',
                    isLocked && 'opacity-80 hover:scale-100'
                  )}
                  style={{ transform: `translateX(${offset}px)` }}
                >
                  {node.status !== 'locked' && (
                    <svg className="absolute -inset-2 h-[102px] w-[102px] -rotate-90" viewBox="0 0 102 102" aria-hidden>
                      <circle cx="51" cy="51" r="45" fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth="5" />
                      <circle
                        cx="51"
                        cy="51"
                        r="45"
                        fill="none"
                        stroke="#FFD54A"
                        strokeLinecap="round"
                        strokeWidth="5"
                        strokeDasharray={`${(progressRing(node) / 100) * 282.7} 282.7`}
                        className="animate-[pathRing_1.2s_ease-out_both]"
                      />
                    </svg>
                  )}
                  {node.status === 'unlocked' && (
                    <span className="absolute -right-1 -top-1 h-5 w-5 rounded-full bg-amber-300 animate-[unlockPing_1.6s_ease-out_infinite]" />
                  )}
                  {iconFor(node)}
                  {node.status === 'current' && <span className="absolute -bottom-2 rounded-full bg-[#FFD54A] px-2 py-0.5 text-[10px] font-black text-[#6B4A00]">NOW</span>}
                </button>
                {isLocked && node.lockedReason && !isActive && (
                  <button
                    type="button"
                    onClick={() => setActive(node.id)}
                    className="absolute left-1/2 top-[92px] z-20 w-[min(260px,calc(100vw-3rem))] -translate-x-1/2 rounded-xl bg-slate-100 px-3 py-1.5 text-[11px] font-semibold text-slate-600 shadow-sm transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  >
                    {node.lockedReason}
                  </button>
                )}

                {isActive && (
                  <div className="absolute left-1/2 top-[96px] z-30 w-[min(320px,calc(100vw-2rem))] -translate-x-1/2 rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-800 dark:bg-slate-900">
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <h3 className="text-sm font-black text-slate-900 dark:text-slate-50">{node.name}</h3>
                      <span className={clsx('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase', style.pill)}>{style.label}</span>
                    </div>
                    <p className="text-xs text-slate-500">Difficulty: {node.difficulty} | Mastery: {node.mastery ?? progressRing(node)}%</p>
                    {node.prerequisiteConcept && <p className="mt-1 text-xs text-slate-500">Prerequisite: {node.prerequisiteConcept}</p>}
                    {node.status === 'locked' && <p className="mt-2 rounded-lg bg-slate-100 p-2 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">{node.lockedReason || 'Complete prerequisite concepts to unlock.'}</p>}
                    {node.reviewDue && <p className="mt-2 rounded-lg bg-amber-50 p-2 text-xs font-semibold text-amber-700 dark:bg-amber-900/20 dark:text-amber-300">Review due now</p>}
                    <p className="mt-2 text-xs text-slate-500">Recommended: {node.recommendedAction || 'Continue learning'}</p>
                    <p className="mt-1 text-xs text-slate-500">Adaptive rank: #{node.adaptiveRank ?? idx + 1}</p>
                    <div className="mt-3 grid grid-cols-2 gap-2">
                      <button onClick={() => navigate(`/lesson/${node.id}`)} disabled={!canStart} title={!canStart ? node.lockedReason || 'This topic is not the current lesson.' : undefined} className="rounded-xl bg-[#21B8F9] px-2 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:bg-slate-400">Start Lesson</button>
                      <button onClick={() => navigate(`/lesson/${node.id}?mode=review`)} disabled={!canReview} title={!canReview ? node.lockedReason || 'Review opens after this topic is started.' : undefined} className="rounded-xl bg-amber-500 px-2 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:bg-slate-400">Review</button>
                      <button onClick={() => navigate(`/quiz/${node.id}`)} disabled={!canAssess} title={!canAssess ? node.lockedReason || 'Quiz opens for the current topic.' : undefined} className="rounded-xl bg-violet-600 px-2 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:bg-slate-400">Take Quiz</button>
                      <button onClick={() => navigate(`/puzzle/${node.id}`)} disabled={!canAssess} title={!canAssess ? node.lockedReason || 'Challenge opens for the current topic.' : undefined} className="rounded-xl bg-rose-500 px-2 py-2 text-xs font-bold text-white disabled:cursor-not-allowed disabled:bg-slate-400">Challenge</button>
                      <button onClick={() => navigate('/notebook')} className="col-span-2 rounded-xl border border-slate-200 px-2 py-2 text-xs font-bold dark:border-slate-700">View Notebook</button>
                    </div>
                  </div>
                )}

                {idx < indexed.length - 1 && (
                  <div
                    className={clsx(
                      'absolute top-[78px] h-12 w-1 rounded-full',
                      node.status === 'locked' ? 'bg-slate-300 dark:bg-slate-700' : 'bg-gradient-to-b from-[#21B8F9] to-[#7B61FF]'
                    )}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
        <div className="flex items-center gap-2 font-bold"><Trophy className="h-4 w-4" /> Next target</div>
        <p className="mt-1">Complete current node to unlock the hard challenge and boss battle.</p>
      </div>
      <style>{`
        @keyframes pathCurrent {
          0%, 100% { filter: brightness(1); }
          50% { filter: brightness(1.08); box-shadow: 0 18px 36px rgba(33, 184, 249, 0.28); }
        }
        @keyframes pathUnlock {
          0%, 100% { filter: saturate(1); }
          50% { filter: saturate(1.25) brightness(1.08); }
        }
        @keyframes pathRing {
          from { stroke-dasharray: 0 282.7; }
        }
        @keyframes unlockPing {
          0% { opacity: 0.95; transform: scale(0.75); }
          80%, 100% { opacity: 0; transform: scale(1.9); }
        }
      `}</style>
    </div>
  );
}

function getFallbackNodes(subject: string): ConceptNode[] {
  const ids = getFallbackPath(subject);
  return ids.map((id, index) => {
    const previousName = index > 0 ? getConceptDisplayName(ids[index - 1]) : 'the previous concept';
    const currentName = getConceptDisplayName(id);
    return {
    id,
    name: currentName,
    subjectId: subject,
    status: index === 0 ? 'current' : 'locked',
    type: 'lesson',
    difficulty: index < 2 ? 'easy' : index < 4 ? 'medium' : 'hard',
    dependsOn: index > 0 ? [ids[index - 1]] : [],
    lockedReason: index > 0 ? `Complete ${previousName} through easy, medium, and hard to unlock ${currentName}.` : undefined,
    mastery: index === 0 ? 40 : 0,
  };
  });
}
