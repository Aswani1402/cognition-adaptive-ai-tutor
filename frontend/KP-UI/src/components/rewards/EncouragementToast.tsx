import { Sparkles } from 'lucide-react';

export default function EncouragementToast({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="fixed bottom-20 right-4 z-40 rounded-2xl bg-slate-900 px-4 py-3 text-sm text-white shadow-xl animate-[toastIn_2.6s_ease-out_both] dark:bg-slate-100 dark:text-slate-900">
      <div className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-amber-400" />{message}</div>
      <style>{`
        @keyframes toastIn {
          0% { opacity: 0; transform: translateY(12px) scale(0.96); }
          12%, 86% { opacity: 1; transform: translateY(0) scale(1); }
          100% { opacity: 0; transform: translateY(8px) scale(0.98); }
        }
      `}</style>
    </div>
  );
}
