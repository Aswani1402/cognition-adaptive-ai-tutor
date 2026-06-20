import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { askNotebookGuide, getAudioOverview, getNotebook, getSimilarQuestion, saveNotebookNote } from '../lib/api';
import { NotebookMemory } from '../lib/types';
import { FileText, Sparkles, AlertTriangle, MessageSquare, Play, Search, Folder, PenLine, Headphones, Send } from 'lucide-react';
import clsx from 'clsx';
import TutorChatPanel from '../components/chat/TutorChatPanel';
import EmptyState from '../components/common/EmptyState';
import NotebookSearchPanel from '../components/notebook/NotebookSearchPanel';
import NotebookPanel from '../components/notebook/NotebookPanel';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';
import { logFrontendEvent } from '../lib/eventLog';

export default function NotebookPage() {
  const navigate = useNavigate();
  const [notebook, setNotebook] = useState<NotebookMemory | null>(null);
  const [loading, setLoading] = useState(true);
  const [guidePanel, setGuidePanel] = useState<{ title: string; body: string }>({ title: '', body: '' });
  const [chatInput, setChatInput] = useState('');
  const [saveStatus, setSaveStatus] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const session = useLearnerSession();

  useEffect(() => {
    logFrontendEvent({ action: 'notebook_opened', module: 'notebook', status: 'started', summary: 'Notebook opened' });
    getNotebook(session.getCurrentLearnerId()).then(res => {
      const cleanStart = localStorage.getItem('cognitutor_clean_start') === 'true';
      const local = JSON.parse(localStorage.getItem('cognitutor_local_progress') || '{}') as { completedQuestions?: number };
      setNotebook(cleanStart && !local.completedQuestions ? {
        learnerId: session.getCurrentLearnerId(),
        conceptId: session.current_concept_id || 'current',
        summary: 'Your notebook will fill with summaries, mistakes, doubts, and revision cards after you start learning.',
        weakPoints: [],
        mistakes: [],
        revisionPlan: ['Complete one quick check', 'Review the feedback', 'Save useful notes'],
        savedFlashcards: [],
        lastUpdated: new Date().toISOString(),
        pastDoubts: [],
      } : res);
      setLoading(false);
    });
  }, [session.learner_id]);

  const askGuide = async (prompt: string) => {
    if (!notebook) return;
    const conceptName = session.current_concept_name || notebook.conceptId || 'current concept';
    const res = await askNotebookGuide({
      learnerId: session.getCurrentLearnerId(),
      question: prompt,
      conceptId: session.current_concept_id || notebook.conceptId || 'current',
      conceptName,
      subject: session.active_subject || 'Python',
    });
    setGuidePanel({ title: prompt, body: String(res.answer || 'Use the current packet, then try one aligned practice question.') });
  };

  const saveGuidePanel = async () => {
    if (!guidePanel.body) return;
    setSaveStatus('Saving...');
    const res = await saveNotebookNote({
      title: guidePanel.title || 'Notebook guide note',
      content: guidePanel.body,
      note_type: 'notebook_guide',
      source_page: 'notebook',
      learnerId: session.getCurrentLearnerId(),
      subject: session.active_subject,
      conceptId: session.current_concept_id || notebook?.conceptId,
      conceptName: session.current_concept_name || conceptTitle,
    });
    setSaveStatus(res.saved ? (res.already_saved ? 'Saved' : 'Saved') : (res.error || 'Save failed'));
  };

  const practiceWeakness = async () => {
    const question = await getSimilarQuestion({
      learner_id: session.getCurrentLearnerId(),
      concept_id: session.current_concept_id || notebook?.conceptId,
      concept_name: session.current_concept_name || notebook?.conceptId,
      subject: session.active_subject,
      weakness: notebook?.weakPoints?.[0],
      question_type: 'practice_question',
    });
    if (question && (session.current_concept_id || notebook?.conceptId)) {
      setGuidePanel({ title: 'Practice Weakness', body: `${question.questionType}: ${question.prompt}` });
      navigate(`/quiz/${session.current_concept_id || notebook?.conceptId}`);
      return;
    }
    setGuidePanel({ title: 'Practice Weakness', body: 'No similar question available yet.' });
  };

  const audioOverview = async () => {
    const audio = await getAudioOverview('teaching_voice_script');
    const voice = (audio.voice_script || audio.audio_overview || {}) as Record<string, unknown>;
    setGuidePanel({ title: 'Audio Overview', body: String(voice.script || 'No audio script available.') });
  };

  if (loading || !notebook) return (
    <div className="flex h-[50vh] flex-col items-center justify-center gap-4 text-slate-400">
      <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      <p className="font-bold">Loading your memory...</p>
    </div>
  );

  const conceptTitle = getConceptDisplayName(session.current_concept_id || notebook.conceptId, session.current_concept_name);
  const nextConceptTitle = getConceptDisplayName('P2', '');
  const keyPoints = notebook.learner_facing_key_points || [];
  const mistakes = notebook.learner_facing_mistakes || notebook.mistakes || [];
  const revisionPlan = notebook.learner_facing_revision_plan || notebook.revisionPlan || [];
  const flashcards = notebook.learner_facing_flashcards || [];
  const doubts = notebook.learner_facing_doubts || [];
  const practiceQueue = notebook.learner_facing_practice_queue || notebook.practiceQueue || [];
  const tabs = ['overview', 'mistakes', 'revision', 'flashcards', 'doubts', 'practice'];

  return (
    <div className="flex min-w-0 flex-col gap-6 pb-20 lg:flex-row lg:pb-4 max-w-[1600px] mx-auto w-full min-h-[calc(100vh-8rem)] px-0 sm:px-2 lg:px-4">
      <div className="lg:hidden"><CogniGuideCard {...getCogniMessage({ page: 'notebook', activityType: 'revision_summary' })} compact /></div>
      
      {/* Left Sidebar - Sources/Chapters */}
      <div className="hidden lg:flex flex-col w-64 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 dark:border-slate-800">
          <h2 className="font-bold text-lg flex items-center gap-2">
            <Folder className="w-5 h-5 text-indigo-500" /> My Sources
          </h2>
        </div>
        <div className="p-3 space-y-1 overflow-y-auto">
          <div className="mt-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
             Concepts
          </div>
          <div className="px-3 py-2.5 bg-indigo-100 dark:bg-indigo-500/20 text-indigo-800 dark:text-indigo-300 font-bold rounded-xl text-sm flex items-center gap-2 cursor-pointer shadow-sm">
             <FileText className="w-4 h-4" /> {conceptTitle}
          </div>
          <div className="px-3 py-2.5 text-slate-600 dark:text-slate-400 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 rounded-xl text-sm flex items-center gap-2 cursor-pointer transition">
             <FileText className="w-4 h-4" /> Next concept: {nextConceptTitle} (Locked)
          </div>
          
          <div className="mt-6 mb-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-400">
             Saved Tools
          </div>
          <div onClick={() => setGuidePanel({ title: 'My Mistakes', body: mistakes.join('\n') || 'No unresolved mistakes yet.' })} className="px-3 py-2 text-slate-600 dark:text-slate-400 flex items-center gap-2 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 rounded-xl text-sm cursor-pointer transition">
             <PenLine className="w-4 h-4 text-emerald-500" /> My Mistakes
          </div>
          <div onClick={audioOverview} className="px-3 py-2 text-slate-600 dark:text-slate-400 flex items-center gap-2 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 rounded-xl text-sm cursor-pointer transition">
             <Headphones className="w-4 h-4 text-amber-500" /> Audio Overviews
          </div>
        </div>
      </div>

      {/* Main Content Area - Notes view */}
      <div className="min-w-0 flex-1 flex flex-col min-h-[640px] lg:min-h-0 bg-white dark:bg-slate-950 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
        
        {/* Notebook Toolbar */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex flex-col sm:flex-row gap-4 items-center justify-between">
           <div>
              <h1 className="text-2xl font-black text-slate-900 dark:text-white">Conceptual Memory</h1>
              <p className="text-sm text-slate-500 font-medium">Auto-generated notes from your learning path</p>
           </div>
           <div className="flex gap-2">
              <button onClick={() => setGuidePanel({ title: 'Study Guide', body: makeStudyGuide(notebook) })} className="flex items-center gap-2 text-sm font-bold px-4 py-2.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-700 dark:text-indigo-400 rounded-xl hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-800 transition">
                 <FileText className="w-4 h-4" /> Study Guide
              </button>
              <button onClick={() => navigate('/notebook/guide')} className="flex items-center gap-2 text-sm font-bold px-4 py-2.5 bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300 rounded-xl border border-sky-200 dark:border-sky-800 transition">
                 <MessageSquare className="w-4 h-4" /> Guide Chat
              </button>
           </div>
        </div>
        <div className="border-b border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fit,minmax(240px,1fr))]">
            <NotebookAction title="Common Mistakes" body={`${mistakes.length} unresolved`} onClick={() => setActiveTab('mistakes')} />
            <NotebookAction title="Practice Focus" body={practiceQueue[0] || 'Ready for review'} onClick={practiceWeakness} />
            <NotebookAction title="Revision Plan" body={`${revisionPlan.length} steps`} onClick={() => setActiveTab('revision')} />
            <NotebookAction title="Flashcards" body={`${flashcards.length || notebook.savedFlashcards?.length || 0} saved`} onClick={() => setActiveTab('flashcards')} />
            <NotebookAction title="Past Doubts" body={`${doubts.length} saved`} onClick={() => setActiveTab('doubts')} />
            <NotebookAction title="Comeback Summary" body="Returning learner" onClick={() => setGuidePanel({ title: 'Comeback Summary', body: String((notebook as NotebookMemory & { comebackSummary?: string; returningLearnerSummary?: string }).comebackSummary || (notebook as NotebookMemory & { returningLearnerSummary?: string }).returningLearnerSummary || 'No comeback summary available yet.') })} />
            <NotebookAction title="Progress Insight" body={session.active_subject || 'Selected subject'} onClick={() => setGuidePanel({ title: 'Progress Insight', body: String((notebook as NotebookMemory & { progressInsight?: string }).progressInsight || 'No progress insight available yet.') })} />
          </div>
        </div>

        {/* Notebook Content Grid */}
        <div className="flex-1 overflow-y-auto w-full p-6 sm:p-8 space-y-8">
           <NotebookSearchPanel learnerId={notebook.learnerId} />
           
           {/* Concept Summary Note */}
           <div className="max-w-4xl">
             <div className="flex items-center gap-2 mb-4">
                <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold uppercase tracking-wider rounded-md">Note</span>
                <span className="text-xs font-medium text-slate-400">Updated {formatDate(notebook.lastUpdated)}</span>
             </div>
             <h2 className="text-3xl sm:text-4xl font-extrabold mb-6 text-slate-900 dark:text-white leading-tight">{conceptTitle} in {session.active_subject || 'your subject'}</h2>
             <div className="mb-5 flex flex-wrap gap-2">
               {tabs.map((tab) => (
                 <button key={tab} onClick={() => setActiveTab(tab)} className={clsx('rounded-full px-4 py-2 text-xs font-black capitalize transition', activeTab === tab ? 'bg-indigo-600 text-white' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200')}>
                   {tab}
                 </button>
               ))}
             </div>
             <div className="grid gap-4 text-slate-700 dark:text-slate-300">
               {activeTab === 'overview' && (
                 <>
                   <Section title="Quick Summary" items={[notebook.summary]} />
                   <Section title="What I should remember" items={keyPoints} empty="No key points saved yet." />
                   <Section title="Revision Plan" items={revisionPlan} ordered empty="No revision plan yet." />
                   <Section title="Practice Queue" items={practiceQueue} empty="No practice queued yet." />
                 </>
               )}
               {activeTab === 'mistakes' && <Section title="My common mistakes" items={mistakes} empty="No unresolved mistakes yet." />}
               {activeTab === 'revision' && <Section title="Revision Plan" items={revisionPlan} ordered empty="No revision plan yet." />}
               {activeTab === 'flashcards' && <FlashcardSection cards={flashcards} fallback={notebook.savedFlashcards || []} />}
               {activeTab === 'doubts' && <DoubtSection doubts={doubts} fallback={notebook.pastDoubts || []} />}
               {activeTab === 'practice' && <Section title="Practice Queue" items={practiceQueue} empty="No practice queued yet." />}
             </div>
           </div>

           {/* Weak Areas Panel */}
           <div className="max-w-4xl bg-rose-50 dark:bg-rose-900/10 p-6 sm:p-8 rounded-3xl border border-rose-100 dark:border-rose-900/30 mt-8">
              <h3 className="text-lg font-bold flex items-center gap-2 text-rose-800 dark:text-rose-300 mb-6">
                 <AlertTriangle className="w-5 h-5 text-rose-500" /> Focus Areas
              </h3>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                 {(mistakes.length ? mistakes : ['No unresolved mistakes yet.']).slice(0, 4).map((pt, i) => (
                   <li key={i} className="flex flex-col gap-2 bg-white dark:bg-slate-900 p-4 rounded-2xl border border-rose-100 dark:border-rose-800/50 shadow-sm">
                     <span className="text-rose-700 dark:text-rose-400 text-sm font-bold">{pt}</span>
                     <span className="text-xs text-slate-500">{mistakes.length ? 'Use the revision plan before retrying' : 'Keep practicing to build memory'}</span>
                   </li>
                 ))}
              </ul>
              <button onClick={practiceWeakness} className="mt-6 inline-flex px-6 py-3 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-full text-sm transition-colors shadow-lg shadow-rose-600/20 active:scale-95">
                 Practice Weaknesses Now
              </button>
           </div>
           
        </div>
      </div>

      {/* Right Sidebar - Chat Interface (NotebookLM style) */}
      <div className="w-full lg:w-[400px] lg:sticky lg:top-4 lg:h-[calc(100vh-7rem)] lg:shrink-0 flex flex-col bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
         <div className="p-5 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/20">
               <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
               <h3 className="font-bold text-slate-900 dark:text-white">Notebook Guide</h3>
               <p className="text-xs text-slate-500 font-medium">Ask questions about your memory</p>
            </div>
         </div>
         
         <div className="flex-1 overflow-y-auto p-5 space-y-6">
            <div className="flex gap-3">
               <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
               </div>
               <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 rounded-tl-none">
                  <p className="text-sm text-slate-700 dark:text-slate-300">
                    Hi! I have access to all your notes and past mistakes. Want me to generate a quick study guide for your upcoming review?
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                     <button onClick={() => askGuide('Ask another practice question')} className="text-xs px-3 py-1.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:text-indigo-600 dark:hover:text-indigo-300 hover:border-indigo-200 dark:hover:border-indigo-800 transition">
                        Generate quiz
                     </button>
                     <button onClick={() => setGuidePanel({ title: 'Study Guide', body: makeStudyGuide(notebook) })} className="text-xs px-3 py-1.5 bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg font-medium text-slate-600 dark:text-slate-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:text-indigo-600 dark:hover:text-indigo-300 hover:border-indigo-200 dark:hover:border-indigo-800 transition">
                        Summarize notes
                     </button>
                  </div>
               </div>
            </div>

            {/* Simulated previous doubt */}
            <div className="flex gap-3 flex-row-reverse">
               <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 shrink-0"></div>
               <div className="bg-indigo-600 rounded-2xl p-4 shadow-sm border border-indigo-600 rounded-tr-none text-white max-w-[85%]">
                  <p className="text-sm">What should I review for {session.current_concept_name || notebook.conceptId}?</p>
               </div>
            </div>
            
            <div className="flex gap-3">
               <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
               </div>
               <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 shadow-sm border border-slate-200 dark:border-slate-700 rounded-tl-none max-w-[85%]">
                  <p className="text-sm text-slate-700 dark:text-slate-300">
                    I will use your saved mistakes, doubts, and revision cards for {session.active_subject || 'the selected subject'}.
                  </p>
               </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {['Generate study guide', 'Summarize notes', 'Ask simpler explanation', 'Ask for analogy', 'Ask for code example', 'Ask why answer is wrong', 'Ask another practice question'].map((label) => (
                <button key={label} onClick={() => askGuide(label)} className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200">{label}</button>
              ))}
            </div>
         </div>

         <div className="p-4 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 shrink-0">
            <div className="relative flex items-center bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-sm overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500 transition-all">
              <input 
                type="text"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                placeholder="Ask about your notes..."
                className="flex-1 bg-transparent border-none px-4 py-3.5 text-sm text-slate-900 dark:text-white focus:outline-none"
              />
              <button onClick={() => { if (chatInput.trim()) askGuide(chatInput.trim()); setChatInput(''); }} className="p-3 text-white bg-slate-900 dark:bg-white dark:text-slate-900 rounded-xl mr-1 hover:scale-105 transition-transform">
                <Send className="w-4 h-4" />
              </button>
            </div>
            <div className="flex justify-center mt-2">
              <span className="text-[10px] font-bold text-slate-400">AI can make mistakes. Verify information.</span>
            </div>
         </div>
         <div className="p-4">
           <button onClick={() => navigate('/tutor/chat')} className="w-full rounded-2xl bg-sky-600 px-4 py-3 text-sm font-black text-white">Open full Tutor Chat</button>
         </div>
      </div>

      {guidePanel.body && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4">
          <div className="max-h-[78vh] w-full max-w-4xl overflow-y-auto rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl dark:border-slate-800 dark:bg-slate-950">
            <div className="mb-4 flex items-start justify-between gap-3">
              <h2 className="text-2xl font-black">{guidePanel.title}</h2>
              <button onClick={() => setGuidePanel({ title: '', body: '' })} className="rounded-xl border border-slate-200 px-3 py-1 text-sm font-bold dark:border-slate-700">Close</button>
            </div>
            <p className="whitespace-pre-wrap text-sm font-semibold leading-7 text-slate-700 dark:text-slate-200">{guidePanel.body}</p>
            <div className="mt-4 flex items-center gap-3">
              <button onClick={saveGuidePanel} className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white">{saveStatus === 'Saved' ? 'Saved' : 'Save to notebook'}</button>
              {saveStatus && <span className="text-sm font-bold text-slate-500">{saveStatus}</span>}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

function Section({ title, items, empty, ordered = false }: { title: string; items: unknown[]; empty?: string; ordered?: boolean }) {
  const values = items.map(String).filter(Boolean);
  if (!values.length) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-black uppercase text-slate-500">{title}</h3>
        <p className="mt-3 text-sm font-semibold text-slate-500">{empty || 'Nothing saved yet.'}</p>
      </section>
    );
  }
  const List = ordered ? 'ol' : 'ul';
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-black uppercase text-slate-500">{title}</h3>
      <List className={clsx('mt-3 space-y-2 pl-5 text-sm font-semibold leading-6', ordered ? 'list-decimal' : 'list-disc')}>
        {values.map((item, index) => <li key={`${title}-${index}`}>{item.length > 240 ? `${item.slice(0, 237)}...` : item}</li>)}
      </List>
    </section>
  );
}

function FlashcardSection({ cards, fallback }: { cards: { front: string; back: string }[]; fallback: string[] }) {
  const normalized = cards.length
    ? cards
    : fallback.map((item) => {
      const match = String(item).match(/^Q:\s*(.*?)\s*A:\s*(.*)$/is);
      return match ? { front: match[1], back: match[2] } : { front: String(item), back: 'Review the saved answer from your notebook.' };
    });
  if (!normalized.length) return <Section title="Saved Flashcards" items={[]} empty="No saved flashcards yet." />;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-black uppercase text-slate-500">Saved Flashcards</h3>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {normalized.slice(0, 5).map((card, index) => (
          <div key={index} className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950">
            <p className="text-xs font-black text-indigo-600 dark:text-indigo-300">Q</p>
            <p className="text-sm font-bold">{card.front}</p>
            <p className="mt-2 text-xs font-black text-emerald-600 dark:text-emerald-300">A</p>
            <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">{card.back}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function DoubtSection({ doubts, fallback }: { doubts: { question: string; answer_preview: string }[]; fallback: string[] }) {
  const normalized = doubts.length
    ? doubts
    : fallback.map((item) => {
      const match = String(item).match(/^Q:\s*(.*?)\s*A:\s*(.*)$/is);
      return match ? { question: match[1], answer_preview: match[2] } : { question: String(item), answer_preview: 'Use the notebook guide for a grounded answer.' };
    });
  if (!normalized.length) return <Section title="Past Doubts" items={[]} empty="No saved doubts yet." />;
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="text-sm font-black uppercase text-slate-500">Past Doubts</h3>
      <div className="mt-3 space-y-3">
        {normalized.slice(0, 5).map((item, index) => (
          <div key={index} className="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-950">
            <p className="text-sm font-bold">{item.question}</p>
            <p className="mt-1 text-sm font-semibold text-slate-600 dark:text-slate-300">{item.answer_preview}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatDate(value?: string) {
  if (!value) return 'after your next saved activity';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'recently';
  return date.toLocaleDateString();
}

function NotebookAction({ title, body, onClick }: { title: string; body: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-left transition hover:border-indigo-200 hover:bg-indigo-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-indigo-900/40 dark:hover:bg-indigo-900/20">
      <p className="text-sm font-black text-slate-900 dark:text-white">{title}</p>
      <p className="mt-1 text-xs font-semibold text-slate-500">{body}</p>
    </button>
  );
}

function makeStudyGuide(notebook: NotebookMemory) {
  return [
    `Summary\n${notebook.summary || 'Saved summary is being prepared.'}`,
    `Key Points\n${(notebook.savedExplanations || notebook.revisionPlan || []).slice(0, 4).map((item) => `- ${item}`).join('\n') || '- Review the definition\n- Try one example'}`,
    `Mistakes to Review\n${(notebook.mistakes || []).slice(0, 4).map((item) => `- ${item}`).join('\n') || '- No unresolved mistakes yet'}`,
    `Flashcards\n${(notebook.savedFlashcards || []).slice(0, 4).map((item) => `- ${item}`).join('\n') || '- What is the key idea?\n- What example proves it?'}`,
    'Practice Questions\n- Explain the concept in one sentence\n- Solve one aligned MCQ\n- Try one output/debug check',
    `Next Revision\n${(notebook.revisionPlan || []).slice(0, 3).map((item) => `- ${item}`).join('\n') || '- Review again after the next assessment'}`,
  ].join('\n\n');
}
