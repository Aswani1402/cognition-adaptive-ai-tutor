import { NotebookMemory } from '../../lib/types';
import MistakeSummary from './MistakeSummary';
import RevisionPlan from './RevisionPlan';
import SavedFlashcards from './SavedFlashcards';
import WeaknessSummaryCard from './WeaknessSummaryCard';

export default function NotebookPanel({ notebook }: { notebook: NotebookMemory }) {
  return (
    <div className="space-y-4">
      <p className="text-lg leading-relaxed text-slate-700 dark:text-slate-300">{notebook.summary}</p>
      <WeaknessSummaryCard weakPoints={notebook.weakPoints} />
      <RevisionPlan items={notebook.revisionPlan} />
      <SavedFlashcards cards={notebook.savedFlashcards} />
      <MistakeSummary mistakes={notebook.mistakes} />
    </div>
  );
}
