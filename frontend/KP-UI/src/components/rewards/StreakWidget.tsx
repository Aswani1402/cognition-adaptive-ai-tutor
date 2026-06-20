import { Flame } from 'lucide-react';

export default function StreakWidget({ streak, days }: { streak: number; days: { day: string; completed: boolean }[] }) {
  return (
    <div className="rounded-3xl border border-orange-200 bg-white p-5 dark:border-orange-900/30 dark:bg-slate-900">
      <div className="mb-3 flex items-center gap-2 font-bold">
        <Flame className="h-5 w-5 fill-orange-500 text-orange-500 animate-[streakFlame_1.6s_ease-in-out_infinite]" />
        {streak}-day streak
      </div>
      <div className="grid grid-cols-7 gap-2">
        {days.map((d, index) => (
          <div
            key={d.day}
            className={`rounded-lg p-2 text-center text-xs transition ${d.completed ? 'bg-orange-100 text-orange-700 shadow-sm shadow-orange-300/30 dark:bg-orange-900/30 dark:text-orange-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800'}`}
            style={{ animation: d.completed ? `streakDay 1.8s ease-in-out ${index * 80}ms infinite` : undefined }}
          >
            {d.day}
          </div>
        ))}
      </div>
      <style>{`
        @keyframes streakFlame {
          0%, 100% { transform: scale(1) rotate(-2deg); filter: drop-shadow(0 0 0 rgba(249, 115, 22, 0)); }
          50% { transform: scale(1.16) rotate(3deg); filter: drop-shadow(0 0 8px rgba(249, 115, 22, 0.45)); }
        }
        @keyframes streakDay {
          0%, 100% { transform: translateY(0); }
          45% { transform: translateY(-2px); }
        }
      `}</style>
    </div>
  );
}
