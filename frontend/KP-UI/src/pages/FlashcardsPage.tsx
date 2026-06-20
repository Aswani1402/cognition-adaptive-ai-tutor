import { useEffect, useState } from 'react';
import { Brain } from 'lucide-react';
import { getFlashcards } from '../lib/api';
import { Flashcard } from '../lib/types';
import FlashcardDeck from '../components/visual/FlashcardDeck';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';

export default function FlashcardsPage() {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [variant, setVariant] = useState('All');
  const [completed, setCompleted] = useState(false);
  const session = useLearnerSession();

  useEffect(() => {
    const learnerId = session.getCurrentLearnerId();
    const conceptId = session.current_concept_id;
    if (conceptId) getFlashcards(learnerId, conceptId, session.active_subject).then(setCards);
    else getFlashcards(learnerId, undefined, session.active_subject).then(setCards);
  }, [session.active_subject, session.current_concept_id]);

  if (completed) {
    return (
      <div className="mx-auto w-full max-w-2xl pb-20 pt-12 text-center">
        <div className="mx-auto mb-6 flex h-24 w-24 items-center justify-center rounded-full bg-emerald-100 text-emerald-500 dark:bg-emerald-900/30">
          <Brain className="h-12 w-12" />
        </div>
        <h1 className="mb-4 text-3xl font-extrabold text-slate-900 dark:text-white">Review Complete</h1>
        <p className="mb-8 text-slate-500">Your guided revision cards are done for now.</p>
        <button onClick={() => setCompleted(false)} className="rounded-2xl bg-indigo-600 px-8 py-3 font-bold text-white shadow-lg shadow-indigo-200 transition hover:scale-105 dark:shadow-indigo-900/20">
          Review Again
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-3xl pb-20 pt-8">
      <header className="mb-6">
        <p className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300">Revision library</p>
        <h1 className="text-3xl font-black text-slate-900 dark:text-white">{getConceptDisplayName(session.current_concept_id, session.current_concept_name || session.active_subject || 'Daily')} Flashcards</h1>
      </header>
      <div className="mb-6"><CogniGuideCard {...getCogniMessage({ page: 'flashcards', activityType: 'flashcard_revision' })} compact /></div>
      <div className="mb-5 flex gap-2 overflow-x-auto">
        {['All', 'Concept Recall', 'Misconception', 'Example', 'Debug', 'Syntax', 'Personal', 'Spaced Repetition'].map((item) => (
          <button key={item} onClick={() => setVariant(item)} className={`shrink-0 rounded-full px-4 py-2 text-sm font-bold ${variant === item ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>{item}</button>
        ))}
      </div>
      <FlashcardDeck cards={cards.filter((card) => variant === 'All' || String(card.card_type || card.cardType || '').toLowerCase().includes(variant.toLowerCase().split(' ')[0]))} onComplete={() => setCompleted(true)} />
    </div>
  );
}
