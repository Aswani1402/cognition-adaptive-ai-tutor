type FeedbackPanelProps = {
  title?: string;
  feedback: string;
  onTrySimilar?: () => void;
  onContinue?: () => void;
  onReview?: () => void;
};

export default function FeedbackPanel({
  title = 'Feedback',
  feedback,
  onTrySimilar,
  onContinue,
  onReview,
}: FeedbackPanelProps) {
  return (
    <section className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sky-900 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-100">
      <h3 className="text-sm font-black">{title}</h3>
      <p className="mt-1 text-sm">{feedback}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onTrySimilar} className="rounded-full bg-white px-3 py-1.5 text-xs font-bold text-sky-800 shadow-sm disabled:opacity-50" disabled={!onTrySimilar}>
          Try Similar Question
        </button>
        <button type="button" onClick={onContinue} className="rounded-full bg-sky-600 px-3 py-1.5 text-xs font-bold text-white shadow-sm disabled:opacity-50" disabled={!onContinue}>
          Continue
        </button>
        <button type="button" onClick={onReview} className="rounded-full border border-sky-200 px-3 py-1.5 text-xs font-bold text-sky-800 disabled:opacity-50 dark:border-sky-800 dark:text-sky-100" disabled={!onReview}>
          Review
        </button>
      </div>
    </section>
  );
}
