export default function WeaknessSummaryCard({ weakPoints }: { weakPoints: string[] }) {
  return (
    <section className="rounded-3xl border border-rose-100 bg-rose-50 p-5 dark:border-rose-900/40 dark:bg-rose-900/20">
      <h3 className="font-black text-rose-800 dark:text-rose-200">Weakness summary</h3>
      <div className="mt-3 grid gap-2 sm:grid-cols-2">{weakPoints.map((point) => <div key={point} className="rounded-xl bg-white p-3 text-sm font-bold text-rose-700 dark:bg-slate-900 dark:text-rose-300">{point}</div>)}</div>
    </section>
  );
}
