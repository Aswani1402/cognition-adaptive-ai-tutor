import { MistakeReview } from '../../lib/types';

export default function MistakeAnalysisPanel({ mistake }: { mistake: MistakeReview }) {
  return (
    <section className="rounded-2xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/40 dark:bg-rose-900/20">
      <h3 className="font-black text-rose-800 dark:text-rose-200">Mistake analysis</h3>
      <p className="mt-2 text-sm"><strong>Misconception:</strong> {mistake.misconceptionDetected}</p>
      <p className="mt-1 text-sm"><strong>Try again type:</strong> {mistake.tryAgainType}</p>
    </section>
  );
}
