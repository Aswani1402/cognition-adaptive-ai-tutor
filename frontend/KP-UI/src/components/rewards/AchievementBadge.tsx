import type { FC } from 'react';

interface Props { title: string; achieved: boolean }

const AchievementBadge: FC<Props> = ({ title, achieved }) => {
  return (
    <div className={`rounded-2xl border p-3 text-sm font-semibold transition hover:-translate-y-0.5 ${achieved ? 'border-emerald-200 bg-emerald-50 text-emerald-700 shadow-sm shadow-emerald-300/30 animate-[badgeEarned_2.8s_ease-in-out_infinite] dark:border-emerald-900/40 dark:bg-emerald-900/20 dark:text-emerald-300' : 'border-slate-200 bg-slate-50 text-slate-500 dark:border-slate-700 dark:bg-slate-900'}`}>
      {title}
      {achieved && (
        <style>{`
          @keyframes badgeEarned {
            0%, 100% { box-shadow: 0 0 0 rgba(16, 185, 129, 0); }
            50% { box-shadow: 0 0 18px rgba(16, 185, 129, 0.22); }
          }
        `}</style>
      )}
    </div>
  );
};

export default AchievementBadge;
