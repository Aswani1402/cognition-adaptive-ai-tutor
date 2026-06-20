import { Gift } from 'lucide-react';

export default function CelebrationModal({ open, message, xpAwarded, onClose }: { open: boolean; message: string; xpAwarded: number; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 animate-[modalFade_220ms_ease-out_both]">
      <div className="w-full max-w-md rounded-3xl border border-amber-200 bg-white p-6 text-center shadow-2xl animate-[modalPop_360ms_cubic-bezier(.2,1.4,.4,1)_both] dark:border-amber-900/40 dark:bg-slate-900">
        <div className="mx-auto mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-amber-400 text-white animate-[giftBounce_1.4s_ease-in-out_infinite]"><Gift className="h-7 w-7" /></div>
        <h3 className="text-xl font-black">Celebration</h3>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{message}</p>
        <p className="mt-2 text-sm font-bold text-amber-600">+{xpAwarded} XP</p>
        <button onClick={onClose} className="mt-4 rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white">Continue</button>
      </div>
      <style>{`
        @keyframes modalFade { from { opacity: 0; } to { opacity: 1; } }
        @keyframes modalPop {
          from { opacity: 0; transform: translateY(14px) scale(0.92); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes giftBounce {
          0%, 100% { transform: translateY(0) rotate(-2deg); }
          50% { transform: translateY(-4px) rotate(3deg); }
        }
      `}</style>
    </div>
  );
}
