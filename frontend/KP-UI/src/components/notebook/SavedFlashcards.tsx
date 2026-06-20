export default function SavedFlashcards({ cards }: { cards: string[] }) {
  return <section className="rounded-2xl border border-slate-200 p-4 dark:border-slate-800"><h3 className="font-black">Saved flashcards</h3><div className="mt-2 flex flex-wrap gap-2">{cards.map((card) => <span key={card} className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold dark:bg-slate-800">{card}</span>)}</div></section>;
}
