export default function LevelProgressBar({ currentLevel, totalXp, nextLevelXp }: { currentLevel: number; totalXp: number; nextLevelXp: number }) {
  const pct = Math.min(100, Math.round((totalXp / nextLevelXp) * 100));
  return (
    <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 dark:border-violet-900/30 dark:bg-violet-900/20">
      <div className="mb-2 flex items-center justify-between"><span className="font-bold">Level {currentLevel}</span><span className="text-sm">{totalXp}/{nextLevelXp} XP</span></div>
      <div className="h-2 overflow-hidden rounded-full bg-white/70 dark:bg-slate-800">
        <div className="h-2 rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-400 transition-all duration-1000 ease-out animate-[levelGlow_2.2s_ease-in-out_infinite]" style={{ width: `${pct}%` }} />
      </div>
      <style>{`
        @keyframes levelGlow {
          0%, 100% { box-shadow: 0 0 0 rgba(139, 92, 246, 0); }
          50% { box-shadow: 0 0 14px rgba(139, 92, 246, 0.55); }
        }
      `}</style>
    </div>
  );
}
