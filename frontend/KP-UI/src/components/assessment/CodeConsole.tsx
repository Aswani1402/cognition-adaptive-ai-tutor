import { useState } from 'react';
import { Play, CheckCircle2, RotateCcw, Terminal, AlertCircle } from 'lucide-react';
import { getHint, runCode, submitAnswer } from '../../lib/api';
import { AssessmentQuestion, CodeRunOutput, CodeSubmitResult } from '../../lib/types';
import RunOutputPanel from './RunOutputPanel';
import TestResultsTable from './TestResultsTable';
import FeedbackCard from './FeedbackCard';
import CodeEditorBox from '../coding/CodeEditorBox';
import HintPanel from './HintPanel';
import clsx from 'clsx';

interface CodeConsoleProps {
  initialCode: string;
  language?: string;
  questionId: string;
  conceptId?: string;
  conceptName?: string;
  subject?: string;
  difficulty?: string;
  questionType?: string;
  question?: AssessmentQuestion;
  onSubmitResult: (result: CodeSubmitResult) => void;
}

export default function CodeConsole({ initialCode, language = 'python', questionId, conceptId, conceptName, subject, difficulty = 'easy', questionType = 'debug_task', question, onSubmitResult }: CodeConsoleProps) {
  const [code, setCode] = useState(initialCode);
  const [runResult, setRunResult] = useState<CodeRunOutput | null>(null);
  const [submitResult, setSubmitResult] = useState<CodeSubmitResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runCount, setRunCount] = useState(0);
  const [answerChangeCount, setAnswerChangeCount] = useState(0);
  const [hintCount, setHintCount] = useState(0);
  const [hintText, setHintText] = useState('');
  const [confidence, setConfidence] = useState(0.6);
  const [startTime] = useState(Date.now());
  const executable = ['python', 'javascript', 'js'].includes(language.toLowerCase());
  const fileLabel = language === 'python' ? 'main.py' : language === 'sql' ? 'query.sql' : language === 'html' ? 'index.html' : language === 'shell' ? 'commands.txt' : 'answer.txt';

  const handleRun = async () => {
    setIsRunning(true);
    setSubmitResult(null);
    setRunResult(null);
    try {
      const res = await runCode({
        learner_id: localStorage.getItem('learner_id') || '',
        language,
        question_id: questionId,
        concept_id: conceptId || localStorage.getItem('current_concept_id') || undefined,
        expected_output: question?.expectedOutput,
        code,
      });
      setRunCount((count) => count + 1);
      setRunResult(res);
    } catch (error) {
      setRunResult({
        status: 'error',
        runOutput: {
          stdout: '',
          stderr: '',
          errorType: 'backend_unavailable',
          blocked: false,
          timedOut: false,
          errorMessage: 'Unable to run live code right now. Showing available learner context.',
        },
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleHint = async () => {
    const data = await getHint({
      question_id: questionId,
      question_type: questionType,
      current_answer: code,
      hint_count: hintCount,
      mastery_score: null,
      behaviour_risk: null,
    });
    setHintCount((count) => count + 1);
    setHintText(String(data.hint_text || data.message || data.hint || 'Run the code mentally first, then compare each line with the expected output.'));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const res = await submitAnswer({
        questionId,
        code,
        answer: code,
        conceptId: conceptId || localStorage.getItem('current_concept_id') || undefined,
        conceptName: conceptName || localStorage.getItem('current_concept_name') || undefined,
        subject: subject || localStorage.getItem('active_subject') || undefined,
        difficulty: difficulty || localStorage.getItem('current_difficulty') || 'easy',
        questionType,
        question,
        run_code_count: runCount,
        confidence,
        time_taken_sec: Math.max(1, Math.round((Date.now() - startTime) / 1000)),
        hint_used: hintCount > 0,
        hint_count: hintCount,
        answer_change_count: Math.max(1, answerChangeCount),
        option_change_count: 0,
        attempt_count: 1,
        wrong_attempt_count: 0,
      });
      setSubmitResult(res);
      onSubmitResult(res);
    } catch (error) {
      setSubmitResult({
        status: 'error',
        score: 0,
        correct: false,
        feedback: 'This content is being prepared. Showing saved learning content instead.',
        nextAction: 'retry',
        questionId,
        taskType: questionType,
        testResults: [],
        weakAreas: [],
        runOutput: { stdout: '', stderr: '', errorType: null, errorMessage: null, timedOut: false, blocked: false },
      } as CodeSubmitResult);
    } finally {
      setIsSubmitting(false);
    }
  };

  const output = runResult?.runOutput;

  return (
    <div className="flex w-full min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-700 bg-[#0d1117] shadow-xl">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2"><Terminal className="w-4 h-4 text-slate-400" /><span className="text-xs font-mono text-slate-300 font-bold">{fileLabel}</span></div>
        <button onClick={() => setCode(initialCode)} className="text-xs text-slate-400 hover:text-white flex items-center gap-1"><RotateCcw className="w-3 h-3" /> Reset</button>
      </div>
      <CodeEditorBox value={code} onChange={(value) => { setAnswerChangeCount((count) => count + 1); setCode(value); }} disabled={isSubmitting} />
      <div className="border-t border-slate-800 bg-slate-900 px-4 py-3">
        <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-300">
          <span>I feel confident</span>
          {[['Low', 0.3], ['Medium', 0.6], ['High', 0.9]].map(([label, value]) => (
            <button key={label as string} onClick={() => setConfidence(value as number)} className={clsx('rounded-full px-3 py-1 text-xs font-bold', confidence === value ? 'bg-sky-600 text-white' : 'bg-slate-800 text-slate-200')}>{label}</button>
          ))}
          <button onClick={handleHint} disabled={!!submitResult} className="rounded-full bg-amber-500 px-3 py-1 text-xs font-bold text-white disabled:opacity-50">Need a hint?</button>
        </div>
        {hintText && <div className="mb-3"><HintPanel hints={[hintText]} /></div>}
        <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {executable && <button onClick={handleRun} disabled={isRunning || isSubmitting} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-white font-bold text-sm disabled:opacity-50"><Play className="w-4 h-4 text-emerald-400" /> {isRunning ? 'Running...' : 'Run'}</button>}
          <button onClick={() => { setCode(initialCode); setRunResult(null); setSubmitResult(null); }} className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 text-sm font-bold">Reset</button>
        </div>
        <button onClick={handleSubmit} disabled={isRunning || isSubmitting} className="flex items-center gap-2 px-6 py-2 rounded-lg bg-sky-600 text-white font-bold text-sm disabled:opacity-50"><CheckCircle2 className="w-4 h-4" /> {isSubmitting ? 'Submitting...' : 'Submit'}</button>
        </div>
      </div>

      {(output || submitResult) && (
        <div className="border-t border-slate-800 bg-[#0a0d12] p-4 font-mono text-sm space-y-3">
          {output?.timedOut && <Warning>Execution timed out.</Warning>}
          {output?.blocked && <Warning>Execution blocked by sandbox policy.</Warning>}
          {output?.errorType && <div className="text-amber-400">{output.errorType}: {output.errorMessage}</div>}
          {output && <RunOutputPanel output={output} />}

          {submitResult && (
            <>
              <FeedbackCard score={submitResult.score} feedback={submitResult.feedback} />
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-3 text-xs text-slate-300">
                <p><span className="font-bold text-slate-100">Your answer:</span> {code}</p>
                <p className="mt-2"><span className="font-bold text-slate-100">Correct answer:</span> {(submitResult as unknown as Record<string, unknown>).correct_answer as string || question?.correctAnswer || question?.expectedOutput || 'See explanation'}</p>
                <p className="mt-2"><span className="font-bold text-slate-100">Explanation:</span> {shortConsoleText((submitResult as unknown as Record<string, unknown>).explanation as string || submitResult.feedback)}</p>
              </div>
              <TestResultsTable rows={submitResult.testResults ?? []} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function shortConsoleText(value: string) {
  const text = String(value || '').replace(/\s+/g, ' ').trim();
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, 3).join(' ');
  return sentences.length > 300 ? `${sentences.slice(0, 297).trim()}...` : sentences;
}

function Warning({ children }: { children: string }) {
  return <div className="flex items-center gap-2 text-amber-400"><AlertCircle className="w-4 h-4" />{children}</div>;
}
