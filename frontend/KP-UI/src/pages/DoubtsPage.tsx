import { useState } from 'react';
import { HelpCircle, Send } from 'lucide-react';
import { askDoubt } from '../lib/api';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';
import ReadAloudButton from '../components/common/ReadAloudButton';

export default function DoubtsPage() {
  const session = useLearnerSession();
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<{ q: string; a: string }[]>([]);
  const concept = getConceptDisplayName(session.current_concept_id, session.current_concept_name);

  const ask = async (text: string) => {
    if (!text.trim()) return;
    setLoading(true);
    try {
      const res = await askDoubt({
        learnerId: session.getCurrentLearnerId(),
        doubtText: text,
        currentConceptId: session.current_concept_id || 'current',
        currentConceptName: concept,
        domain: session.active_subject || 'Python',
        difficulty: 'easy',
      });
      setHistory((items) => [{ q: text, a: concise(res.answer || fallbackAnswer(text, concept)) }, ...items]);
    } catch {
      setHistory((items) => [{ q: text, a: fallbackAnswer(text, concept) }, ...items]);
    } finally {
      setInput('');
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 pb-20">
      <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="flex items-center gap-3">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-indigo-600 text-white"><HelpCircle className="h-6 w-6" /></div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Ask Tutor</p>
            <h1 className="text-2xl font-black">Doubts for {concept}</h1>
            <p className="text-sm text-slate-500">{session.active_subject || 'Selected subject'} · concise grounded help</p>
          </div>
        </div>
      </header>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-4 flex flex-wrap gap-2">
          {['What is this concept?', 'Give a simpler explanation', 'Give one example', 'Why was my answer wrong?'].map((prompt) => (
            <button key={prompt} onClick={() => ask(prompt)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold dark:border-slate-700">{prompt}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} className="flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-900" placeholder="Type your doubt..." />
          <button onClick={() => ask(input)} disabled={loading} className="rounded-2xl bg-indigo-600 px-4 text-white disabled:opacity-60"><Send className="h-5 w-5" /></button>
        </div>
      </section>

      <div className="space-y-3">
        {history.length === 0 && <p className="rounded-3xl border border-dashed border-slate-200 p-8 text-center text-sm font-semibold text-slate-500 dark:border-slate-800">No doubts asked yet.</p>}
        {history.map((item, index) => (
          <article key={index} className="rounded-3xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950">
            <p className="font-black">Q: {item.q}</p>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-700 dark:text-slate-200">A: {item.a}</p>
            <div className="mt-3"><ReadAloudButton text={item.a} compact /></div>
          </article>
        ))}
      </div>
    </div>
  );
}

function fallbackAnswer(query: string, concept: string) {
  const q = query.toLowerCase();
  if (q.includes('create database')) return 'Use this SQL syntax: CREATE DATABASE database_name; Replace database_name with your chosen name. Example: CREATE DATABASE school;';
  if (q.includes('database')) return 'A database stores organized data. Tables organize related data, rows are records, and columns describe fields.';
  if (q.includes('analogy')) return `${concept} is like a labeled section in a notebook: each section keeps related information easy to find.`;
  if (q.includes('example')) return `One small example for ${concept}: state the rule, show one tiny case, then explain the result.`;
  return `For ${concept}, focus on the definition, one example, and the common mistake to avoid.`;
}

function concise(text: string) {
  const sentences = String(text || '').split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 4).join(' ');
  return sentences.length > 520 ? `${sentences.slice(0, 519).trim()}...` : sentences;
}
