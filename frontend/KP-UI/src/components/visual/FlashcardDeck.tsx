import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Flashcard } from '../../lib/types';
import { RotateCcw, ThumbsDown, ThumbsUp, Meh } from 'lucide-react';
import { submitAnswer } from '../../lib/api';
import { getConceptDisplayName } from '../../lib/concepts';

export default function FlashcardDeck({ cards, onComplete }: { cards: Flashcard[]; onComplete?: () => void }) {
  const safeCards = cards.length ? cards : [{
    id: 'fallback-card',
    conceptId: 'current',
    front: 'What is the main idea of this concept?',
    back: 'Review the definition, example, and common mistake before the next check.',
    difficulty: 'easy' as const,
    due: true,
  }];
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [activeType, setActiveType] = useState('all');
  const [answerChangeCount, setAnswerChangeCount] = useState(0);
  const startTime = useRef(Date.now());
  const types = ['all', ...Array.from(new Set(safeCards.map((card) => card.card_type || card.cardType || 'concept_recall_flashcard')))];
  const visibleCards = safeCards.filter((card) => activeType === 'all' || (card.card_type || card.cardType) === activeType);
  const card = visibleCards[Math.min(index, visibleCards.length - 1)] || safeCards[0];
  const progress = ((Math.min(index, visibleCards.length - 1) + 1) / Math.max(visibleCards.length, 1)) * 100;

  useEffect(() => {
    startTime.current = Date.now();
    setAnswerChangeCount(0);
  }, [card.id]);

  const next = async (rating: string, confidence: number, correct: boolean) => {
    await submitAnswer({
      learner_id: localStorage.getItem('learner_id') || '',
      subject: localStorage.getItem('active_subject') || '',
      conceptId: card.conceptId,
      conceptName: localStorage.getItem('current_concept_name') || card.conceptId,
      difficulty: card.difficulty,
      questionId: card.id,
      questionType: 'flashcard_recall',
      answer: rating,
      question: {
        questionId: card.id,
        taskType: 'flashcard_recall',
        questionType: 'flashcard_recall',
        prompt: card.front,
        correctAnswer: card.back,
        sourceConcept: card.conceptId,
        difficulty: card.difficulty,
      },
      confidence,
      time_taken_sec: Math.max(1, Math.round((Date.now() - startTime.current) / 1000)),
      hint_used: flipped,
      hint_count: flipped ? 1 : 0,
      option_change_count: 0,
      answer_change_count: answerChangeCount,
      run_code_count: 0,
      attempt_count: 1,
      wrong_attempt_count: correct ? 0 : 1,
    });
    if (index < visibleCards.length - 1) {
      setIndex((curr) => curr + 1);
      setFlipped(false);
    } else {
      onComplete?.();
    }
  };

  return (
    <section className="mx-auto w-full max-w-2xl rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-5 flex items-center justify-between">
        <p className="text-sm font-black text-slate-700 dark:text-slate-200">Flashcard revision</p>
        <p className="text-sm font-bold text-slate-400">Card {Math.min(index, visibleCards.length - 1) + 1}/{visibleCards.length}</p>
      </div>
      <div className="mb-4 flex flex-wrap gap-2">
        {types.map((type) => (
          <button key={type} onClick={() => { setActiveType(type); setIndex(0); setFlipped(false); }} className={`rounded-full px-3 py-1 text-xs font-bold ${activeType === type ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200'}`}>
            {label(type)}
          </button>
        ))}
      </div>
      <div className="mb-6 h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-full rounded-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} />
      </div>
      <button
        onClick={() => { setFlipped((curr) => !curr); setAnswerChangeCount((count) => count + 1); }}
        className="flex min-h-72 w-full flex-col items-center justify-center rounded-3xl border border-slate-200 bg-slate-50 p-6 text-center transition hover:border-indigo-300 dark:border-slate-800 dark:bg-slate-900"
      >
        <p className="mb-4 text-xs font-black uppercase tracking-wider text-indigo-600 dark:text-indigo-300">{label(card.card_type || card.cardType || 'flashcard')} · {flipped ? 'Answer' : 'Question'}</p>
        {flipped ? <BulletText text={card.back} /> : <p className="max-w-xl text-2xl font-black leading-relaxed text-slate-900 dark:text-white">{shortText(card.front, 120)}</p>}
        {flipped && card.explanation && <p className="mt-4 max-w-xl text-sm font-semibold leading-6 text-slate-500 dark:text-slate-300">{card.explanation}</p>}
        <span className="mt-4 rounded-full border border-slate-200 px-3 py-1 text-xs font-black uppercase text-slate-500 dark:border-slate-700">{card.difficulty}</span>
        <span className="mt-2 rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-black uppercase text-indigo-600 dark:border-indigo-900/40 dark:bg-indigo-900/20 dark:text-indigo-200">
          Topic: {getConceptDisplayName(card.conceptId, localStorage.getItem('current_concept_name'))}
        </span>
        <span className="mt-8 inline-flex items-center gap-2 text-sm font-bold text-slate-400"><RotateCcw className="h-4 w-4" /> {flipped ? 'Tap to see question' : 'Show answer'}</span>
      </button>
      <div className="mt-6 grid grid-cols-4 gap-3">
        <RatingButton label="Again" icon={<RotateCcw className="h-5 w-5" />} onClick={() => next('Again', 0.3, false)} tone="rose" />
        <RatingButton label="Hard" icon={<ThumbsDown className="h-5 w-5" />} onClick={() => next('Hard', 0.5, false)} tone="amber" />
        <RatingButton label="Good" icon={<Meh className="h-5 w-5" />} onClick={() => next('Good', 0.7, true)} tone="sky" />
        <RatingButton label="Easy" icon={<ThumbsUp className="h-5 w-5" />} onClick={() => next('Easy', 0.9, true)} tone="emerald" />
      </div>
      <button className="mt-3 w-full rounded-2xl border border-slate-200 p-3 text-xs font-black text-slate-600 dark:border-slate-800 dark:text-slate-300">Save to notebook</button>
    </section>
  );
}

function label(type: string) {
  const clean = type.replace(/_flashcard|_card/g, '').replaceAll('_', ' ');
  if (clean === 'all') return 'All';
  return clean.replace(/\b\w/g, (m) => m.toUpperCase());
}

function RatingButton({ label, icon, onClick, tone }: { label: string; icon: ReactNode; onClick: () => void; tone: string }) {
  const classes: Record<string, string> = {
    rose: 'border-rose-200 text-rose-700 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-300',
    amber: 'border-amber-200 text-amber-700 hover:bg-amber-50 dark:border-amber-900 dark:text-amber-300',
    sky: 'border-sky-200 text-sky-700 hover:bg-sky-50 dark:border-sky-900 dark:text-sky-300',
    emerald: 'border-emerald-200 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-900 dark:text-emerald-300',
  };
  return <button onClick={onClick} className={`flex flex-col items-center gap-2 rounded-2xl border bg-white p-3 text-xs font-black transition dark:bg-slate-950 ${classes[tone]}`}>{icon}{label}</button>;
}

function BulletText({ text }: { text: string }) {
  const items = text
    .split(/\n/)
    .map((item) => item.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)
    .slice(0, 4);
  return (
    <ul className="max-h-56 max-w-xl space-y-2 overflow-y-auto text-left text-base font-bold leading-7 text-slate-800 dark:text-slate-100">
      {(items.length ? items : [shortText(text, 140)]).map((item, idx) => <li key={idx}>- {shortText(item, 120)}</li>)}
    </ul>
  );
}

function shortText(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1).trim()}...` : text;
}
