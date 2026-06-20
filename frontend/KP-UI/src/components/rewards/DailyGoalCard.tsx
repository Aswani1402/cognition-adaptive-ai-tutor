export default function DailyGoalCard({ current, goal }: { current: number; goal: number }) {
  const pct = Math.min(100, Math.round((current / goal) * 100));
  return (
    <div className="rounded-3xl border border-emerald-200 bg-white p-5 dark:border-emerald-900/30 dark:bg-slate-900">
      <h4 className="font-bold">Daily Goal</h4>
      <p className="mt-1 text-sm text-slate-500">{current}/{goal} XP</p>
      <div className="mt-3 h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-3 rounded-full bg-gradient-to-r from-emerald-500 to-lime-400 transition-all duration-1000 ease-out animate-[goalFill_2.4s_ease-in-out_infinite]" style={{ width: `${pct}%` }} />
      </div>
      <style>{`
        @keyframes goalFill {
          0%, 100% { filter: saturate(1); }
          50% { filter: saturate(1.35) brightness(1.08); }
        }
      `}</style>
    </div>
  );
}
