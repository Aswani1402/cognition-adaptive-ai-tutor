import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Gamepad2, ArrowRight, Zap, RefreshCw, CheckCircle2 } from 'lucide-react';
import clsx from 'clsx';
import { getHint, getPuzzleActivities, submitAnswer } from '../lib/api';
import { PuzzleActivity } from '../lib/types';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { logFrontendEvent } from '../lib/eventLog';

export default function PuzzlePage() {
  const { conceptId } = useParams();
  const session = useLearnerSession();
  const [challenges, setChallenges] = useState<PuzzleActivity[]>([]);
  const [currentChallenge, setCurrentChallenge] = useState(0);
  const [activeType, setActiveType] = useState('All');
  const [answer, setAnswer] = useState("");
  const [status, setStatus] = useState<'idle' | 'checking' | 'correct' | 'wrong'>('idle');
  const [confidence, setConfidence] = useState(0.6);
  const [hintCount, setHintCount] = useState(0);
  const [hintText, setHintText] = useState('');
  const [answerChangeCount, setAnswerChangeCount] = useState(0);
  const [attemptCount, setAttemptCount] = useState(1);
  const [wrongAttemptCount, setWrongAttemptCount] = useState(0);
  const startTime = useRef(Date.now());

  useEffect(() => {
    const activeConcept = conceptId || session.current_concept_id;
    if (activeConcept) getPuzzleActivities(session.getCurrentLearnerId(), activeConcept, session.active_subject).then(setChallenges);
  }, [conceptId, session.active_subject, session.current_concept_id]);

  const visibleChallenges = challenges.filter((item) => activeType === 'All' || typeLabel(item.type) === activeType);
  const challenge = visibleChallenges[currentChallenge] || visibleChallenges[0];

  useEffect(() => {
    startTime.current = Date.now();
    setHintCount(0);
    setHintText('');
    setAnswerChangeCount(0);
    setAttemptCount(1);
    setWrongAttemptCount(0);
  }, [currentChallenge]);

  if (!challenge) {
    return <div className="grid h-[45vh] place-items-center text-slate-500">Loading challenge...</div>;
  }

  const handleCheck = async () => {
    setStatus('checking');
    logFrontendEvent({ action: 'answer_submitted', module: 'puzzle', status: 'started', summary: challenge.type });
    const localCorrect = answer.toLowerCase().trim() === challenge.solution.toLowerCase().trim() ||
      answer.toLowerCase().includes(challenge.solution.toLowerCase().slice(0, 24).trim());
    const result = await submitAnswer({
      learner_id: session.getCurrentLearnerId(),
      subject: session.active_subject,
      conceptId: challenge.conceptId || conceptId || session.current_concept_id,
      conceptName: session.current_concept_name || challenge.title,
      difficulty: session.current_difficulty,
      questionId: challenge.id,
      questionType: `puzzle_${challenge.type}`,
      answer,
      question: {
        questionId: challenge.id,
        taskType: `puzzle_${challenge.type}`,
        questionType: `puzzle_${challenge.type}`,
        prompt: challenge.prompt,
        code: challenge.code,
        correctAnswer: challenge.solution,
        sourceConcept: challenge.conceptId,
        subject: session.active_subject,
        difficulty: session.current_difficulty,
      },
      confidence,
      time_taken_sec: Math.max(1, Math.round((Date.now() - startTime.current) / 1000)),
      hint_used: hintCount > 0,
      hint_count: hintCount,
      option_change_count: 0,
      answer_change_count: answerChangeCount,
      run_code_count: 0,
      attempt_count: attemptCount,
      wrong_attempt_count: wrongAttemptCount + (localCorrect ? 0 : 1),
    });
    const correct = Boolean(result.correct || localCorrect);
    setStatus(correct ? 'correct' : 'wrong');
    if (!correct) {
      setWrongAttemptCount((count) => count + 1);
      setAttemptCount((count) => count + 1);
    }
  };

  const handleHint = async () => {
    const data = await getHint({
      question_id: challenge.id,
      question_type: `puzzle_${challenge.type}`,
      current_answer: answer,
      hint_count: hintCount,
    });
    setHintCount((count) => count + 1);
    setHintText(String(data.hint_text || data.message || data.hint || challenge.hint || 'Review the prompt and compare it with the code.'));
  };

  const nextChallenge = () => {
    if (currentChallenge < visibleChallenges.length - 1) {
      setCurrentChallenge(c => c + 1);
      setAnswer("");
      setStatus('idle');
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full pb-20 pt-8">
      <header className="mb-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Gamepad2 className="w-8 h-8 text-indigo-500" />
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">Brain Teasers</h1>
        </div>
        <div className="flex gap-1.5">
           {[...Array(visibleChallenges.length)].map((_, i) => (
             <div key={i} className={clsx("h-2.5 rounded-full transition-all duration-300", 
                i === currentChallenge ? "w-8 bg-indigo-500" : 
                i < currentChallenge ? "w-2.5 bg-emerald-500" : "w-2.5 bg-slate-200 dark:bg-slate-800"
             )} />
           ))}
        </div>
      </header>
      <div className="mb-5 flex gap-2 overflow-x-auto">
        {['All', 'Transfer', 'Real-world Application', 'Debug Challenge', 'Output Prediction Challenge', 'Order Puzzle', 'Multi-step Challenge'].map((item) => (
          <button
            key={item}
            onClick={() => { setActiveType(item); setCurrentChallenge(0); setStatus('idle'); setAnswer(''); }}
            className={clsx('shrink-0 rounded-full px-4 py-2 text-sm font-bold', activeType === item ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300')}
          >
            {item}
          </button>
        ))}
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden flex flex-col min-h-[500px]">
        {/* Top visual area */}
        <div className="bg-indigo-600 p-8 sm:p-12 text-white relative overflow-hidden">
           <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
           <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/20 backdrop-blur-sm rounded-full text-sm font-bold mb-6">
             <Zap className="w-4 h-4 text-amber-300" />
             {typeLabel(challenge.type)} · {challenge.title}
           </div>
           <h2 className="text-2xl sm:text-3xl font-bold leading-tight relative z-10 max-w-xl">
             {challenge.prompt}
           </h2>
        </div>

        {/* Content area */}
        <div className="p-8 sm:p-12 flex-1 flex flex-col">
          
          {challenge.code ? (
            <div className="bg-slate-900 rounded-xl p-4 sm:p-6 mb-8 font-mono text-sm sm:text-base text-slate-300 shadow-inner relative group">
               <div className="absolute top-3 right-3 text-[10px] uppercase font-bold tracking-wider text-slate-600">{session.active_subject || 'subject'}</div>
               <pre><code>{challenge.code}</code></pre>
            </div>
          ) : (
            <div className="mb-8 rounded-xl border border-indigo-100 bg-indigo-50 p-4 text-sm font-semibold text-indigo-900 dark:border-indigo-900/40 dark:bg-indigo-900/20 dark:text-indigo-100">
              Apply the concept in a short answer. Use one clear rule and one example if needed.
            </div>
          )}

          <div className="mt-auto">
             <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-3 uppercase tracking-wider">Your Answer</label>
             <textarea
               value={answer}
               onChange={(e) => { setAnswer(e.target.value); setStatus('idle'); setAnswerChangeCount((count) => count + 1); }}
               placeholder={placeholderForChallenge(challenge.type)}
               className={clsx(
                 "min-h-[112px] w-full resize-y p-4 rounded-xl border-2 transition-all outline-none text-base font-semibold",
                 status === 'wrong' ? "border-rose-300 bg-rose-50 dark:bg-rose-900/10 text-rose-900 dark:text-rose-100 focus:border-rose-500 focus:ring-4 focus:ring-rose-500/20" :
                 status === 'correct' ? "border-emerald-300 bg-emerald-50 dark:bg-emerald-900/10 text-emerald-900 dark:text-emerald-100" :
                 "border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-white focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/20"
               )}
               disabled={status === 'correct' || status === 'checking'}
             />
             
             {status === 'wrong' && (
               <p className="mt-3 text-sm font-bold text-rose-500 animate-in slide-in-from-top-2">That doesn't look quite right. Try again!</p>
             )}
          </div>
        </div>

        {/* Action bar */}
        <div className="p-6 sm:px-12 bg-slate-50 dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center">
           <button className="text-slate-500 font-bold text-sm hover:text-slate-800 dark:hover:text-slate-200 transition-colors">
              <span onClick={handleHint}>Need a hint?</span>
           </button>
           <div className="flex items-center gap-2 text-xs font-bold text-slate-500">
             {(['Low', 'Medium', 'High'] as const).map((label) => {
               const value = label === 'Low' ? 0.3 : label === 'Medium' ? 0.6 : 0.9;
               return <button key={label} onClick={() => setConfidence(value)} className={clsx('rounded-full px-2 py-1', confidence === value ? 'bg-indigo-600 text-white' : 'bg-white dark:bg-slate-900')}>{label}</button>;
             })}
           </div>
           
           {status !== 'correct' ? (
             <button 
               onClick={handleCheck}
               disabled={!answer.trim() || status === 'checking'}
               className="flex items-center justify-center min-w-[120px] py-3 px-6 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow-md gap-2"
             >
               {status === 'checking' ? <RefreshCw className="w-5 h-5 animate-spin" /> : 'Check'}
             </button>
           ) : (
             <button 
               onClick={nextChallenge}
               className="flex items-center justify-center min-w-[120px] py-3 px-6 rounded-xl font-bold text-white bg-emerald-500 hover:bg-emerald-600 transition-all shadow-sm shadow-emerald-500/20 hover:shadow-md hover:shadow-emerald-500/40 gap-2 animate-in fade-in"
             >
               Next <ArrowRight className="w-5 h-5" />
             </button>
           )}
        </div>
        {hintText && <p className="px-8 pb-4 text-sm font-semibold text-amber-600 dark:text-amber-300">{hintText}</p>}
      </div>
    </div>
  );
}

function typeLabel(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes('real')) return 'Real-world Application';
  if (normalized.includes('debug')) return 'Debug Challenge';
  if (normalized.includes('output') || normalized.includes('predict')) return 'Output Prediction Challenge';
  if (normalized.includes('logic') || normalized.includes('order')) return 'Order Puzzle';
  if (normalized.includes('multi') || normalized.includes('logic')) return 'Multi-step Challenge';
  if (normalized.includes('transfer') || normalized.includes('challenge')) return 'Transfer';
  return 'Multi-step Challenge';
}

function placeholderForChallenge(type: string) {
  const normalized = type.toLowerCase();
  if (normalized.includes('debug')) return 'Type the corrected command, query, or snippet...';
  if (normalized.includes('output') || normalized.includes('predict')) return 'Type the expected result...';
  if (normalized.includes('logic') || normalized.includes('order')) return 'Type the ordered steps...';
  return 'Type your answer...';
}
