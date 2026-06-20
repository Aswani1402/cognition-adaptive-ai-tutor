export default function RevisionPlan({ items }: { items: string[] }) {
  return <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><h3 className="font-black">Revision plan</h3><ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">{items.map((item) => <li key={item}>{item}</li>)}</ol></section>;
}
