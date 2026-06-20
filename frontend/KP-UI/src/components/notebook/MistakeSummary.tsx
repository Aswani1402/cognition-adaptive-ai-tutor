export default function MistakeSummary({ mistakes }: { mistakes: string[] }) {
  return <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><h3 className="font-black">Mistake summary</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{mistakes.map((mistake) => <li key={mistake}>{mistake}</li>)}</ul></section>;
}
