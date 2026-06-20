import { Sparkles, Send } from 'lucide-react';
import { useState } from 'react';
import { askDoubt } from '../../lib/api';
import { getConceptDisplayName } from '../../lib/concepts';
import ReadAloudButton from '../common/ReadAloudButton';

const quick = ['Ask simpler explanation', 'Ask for analogy', 'Ask for code example', 'Ask why answer is wrong', 'Ask another practice question'];

export default function TutorChatPanel({ fullPage = false }: { fullPage?: boolean }) {
  const [q, setQ] = useState('');
  const [messages, setMessages] = useState<string[]>(['I can help with this concept. What do you want to explore?']);

  const [loading, setLoading] = useState(false);
  const send = async (text: string) => {
    if (!text.trim()) return;
    setMessages((m) => [...m, `You: ${text}`]);
    setLoading(true);
    const conceptId = localStorage.getItem('current_concept_id') || 'current';
    const concept = getConceptDisplayName(conceptId, localStorage.getItem('current_concept_name'));
    try {
      const res = await askDoubt({
        learnerId: localStorage.getItem('learner_id') || '',
        doubtText: text,
        currentConceptId: conceptId,
        currentConceptName: concept,
        domain: localStorage.getItem('active_subject') || 'Python',
        difficulty: 'easy',
      });
      setMessages((m) => [...m, `Tutor: ${shortAnswer(res.answer, text, concept)}`]);
    } catch {
      setMessages((m) => [...m, `Tutor: ${fallbackAnswer(text, concept)}`]);
    } finally {
      setLoading(false);
    }
    setQ('');
  };

  return (
    <div className={`flex flex-col rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900 ${fullPage ? 'min-h-[75vh]' : ''}`}>
      <div className="mb-3 flex items-center gap-2 font-bold"><Sparkles className="h-4 w-4 text-sky-500" />Tutor Chat</div>
      <div className="mb-3 flex flex-wrap gap-2">{quick.map((x) => <button key={x} onClick={() => send(x)} className="rounded-full border border-slate-200 px-2.5 py-1 text-xs dark:border-slate-700">{x}</button>)}</div>
      <div className={`mb-3 flex-1 space-y-2 overflow-auto rounded-xl bg-slate-50 p-4 text-sm dark:bg-slate-950 ${fullPage ? 'min-h-[50vh]' : 'max-h-44'}`}>{messages.map((m, i) => <div key={i}><p className="leading-6">{m}</p>{m.startsWith('Tutor:') && <ReadAloudButton text={m.replace(/^Tutor:\s*/, '')} compact />}</div>)}{loading && <p className="font-bold text-sky-600">Tutor: preparing...</p>}</div>
      <div className="flex items-center gap-2"><input value={q} onChange={(e) => setQ(e.target.value)} className="flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950" placeholder="Ask your tutor..." /><button onClick={() => send(q)} className="rounded-xl bg-sky-600 p-2 text-white"><Send className="h-4 w-4" /></button></div>
    </div>
  );
}

function shortAnswer(answer: string, query: string, concept: string) {
  const text = answer && answer.trim() ? answer : fallbackAnswer(query, concept);
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 4).join(' ');
  return sentences.length > 520 ? `${sentences.slice(0, 519).trim()}...` : sentences;
}

function fallbackAnswer(query: string, concept: string) {
  const q = query.toLowerCase();
  if (q.includes('create database')) return 'Use this SQL syntax: CREATE DATABASE database_name; Replace database_name with the name you want. Example: CREATE DATABASE school;';
  if (q.includes('database')) return 'A database stores organized data so it can be searched, updated, and reused. Think of tables as structured sheets: rows are records, columns are fields, and keys identify important rows.';
  if (q.includes('analogy')) return `${concept} is like a labeled tool in a study kit: you use the right tool for the right step, then check the result with a small example.`;
  if (q.includes('code') || q.includes('example')) return `Use one small ${concept} example, then explain what each part does. Keep it short before moving to harder practice.`;
  if (q.includes('wrong')) return 'Compare your answer with the expected rule, then find the first step where the meaning changed. That is usually the mistake to fix first.';
  if (q.includes('practice')) return `Practice prompt: explain ${concept} in one sentence, give one example, then answer one quick check.`;
  return `${concept} is the current idea. Start with the definition, inspect one example, and then try a quick check.`;
}
