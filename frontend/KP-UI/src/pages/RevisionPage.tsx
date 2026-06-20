import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpenCheck, CheckCircle2 } from 'lucide-react';
import { getMistakeReview, getNotebook, getRevision } from '../lib/api';
import { MistakeReview, NotebookMemory } from '../lib/types';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';
import { logFrontendEvent } from '../lib/eventLog';

export default function RevisionPage() {
  const session = useLearnerSession();
  const [notebook, setNotebook] = useState<NotebookMemory | null>(null);
  const [mistakes, setMistakes] = useState<MistakeReview[]>([]);
  const [revision, setRevision] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    logFrontendEvent({ action: 'revision_opened', module: 'revision', status: 'started', summary: 'Revision opened' });
    const learnerId = session.getCurrentLearnerId();
    getNotebook(learnerId).then(setNotebook).catch(() => setNotebook(null));
    getMistakeReview(learnerId).then(setMistakes).catch(() => setMistakes([]));
    getRevision(learnerId).then(setRevision).catch(() => setRevision(null));
  }, [session.learner_id]);

  const concept = getConceptDisplayName(session.current_concept_id || notebook?.conceptId, session.current_concept_name);
  const unresolved = mistakes.filter((m) => !/correct/i.test(m.feedback || '') && String(m.misconceptionDetected || '').toLowerCase() !== 'none').slice(0, 3);
  const dueCards = asArray(revision?.due_revision_cards || revision?.due_cards);
  const revisionPacket = asRecord(revision?.revision_packet);
  const recommended = asRecord(revision?.recommended_revision_activity || revision?.next_recommended_activity);
  const weakConcept = String(
    dueCards[0]?.concept_name
    || dueCards[0]?.concept
    || unresolved[0]?.conceptName
    || revision?.concept_name
    || concept
    || ''
  );
  const revisionNeeded = Boolean(revision?.revision_needed || dueCards.length || unresolved.length);
  const whyRevision = String(
    dueCards[0]?.revision_reason
    || dueCards[0]?.reason
    || unresolved[0]?.feedback
    || recommended.reason
    || revisionPacket.revision_reason
    || 'No revision due yet.'
  );
  const suggestedAction = String(
    recommended.label
    || revisionPacket.next_revision_action
    || (revisionNeeded ? 'Review this concept' : 'No revision due yet.')
  );

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-20">
      <header className="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 dark:border-emerald-900/40 dark:bg-emerald-900/20">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-600 text-white"><BookOpenCheck className="h-6 w-6" /></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-200">Today revision</p>
            <h1 className="text-2xl font-black">{concept}</h1>
            <p className="text-sm text-emerald-800 dark:text-emerald-100">{revisionNeeded ? 'Action-oriented review, not full notebook notes.' : 'No revision due yet.'}</p>
          </div>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card title="Current weak concept" body={revisionNeeded ? weakConcept || 'Current concept' : 'No revision due yet.'} />
        <Card title="Why revision is needed" body={revisionNeeded ? whyRevision : 'No revision due yet.'} />
        <Card title="Suggested revision action" body={suggestedAction} />
        <Card title="Due cards" body={dueCards.length ? `${dueCards.length} backend cards due` : `${notebook?.savedFlashcards?.length || 0} flashcards ready`} />
      </div>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-xl font-black">Practice queue</h2>
          <div className="flex flex-wrap gap-2">
            <Link to="/flashcards" className="rounded-full border border-slate-200 px-4 py-2 text-sm font-bold dark:border-slate-700">Flashcards</Link>
            <Link to="/assessment" className="rounded-full bg-sky-600 px-4 py-2 text-sm font-bold text-white">Practice</Link>
          </div>
        </div>
        <div className="space-y-3">
          {!revisionNeeded && <p className="flex items-center gap-2 rounded-2xl bg-emerald-50 p-4 text-sm font-bold text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-200"><CheckCircle2 className="h-4 w-4" />No revision due yet.</p>}
          {dueCards.map((card, index) => <Card key={`${card.concept_id || card.concept_name || 'due'}-${index}`} title={String(card.concept_name || card.concept || 'Due revision')} body={String(card.revision_reason || card.reason || card.prompt || 'Review this concept before continuing.')} />)}
          {unresolved.map((m) => <Card key={m.mistakeId} title={`${getConceptDisplayName(m.conceptId, m.conceptName)} · ${m.questionType}`} body={m.feedback || 'Review this item'} />)}
        </div>
      </section>
    </div>
  );
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function asArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object' && !Array.isArray(item)) : [];
}

function Card({ title, body }: { title: string; body: string; key?: unknown }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
      <h3 className="font-black">{title}</h3>
      <p className="mt-2 line-clamp-2 text-sm font-semibold text-slate-500">{body}</p>
    </article>
  );
}
