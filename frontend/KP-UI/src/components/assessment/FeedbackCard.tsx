export default function FeedbackCard({ score, feedback }: { score: number; feedback: string }) {
  return (
    <div className="rounded-xl border border-sky-200 bg-sky-50 p-3 dark:border-sky-900/30 dark:bg-sky-900/20">
      <p className="text-sm font-bold text-sky-800 dark:text-sky-300">Score: {score}</p>
      <p className="text-sm text-slate-700 dark:text-slate-200">{feedback}</p>
    </div>
  );
}
