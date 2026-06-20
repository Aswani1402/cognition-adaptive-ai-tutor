import { useEffect, useState, type ReactNode, type FC } from 'react';
import { Trophy, CheckCircle, BarChart3, TrendingUp, Sparkles, Flame } from 'lucide-react';
import { getProgress } from '../lib/api';
import { ProgressData } from '../lib/types';
import { useLearnerSession } from '../context/LearnerSessionContext';

export default function ProgressPage() {
  const [data, setData] = useState<ProgressData | null>(null);
  const session = useLearnerSession();

  useEffect(() => {
    getProgress(session.getCurrentLearnerId(), session.active_subject).then(setData);
  }, [session.active_subject]);

  if (!data) return <div className="flex h-[50vh] items-center justify-center text-slate-500">Loading your progress...</div>;

  const subjectProgress = data.subjectProgress ?? [];
  const conceptMastery = data.conceptMastery ?? [];
  const weakAreas = data.weakAreas ?? [];
  const xpHistory = data.xpHistory ?? [];
  const streakCalendar = data.streakCalendar ?? [];
  const hasProgress = Boolean(data.hasProgressData || data.totalXP > 0 || data.conceptsMastered > 0 || conceptMastery.length || weakAreas.length || (data.recentAttempts?.length || 0) > 0);

  if (!hasProgress) {
    return (
      <div className="mx-auto w-full max-w-3xl pb-20">
        <h1 className="text-3xl font-extrabold">Your Progress Profile</h1>
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <p className="text-sm font-bold uppercase text-slate-500">{data.sourceLabel || 'No progress yet'}</p>
          <h2 className="mt-2 text-2xl font-black text-slate-900 dark:text-white">No progress yet.</h2>
          <p className="mt-3 text-slate-600 dark:text-slate-300">No progress yet. Complete one lesson or assessment to build your progress profile.</p>
          {session.active_subject && <p className="mt-4 text-sm font-semibold text-sky-700 dark:text-sky-300">Active subject: {session.active_subject}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto w-full pb-20 space-y-6">
      <h1 className="text-3xl font-extrabold">Your Progress Profile</h1>
      <p className="text-sm font-bold uppercase text-slate-500">{data.sourceLabel || 'Live backend'}</p>
      {(session.active_subject || session.current_concept_name || session.current_concept_id) && (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold dark:border-slate-800 dark:bg-slate-950">
          {session.active_subject && <p>Active subject: {session.active_subject}</p>}
          {(session.current_concept_name || session.current_concept_id) && <p>Current concept: {session.current_concept_name || session.current_concept_id}</p>}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat icon={<Trophy className="w-6 h-6 text-amber-500" />} label="Current level" value={`Level ${data.currentLevel}`} />
        <Stat icon={<TrendingUp className="w-6 h-6 text-sky-500" />} label="Total XP" value={`${data.totalXP}`} />
        <Stat icon={<CheckCircle className="w-6 h-6 text-emerald-500" />} label="Concepts mastered" value={`${data.conceptsMastered}`} />
        <Stat icon={<BarChart3 className="w-6 h-6 text-rose-500" />} label="Accuracy" value={`${data.accuracy}%`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-bold mb-4 flex items-center gap-2"><Sparkles className="w-4 h-4 text-sky-500" /> XP history</h2>
          <div className="space-y-3">{xpHistory.length ? xpHistory.map((d) => <BarRow key={d.day} label={d.day} value={d.xp} max={400} color="bg-sky-500" />) : <p className="text-sm text-slate-500">No XP history rows yet.</p>}</div>
        </div>
        <div className="card">
          <h2 className="font-bold mb-4">Subject progress</h2>
          <div className="space-y-4">
            {subjectProgress.map((s) => (
              <div key={s.subjectName}>
                <div className="flex justify-between text-sm font-semibold"><span>{s.subjectName}</span><span>{s.progressPercentage}%</span></div>
                <div className="h-3 rounded-full bg-slate-100 dark:bg-slate-800 mt-2"><div className="h-3 rounded-full" style={{ width: `${s.progressPercentage}%`, background: s.color }}></div></div>
                <p className="text-xs text-slate-500 mt-1">{s.masteredConcepts}/{s.totalConcepts} concepts mastered</p>
              </div>
            ))}
            {!subjectProgress.length && <p className="text-sm text-slate-500">No subject progress rows yet.</p>}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="font-bold mb-4">Concept mastery</h2>
        <div className="overflow-x-auto">
          <table className="min-w-[720px] w-full text-sm">
            <thead><tr className="text-left text-slate-500"><th>Concept</th><th>Subject</th><th>Mastery</th><th>Status</th><th>Last practiced</th></tr></thead>
            <tbody>{conceptMastery.map((c) => <tr key={c.conceptName} className="border-t border-slate-200 dark:border-slate-800"><td className="py-2">{c.conceptName}</td><td>{c.subject}</td><td>{c.mastery}%</td><td>{c.status}</td><td>{c.lastPracticed}</td></tr>)}</tbody>
          </table>
          {!conceptMastery.length && <p className="py-4 text-sm text-slate-500">No concept mastery rows yet.</p>}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-bold mb-4">Weak areas</h2>
          <div className="space-y-3">{weakAreas.length ? weakAreas.map((w, i) => <div key={`${w.concept}-${i}`} className="p-3 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-900/40"><p className="font-semibold">{w.concept} - {w.skill}</p><p className="text-sm text-slate-600 dark:text-slate-300">{w.recommendedAction}</p></div>) : <p className="text-sm text-slate-500">No weak areas recorded yet.</p>}</div>
        </div>
        <div className="card">
          <h2 className="font-bold mb-4 flex items-center gap-2"><Flame className="w-4 h-4 text-orange-500" /> Streak calendar</h2>
          <div className="grid grid-cols-7 gap-2">{streakCalendar.length ? streakCalendar.map((d) => <div key={d.day} className={`p-2 rounded-lg text-center text-xs font-bold ${d.completed ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}><div>{d.day}</div><div>{d.xp}</div></div>) : <p className="col-span-7 text-sm text-slate-500">No streak rows yet.</p>}</div>
          <p className="mt-4 text-sm text-slate-600 dark:text-slate-300">Review due: {data.reviewDue} | Avg confidence: {data.averageConfidence} | Mastery: {data.masteryPercent}% | XP today: {data.xpToday}</p>
        </div>
      </div>
    </div>
  );
}

const Stat: FC<{ icon: ReactNode; label: string; value: string }> = ({ icon, label, value }) => {
  return <div className="card"><div className="mb-2">{icon}</div><div className="text-2xl font-black">{value}</div><div className="text-xs text-slate-500 uppercase">{label}</div></div>;
};

const BarRow: FC<{ label: string; value: number; max: number; color: string }> = ({ label, value, max, color }) => {
  const pct = Math.min(100, Math.round((value / max) * 100));
  return <div><div className="flex justify-between text-sm"><span>{label}</span><span>{value}</span></div><div className="h-2 rounded-full bg-slate-100 dark:bg-slate-800 mt-1"><div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }}></div></div></div>;
};
