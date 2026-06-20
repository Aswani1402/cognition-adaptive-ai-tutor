import { Zap } from 'lucide-react';

export default function XPBadge({ value }: { value: number }) {
  return (
    <div className="inline-flex animate-[xpPop_2.6s_ease-in-out_infinite] items-center gap-1 rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-700 shadow-sm shadow-amber-300/30 dark:bg-amber-900/30 dark:text-amber-300">
      <Zap className="h-4 w-4 fill-current animate-[xpSpark_1.8s_ease-in-out_infinite]" />
      {value} XP
      <style>{`
        @keyframes xpPop {
          0%, 100% { transform: translateY(0) scale(1); }
          45% { transform: translateY(-1px) scale(1.035); }
        }
        @keyframes xpSpark {
          0%, 100% { transform: rotate(0deg) scale(1); }
          50% { transform: rotate(8deg) scale(1.16); }
        }
      `}</style>
    </div>
  );
}
