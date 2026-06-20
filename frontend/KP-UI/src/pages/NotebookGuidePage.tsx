import { useEffect, useState } from 'react';
import { askNotebookGuide, getNotebook } from '../lib/api';
import { NotebookMemory } from '../lib/types';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { Send, Sparkles } from 'lucide-react';
import { getConceptDisplayName } from '../lib/concepts';
import ReadAloudButton from '../components/common/ReadAloudButton';

export default function NotebookGuidePage() {
  const session = useLearnerSession();
  const [notebook, setNotebook] = useState<NotebookMemory | null>(null);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState(['I can use your notebook memory, mistakes, flashcards, and revision plan.']);

  useEffect(() => {
    getNotebook(session.getCurrentLearnerId()).then(setNotebook);
  }, [session.learner_id]);

  const send = async (text: string) => {
    if (!text.trim()) return;
    setMessages((items) => [...items, `You: ${text}`]);
    setLoading(true);
    const concept = getConceptDisplayName(session.current_concept_id || notebook?.conceptId, session.current_concept_name);
    try {
      const res = await askNotebookGuide({
        learnerId: session.getCurrentLearnerId(),
        question: text,
        conceptId: session.current_concept_id || notebook?.conceptId || 'current',
        conceptName: concept,
        subject: session.active_subject || 'Python',
      });
      setMessages((items) => [...items, `Guide: ${guideAnswer(text, res.answer, concept, notebook)}`]);
    } catch {
      setMessages((items) => [...items, `Guide: ${guideAnswer(text, '', concept, notebook)}`]);
    } finally {
      setInput('');
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-[80vh] w-full max-w-5xl flex-col rounded-3xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <header className="border-b border-slate-200 p-5 dark:border-slate-800">
        <p className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300">Notebook Guide</p>
        <h1 className="text-3xl font-black">{getConceptDisplayName(session.current_concept_id || notebook?.conceptId, session.current_concept_name)} Study Chat</h1>
      </header>
      <div className="flex-1 space-y-3 overflow-y-auto p-5">
        {messages.map((message, index) => <div key={index} className="rounded-2xl bg-slate-50 p-4 text-sm font-semibold leading-6 dark:bg-slate-900"><p>{message}</p>{message.startsWith('Guide:') && <div className="mt-2"><ReadAloudButton text={message.replace(/^Guide:\s*/, '')} compact /></div>}</div>)}
        {loading && <p className="rounded-2xl bg-indigo-50 p-4 text-sm font-bold text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-100">Preparing answer...</p>}
      </div>
      <div className="border-t border-slate-200 p-4 dark:border-slate-800">
        <div className="mb-3 flex flex-wrap gap-2">
          {['Generate study guide', 'Summarize notes', 'Ask simpler explanation', 'Ask for analogy', 'Ask for code example', 'Ask why answer is wrong', 'Ask another practice question'].map((prompt) => (
            <button key={prompt} onClick={() => send(prompt)} className="rounded-full border border-slate-200 px-3 py-1.5 text-xs font-bold dark:border-slate-700"><Sparkles className="mr-1 inline h-3 w-3" />{prompt}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={input} onChange={(event) => setInput(event.target.value)} className="flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900" placeholder="Ask about your notebook..." />
          <button onClick={() => send(input)} className="rounded-2xl bg-indigo-600 px-4 text-white"><Send className="h-5 w-5" /></button>
        </div>
      </div>
    </div>
  );
}

function guideAnswer(query: string, answer: string, concept: string, notebook: NotebookMemory | null) {
  const q = query.toLowerCase();
  if (q.includes('review')) return `Review ${concept}: ${oneLine(notebook?.summary || 'start with the definition, one example, and one quick check')}. Then practice one due card.`;
  if (q.includes('mistake')) return notebook?.mistakes?.length ? `Your current mistakes to review: ${notebook.mistakes.slice(0, 3).join('; ')}` : 'No unresolved mistakes are saved for this clean learner session.';
  if (q.includes('quiz')) return `Mini quiz: 1. Define ${concept}. 2. Give one example. 3. Name one mistake to avoid.`;
  const text = answer || `Summary for ${concept}: ${notebook?.summary || 'learning content will appear after you start studying.'}`;
  return oneLine(text, 520);
}

function oneLine(text: string, max = 360) {
  const clean = String(text || '').split(/(?<=[.!?])\s+/).slice(0, 4).join(' ').replace(/\s+/g, ' ').trim();
  return clean.length > max ? `${clean.slice(0, max - 1).trim()}...` : clean;
}
