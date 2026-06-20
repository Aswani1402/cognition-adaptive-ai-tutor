import React, { useState } from 'react';
import { Send, Sparkles, Code2, AlertTriangle, ChevronDown, CheckCircle2, HelpCircle, Copy } from 'lucide-react';
import { askDoubt, submitDoubtFollowUp } from '../../lib/api';
import { DoubtResponse } from '../../lib/types';
import clsx from 'clsx';
import { useLearnerSession } from '../../context/LearnerSessionContext';
import CogniSpeechBubble from '../mascot/CogniSpeechBubble';

interface DoubtPanelProps {
  conceptName: string;
  conceptId: string;
  currentTeachingView?: string;
}

export default function DoubtPanel({ conceptName, conceptId, currentTeachingView = 'code_view' }: DoubtPanelProps) {
  const session = useLearnerSession();
  const activeConceptName = conceptName || session.current_concept_name || 'Select a concept first';
  const activeConceptId = conceptId || session.current_concept_id;
  const activeSubject = session.active_subject || 'Select a subject first';
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<DoubtResponse | null>(null);
  const [followUpAnswered, setFollowUpAnswered] = useState(false);
  const [copied, setCopied] = useState(false);

  const submitDoubt = async (doubtText: string) => {
    if (!doubtText.trim()) return;
    setLoading(true);
    const res = await askDoubt({
      learnerId: session.getCurrentLearnerId(),
      doubtText,
      currentConceptId: activeConceptId,
      currentConceptName: activeConceptName,
      domain: activeSubject,
      difficulty: (session.current_difficulty || 'easy') as any,
      currentTeachingView,
      weakestSkill: 'debug',
      dominantMistakeType: 'syntax',
    });
    setResponse(res);
    setLoading(false);
    setQuery('');
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    await submitDoubt(query);
  };

  const handleQuickAction = async (text: string) => {
    setQuery(text);
    await submitDoubt(text);
  };

  const handleFollowUpSelect = async () => {
    await submitDoubtFollowUp({ learnerId: session.getCurrentLearnerId(), conceptId: activeConceptId, correct: true });
    setFollowUpAnswered(true);
  };

  const copyCode = async (code: string) => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-900">
      {/* Context Banner */}
      <div className="px-4 py-3 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-100 dark:border-indigo-900/50 flex flex-wrap gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">Context:</span>
        <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
          {activeSubject}
        </span>
        <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
          {activeConceptName}
        </span>
        <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Difficulty: {session.current_difficulty || 'easy'}</span>
        <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">Teaching view: {currentTeachingView.replace('_view', '').replaceAll('_', ' ')}</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {!response && !loading && (
          <div className="text-center py-10 opacity-70">
            <Sparkles className="w-12 h-12 mx-auto mb-4 text-slate-400" />
            <p className="text-slate-500">Ask any doubt about {activeConceptName}. I'm here to help.</p>
            
            <div className="mt-8 flex flex-col gap-2">
              <button onClick={() => handleQuickAction("Explain this simply")} className="text-sm px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 hover:bg-slate-100 transition">
                Explain this simply
              </button>
              <button onClick={() => handleQuickAction("Show me an example")} className="text-sm px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 hover:bg-slate-100 transition">
                Show me an example
              </button>
              <button onClick={() => handleQuickAction("Debug my code")} className="text-sm px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 hover:bg-slate-100 transition">
                Debug my code
              </button>
              <button onClick={() => handleQuickAction("What should I revise?")} className="text-sm px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 hover:bg-slate-100 transition">
                What should I revise?
              </button>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-3 text-slate-500 animate-pulse bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-200 dark:border-slate-700">
            <Sparkles className="w-5 h-5 text-indigo-500" />
            <span>Finding grounded explanation...</span>
          </div>
        )}

        {response && (
          <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
            {!response.ragGrounded && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/30 dark:bg-amber-900/20 dark:text-amber-200">
                This answer may need review because source grounding confidence is low.
              </div>
            )}
            {/* Answer Card */}
            {response.voiceScript && (
              <div>
                <p className="mb-2 text-xs font-black uppercase tracking-wider text-emerald-600 dark:text-emerald-300">Voice-ready script</p>
                <CogniSpeechBubble message={response.voiceScript} />
              </div>
            )}
            <div className="bg-white dark:bg-slate-950 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
              <div className="px-4 py-3 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-bold text-xs uppercase tracking-wider">
                  {response.doubtType.replace('_', ' ')}
                </span>
                {response.ragGrounded && (
                  <span className="inline-flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-medium ml-auto">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Grounded
                  </span>
                )}
              </div>
              <div className="p-4 prose dark:prose-invert text-sm max-w-none text-slate-700 dark:text-slate-300">
                <p>{response.answer}</p>
                {response.simpleExplanation && (
                  <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/10 border-l-2 border-amber-400 text-amber-900 dark:text-amber-200 rounded-r-lg">
                    <strong>Simple term:</strong> {response.simpleExplanation}
                  </div>
                )}
              </div>
            </div>

            {/* Example Card */}
            {response.example && (
              <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-lg">
                <div className="px-4 py-2 bg-slate-800 flex items-center justify-between border-b border-slate-700">
                  <span className="text-xs font-bold text-slate-300 flex items-center gap-2 mt-1 mb-1">
                    <Code2 className="w-4 h-4" /> {response.example.title}
                  </span>
                  <button onClick={() => copyCode(response.example?.code || '')} className="rounded-lg bg-slate-700 px-2 py-1 text-[10px] font-semibold text-slate-200 hover:bg-slate-600 inline-flex items-center gap-1"><Copy className="w-3 h-3" />{copied ? 'Copied' : 'Copy code'}</button>
                </div>
                <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto bg-[#0d1117]">
                  <code>{response.example.code}</code>
                </pre>
                <div className="p-3 bg-slate-800/50 text-xs text-slate-400 border-t border-slate-800">
                  {response.example.explanation}
                </div>
              </div>
            )}

            {response.memoryUpdateSuggestion && (
              <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4 dark:border-cyan-900/40 dark:bg-cyan-900/20">
                <p className="text-sm font-bold text-cyan-800 dark:text-cyan-200">Added to your revision notebook</p>
                <p className="mt-1 text-xs text-cyan-700 dark:text-cyan-300">Weak area: {response.memoryUpdateSuggestion.weakConcept} - {response.memoryUpdateSuggestion.weakQuestionType}</p>
                <p className="text-xs text-cyan-700 dark:text-cyan-300">Mistake type: {response.memoryUpdateSuggestion.mistakeType}</p>
                <button className="mt-3 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white">Start recommended revision</button>
              </div>
            )}

            {/* Follow-up Check */}
            {response.followUpCheck && (
              <div className="bg-indigo-50 dark:bg-indigo-900/10 rounded-2xl border border-indigo-200 dark:border-indigo-900/50 p-4">
                <h4 className="flex items-center gap-2 text-sm font-bold text-indigo-900 dark:text-indigo-100 mb-3">
                  <HelpCircle className="w-4 h-4 text-indigo-600" /> Let's check your understanding
                </h4>
                <p className="text-sm text-slate-700 dark:text-slate-300 mb-4">{response.followUpCheck.question}</p>
                <div className="space-y-2">
                  {response.followUpCheck.options?.map((opt, i) => (
                    <button 
                      key={i}
                      onClick={handleFollowUpSelect}
                      className={clsx(
                        "w-full text-left px-4 py-2.5 rounded-xl border text-sm transition-colors",
                        followUpAnswered && opt === response.followUpCheck?.correctAnswer
                          ? "bg-emerald-100 border-emerald-300 text-emerald-900 dark:bg-emerald-900/30 dark:border-emerald-800 dark:text-emerald-200 font-bold"
                          : followUpAnswered 
                            ? "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 opacity-50"
                            : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20"
                      )}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
                {followUpAnswered && (
                  <div className="mt-4 flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/30">
                    <CheckCircle2 className="w-5 h-5" /> Memory updated! You can continue the lesson.
                  </div>
                )}
              </div>
            )}
            
            {/* Next Action */}
            {followUpAnswered && (
              <div className="text-center pt-2 pb-6">
                 <button className="px-6 py-2 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-full text-sm font-bold shadow-md hover:scale-105 transition-transform">
                   Continue Lesson
                 </button>
              </div>
            )}

            {/* Optional Source Detail */}
            <details className="text-xs text-slate-500 group">
              <summary className="flex items-center gap-1 cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-300">
                <ChevronDown className="w-4 h-4 group-open:-rotate-180 transition-transform" />
                View retrieved context
              </summary>
              <div className="mt-2 pl-5 pr-2 py-2 border-l-2 border-slate-200 dark:border-slate-700">
                {response.retrievedContextSummary}
              </div>
            </details>
          </div>
        )}
      </div>

      {/* Input Box */}
      <div className="p-4 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a doubt about Variable Naming..."
            className="w-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white rounded-full pl-5 pr-12 py-3.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm"
          />
          <button 
            type="submit"
            disabled={!query.trim()}
            className="absolute right-2 p-2 rounded-full bg-indigo-600 text-white hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
