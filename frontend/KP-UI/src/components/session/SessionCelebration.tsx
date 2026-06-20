import { Trophy, Zap } from 'lucide-react';
import type { ReactNode } from 'react';
import { RewardState } from '../../lib/types';

export default function SessionCelebration({ reward, message }: { reward?: RewardState | null; message: string }) {
  return (
    <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 text-center dark:border-emerald-900/50 dark:bg-emerald-900/20">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-lg shadow-emerald-600/20">
        <Trophy className="h-8 w-8" />
      </div>
      <h3 className="text-2xl font-black text-slate-900 dark:text-white">{message}</h3>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <Metric icon={<Zap className="h-4 w-4" />} label="XP" value={`+${reward?.xpAwardedToday || 10}`} />
        <Metric label="Streak" value={`${reward?.currentStreak || 1} day`} />
        <Metric label="Level" value={`${reward?.currentLevel || 1}`} />
      </div>
    </section>
  );
}

function Metric({ icon, label, value }: { icon?: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-emerald-200 bg-white p-4 dark:border-emerald-900/40 dark:bg-slate-950">
      <p className="flex items-center justify-center gap-1 text-xs font-black uppercase text-emerald-700 dark:text-emerald-300">{icon}{label}</p>
      <p className="mt-1 text-xl font-black text-slate-900 dark:text-white">{value}</p>
    </div>
  );
}
