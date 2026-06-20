export default function RewardPopup({ show, message }: { show: boolean; message: string }) {
  if (!show) return null;
  return (
    <div className="fixed left-1/2 top-6 z-40 -translate-x-1/2 rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/30 animate-[rewardDrop_1.8s_ease-out_both]">
      {message}
      <style>{`
        @keyframes rewardDrop {
          0% { opacity: 0; transform: translate(-50%, -18px) scale(0.92); }
          16% { opacity: 1; transform: translate(-50%, 0) scale(1.04); }
          82% { opacity: 1; transform: translate(-50%, 0) scale(1); }
          100% { opacity: 0; transform: translate(-50%, -10px) scale(0.96); }
        }
      `}</style>
    </div>
  );
}
