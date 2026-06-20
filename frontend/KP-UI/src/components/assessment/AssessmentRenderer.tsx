import { AssessmentQuestion, CodeSubmitResult } from '../../lib/types';
import { useEffect, useRef, useState, type FC } from 'react';
import { useNavigate } from 'react-router-dom';
import { getHint, submitAnswer } from '../../lib/api';
import clsx from 'clsx';
import { ArrowRight, CheckCircle2, GripVertical } from 'lucide-react';
import CodeConsole from './CodeConsole';
import HintPanel from './HintPanel';
import { MCQQuestionCard, DebugQuestionCard, OutputPredictionCard, SyntaxCompletionCard, CodeWritingCard, DragOrderQuestionCard, MatchPairsQuestionCard, FillBlankQuestionCard, ChallengeQuestionCard, TransferQuestionCard, ShortExplanationCard } from './cards/QuestionCards';
import ReadAloudButton from '../common/ReadAloudButton';

interface Props {
  question: AssessmentQuestion;
  questionIndex?: number;
  questionTotal?: number;
  onComplete: (score: number) => void;
  onResult?: (result: CodeSubmitResult) => void;
}

const AssessmentRenderer: FC<Props> = ({ question, questionIndex = 0, questionTotal = 1, onComplete, onResult }) => {
  const navigate = useNavigate();
  const [selectedOpt, setSelectedOpt] = useState<string | null>(null);
  const [textAnswer, setTextAnswer] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CodeSubmitResult | null>(null);
  const [sortItems, setSortItems] = useState(normalizeSortItems(question.items || question.options || []));
  const [blankAnswers, setBlankAnswers] = useState<Record<string, string>>({});
  const [pairAnswers, setPairAnswers] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState(0.6);
  const [hintText, setHintText] = useState('');
  const [hintVariants, setHintVariants] = useState<string[]>([]);
  const [hintMeta, setHintMeta] = useState<{ type?: string; level?: number }>({});
  const [hintCount, setHintCount] = useState(0);
  const [optionChangeCount, setOptionChangeCount] = useState(0);
  const [answerChangeCount, setAnswerChangeCount] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [frozenElapsedSec, setFrozenElapsedSec] = useState<number | null>(null);
  const startTime = useRef(Date.now());

  useEffect(() => {
    startTime.current = Date.now();
    setElapsedSec(0);
    setHintText('');
    setHintVariants([]);
    setHintMeta({});
    setHintCount(0);
    setOptionChangeCount(0);
    setAnswerChangeCount(0);
    setResult(null);
    setSelectedOpt(null);
    setTextAnswer('');
    setSortItems(normalizeSortItems(question.items || question.options || []));
    setFrozenElapsedSec(null);
  }, [question.questionId]);

  useEffect(() => {
    const id = window.setInterval(() => {
      if (result || frozenElapsedSec !== null || submitting) return;
      setElapsedSec(Math.max(0, Math.round((Date.now() - startTime.current) / 1000)));
    }, 1000);
    return () => window.clearInterval(id);
  }, [question.questionId, result, frozenElapsedSec, submitting]);

  const task = canonicalTaskType(question);
  const normalizedTask = task.toLowerCase();

  const isCodeTask = ['debug', 'debug_task', 'debug_challenge', 'coding_question', 'coding_prompt', 'code_reasoning_task'].includes(normalizedTask);
  const isOutputPrediction = ['output_prediction', 'output_prediction_challenge', 'code_tracing', 'output_reasoning'].includes(normalizedTask);
  const isMultipleChoice = ['mcq', 'multiple_choice', 'true_false', 'true_or_false'].includes(normalizedTask);
  const isDragOrder = normalizedTask === 'drag_order';
  const isPuzzle = normalizedTask === 'puzzle';
  const isMatchPairs = normalizedTask === 'match_pairs';
  const isFillBlank = ['fill_blank', 'fill_in_the_blank'].includes(normalizedTask);

  const handleSubmit = async (answerData?: unknown) => {
    const finalTime = Math.max(1, Math.round((Date.now() - startTime.current) / 1000));
    setElapsedSec(finalTime);
    setFrozenElapsedSec(finalTime);
    setSubmitting(true);
    const answer = answerData ?? selectedOpt ?? textAnswer;
    const res = await submitAnswer({
      questionId: question.questionId,
      conceptId: question.concept_id || question.sourceConcept || localStorage.getItem('current_concept_id') || question.questionId.split('-')[0],
      subject: localStorage.getItem('active_subject') || question.subject,
      conceptName: question.concept_name || localStorage.getItem('current_concept_name') || question.sourceConcept,
      questionType: question.questionType || question.taskType,
      taskType: question.taskType,
      difficulty: question.difficulty,
      answer,
      question,
      confidence,
      time_taken_sec: finalTime,
      hint_used: hintCount > 0,
      hint_count: hintCount,
      option_change_count: optionChangeCount,
      answer_change_count: answerChangeCount,
      run_code_count: 0,
      code_runs: 0,
      attempt_count: 1,
      attempts: 1,
      wrong_attempt_count: 0,
    });
    const normalizedRes = normalizeFeedbackResult(res);
    setResult(normalizedRes);
    onResult?.(normalizedRes);
    setSubmitting(false);
  };

  const handleHint = async () => {
    const data = await getHint({
      question_id: question.questionId,
      subject: localStorage.getItem('active_subject') || question.subject,
      concept_id: question.sourceConcept || localStorage.getItem('current_concept_id') || question.questionId.split('-')[0],
      concept_name: localStorage.getItem('current_concept_name') || question.concept_name || question.sourceConcept,
      difficulty: question.difficulty,
      question_type: question.questionType || question.taskType,
      current_answer: selectedOpt || textAnswer || JSON.stringify(blankAnswers),
      hint_count: hintCount,
      mastery_score: null,
      behaviour_risk: null,
    });
    setHintCount((count) => count + 1);
    setHintText(String(data.hint_text || data.message || data.hint || question.hidden_hint || question.hint || 'Review the key idea, then try again.'));
    setHintMeta({ type: String(data.hint_type || 'guided_hint'), level: Number(data.hint_level || hintCount + 1) });
    const available = data.available_hints && typeof data.available_hints === 'object'
      ? Object.entries(data.available_hints as Record<string, unknown>).map(([type, text]) => `${type.replaceAll('_', ' ')}: ${String(text)}`)
      : [];
    setHintVariants(available);
  };

  return (
    <div className="w-full space-y-6">
      <div className="bg-white dark:bg-slate-900 rounded-3xl p-6 sm:p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <span className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">{task.replace(/_/g, ' ')}</span>
          <span className={clsx('px-3 py-1 rounded-lg text-xs font-bold uppercase', question.difficulty === 'easy' ? 'bg-emerald-100 text-emerald-700' : question.difficulty === 'medium' ? 'bg-orange-100 text-orange-700' : 'bg-rose-100 text-rose-700')}>{question.difficulty}</span>
          <span className="rounded-lg bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-200">Question {questionIndex + 1}/{questionTotal}</span>
          <span className="ml-auto rounded-lg bg-slate-900 px-3 py-1 text-xs font-bold text-white dark:bg-slate-100 dark:text-slate-900">Time: {formatTime(frozenElapsedSec ?? elapsedSec)}</span>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold mb-6">{question.prompt}</h2>
        <div className="mb-4">
          {renderCard(normalizedTask, question)}
        </div>

        {isMultipleChoice && !question.options?.length && !normalizedTask.includes('true') && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm font-bold text-amber-900 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-100">
            MCQ options not available. Please refresh or try the next generated question.
          </div>
        )}

        {isMultipleChoice && (question.options?.length ? question.options : normalizedTask.includes('true') ? ['True', 'False'] : []).map((opt) => (
          <button key={opt} title={opt} onClick={() => { if (selectedOpt && selectedOpt !== opt) setOptionChangeCount((count) => count + 1); setSelectedOpt(opt); }} disabled={!!result} className={clsx('w-full text-left p-4 rounded-xl border-2 transition-all font-medium mb-3', selectedOpt === opt ? 'border-sky-500 bg-sky-50 dark:bg-sky-900/20' : 'border-slate-200 dark:border-slate-700')}>
            {shortOption(opt)}
          </button>
        ))}

        {isCodeTask && <CodeConsole
          initialCode={question.buggyCode || question.starterCode || question.code || ''}
          language={languageForSubject(localStorage.getItem('active_subject') || question.subject || '')}
          questionId={question.questionId}
          conceptId={question.sourceConcept || localStorage.getItem('current_concept_id') || undefined}
          conceptName={localStorage.getItem('current_concept_name') || question.sourceConcept}
          subject={localStorage.getItem('active_subject') || question.subject}
          difficulty={question.difficulty}
          questionType={question.questionType || question.taskType}
          question={question}
          onSubmitResult={(res) => {
            const normalizedRes = normalizeFeedbackResult(res);
            setResult(normalizedRes);
            setFrozenElapsedSec(elapsedSec);
            onResult?.(normalizedRes);
          }}
        />}

        {isOutputPrediction && (
          <div className="space-y-4">
            {(question.code || question.code_snippet) && <pre className="overflow-x-auto rounded-xl bg-slate-950 p-4 text-sm text-slate-200"><code>{question.code || question.code_snippet}</code></pre>}
            <input type="text" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-4" placeholder="Type expected output" value={textAnswer} onChange={(e) => { setAnswerChangeCount((count) => count + 1); setTextAnswer(e.target.value); }} disabled={!!result} />
          </div>
        )}

        {isFillBlank && (
          <div className="space-y-3">
            {(question.blanks?.length ? question.blanks : [{ id: 'answer', label: 'blank', answer: question.correctAnswer || '' }]).map((blank) => (
              <label key={blank.id} className="block">
                <span className="mb-1 block text-xs font-bold uppercase text-slate-500">{blank.label}</span>
                <input type="text" className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-4" placeholder="Type missing syntax" value={blankAnswers[blank.id] || ''} onChange={(e) => { setAnswerChangeCount((count) => count + 1); setBlankAnswers((curr) => ({ ...curr, [blank.id]: e.target.value })); }} disabled={!!result} />
              </label>
            ))}
          </div>
        )}

        {(isDragOrder || isPuzzle) && <div className="space-y-3">{sortItems.map((item, idx) => <div key={`${item}-${idx}`} className="flex items-center gap-3 p-4 bg-white dark:bg-slate-900 border-2 border-slate-200 dark:border-slate-700 rounded-xl"><GripVertical className="w-5 h-5 text-slate-400" /><span className="flex-1 font-mono text-slate-700 dark:text-slate-300">{item}</span><button disabled={idx === 0 || !!result} onClick={() => setSortItems((items) => move(items, idx, idx - 1))} className="rounded-lg border px-2 py-1 text-xs disabled:opacity-40">Up</button><button disabled={idx === sortItems.length - 1 || !!result} onClick={() => setSortItems((items) => move(items, idx, idx + 1))} className="rounded-lg border px-2 py-1 text-xs disabled:opacity-40">Down</button></div>)}</div>}

        {isMatchPairs && <div className="grid grid-cols-1 md:grid-cols-2 gap-3">{(question.pairs ?? []).map((p, i) => <label key={i} className="p-3 rounded-xl border border-slate-200 dark:border-slate-700"><span className="mb-2 block font-bold">{p.left}</span><select value={pairAnswers[p.left] || ''} onChange={(e) => { setAnswerChangeCount((count) => count + 1); setPairAnswers((curr) => ({ ...curr, [p.left]: e.target.value })); }} className="w-full rounded-lg border border-slate-200 bg-white p-2 dark:border-slate-700 dark:bg-slate-950"><option value="">Choose match</option>{(question.pairs ?? []).map((option) => <option key={option.right} value={option.right}>{option.right}</option>)}</select></label>)}</div>}

        {!isMultipleChoice && !isCodeTask && !isOutputPrediction && !isDragOrder && !isPuzzle && !isFillBlank && !isMatchPairs && <textarea className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-4 min-h-[120px]" placeholder={placeholderForTask(normalizedTask)} value={textAnswer} onChange={(e) => { setAnswerChangeCount((count) => count + 1); setTextAnswer(e.target.value); }} disabled={!!result} />}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-900">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <span>I feel confident</span>
            {[['Low', 0.3], ['Medium', 0.6], ['High', 0.9]].map(([label, value]) => (
              <button key={label as string} onClick={() => setConfidence(value as number)} className={clsx('rounded-full px-3 py-1 text-xs font-bold', confidence === value ? 'bg-sky-600 text-white' : 'bg-white text-slate-600 dark:bg-slate-800 dark:text-slate-200')}>{label}</button>
            ))}
          </div>
          <button onClick={handleHint} disabled={!!result} className="rounded-full bg-amber-500 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">Need a hint?</button>
        </div>
        {hintText && <div className="mt-4"><HintPanel hints={[`${hintMeta.type || 'guided_hint'} level ${hintMeta.level || hintCount}: ${hintText}`, ...hintVariants]} /></div>}
      </div>

      {result ? (
        <div className={clsx('rounded-3xl p-6 border-2', result.correct ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200')}>
          <h3 className={clsx('text-xl font-black mb-2', result.correct ? 'text-emerald-700' : 'text-rose-700')}>{result.correct ? 'Correct' : result.score >= 0.45 ? 'Partially correct' : 'Not quite right'}</h3>
          <p className="font-semibold">Score: {Math.round(result.score * 100)}%</p>
          <p className="mt-2">{result.feedback}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <FeedbackInfo label="Your answer" value={String(answerPayload(normalizedTask, selectedOpt, textAnswer, sortItems, blankAnswers, pairAnswers))} />
            <FeedbackInfo label={isMultipleChoice || isOutputPrediction || isFillBlank ? 'Expected answer' : 'Expected idea'} value={formatExpectedAnswer(result, question, normalizedTask)} />
            <FeedbackInfo label="Why" value={clipLearnerText(cleanLearnerText(String(result.explanation || (result.correct ? 'Your answer matches the expected concept.' : 'Review the expected idea and try a similar question.'))), 300, 3)} />
            <FeedbackInfo label="Next step" value={clipLearnerText(String(result.recommended_next_activity?.label || (result.correct ? 'Continue to the next activity' : 'Review the definition, then try one similar question.')), 140, 1)} />
            {!result.correct && <FeedbackInfo label="Focus area" value={formatFocusArea(result.mistake_type || result.weakest_skill || 'needs_review')} />}
            {(result.next_teaching_view || result.recommended_teaching_view) && <FeedbackInfo label="Teaching view" value={String(result.next_teaching_view || result.recommended_teaching_view).replace(/_/g, ' ')} />}
          </div>
          <div className="mt-3"><ReadAloudButton text={`${result.feedback}. ${result.mascot_script || ''}`} /></div>
          <div className="mt-6 flex flex-wrap justify-end gap-3">
            {revisionRouteNeeded(result) && (
              <button
                type="button"
                onClick={() => navigate('/revision')}
                className="px-6 py-3 rounded-full font-bold text-sky-700 bg-white border border-sky-200 dark:bg-slate-950 dark:text-sky-300 dark:border-sky-900/50"
              >
                {revisionButtonLabel(result)}
              </button>
            )}
            <button onClick={() => onComplete(result.score)} className="px-8 py-3 rounded-full font-bold text-white bg-sky-600 flex items-center gap-2">Continue <ArrowRight className="w-5 h-5" /></button>
          </div>
        </div>
      ) : !isCodeTask && (
        <div className="flex justify-end px-2"><button onClick={() => handleSubmit(answerPayload(normalizedTask, selectedOpt, textAnswer, sortItems, blankAnswers, pairAnswers))} disabled={submitting || !canSubmit(normalizedTask, selectedOpt, textAnswer, sortItems, blankAnswers, pairAnswers)} className="px-10 py-4 rounded-full font-bold text-white bg-sky-600 disabled:opacity-50 flex items-center gap-2">{submitting ? 'Checking...' : 'Check Answer'} <CheckCircle2 className="w-5 h-5" /></button></div>
      )}
    </div>
  );
};

export default AssessmentRenderer;

function move(items: string[], from: number, to: number) {
  const copy = [...items];
  const [item] = copy.splice(from, 1);
  copy.splice(to, 0, item);
  return copy;
}

function normalizeSortItems(items: unknown[]): string[] {
  return items.map((item) => {
    if (typeof item === 'string') return item;
    if (item && typeof item === 'object') {
      const record = item as Record<string, unknown>;
      return String(record.text || record.label || record.id || JSON.stringify(record));
    }
    return String(item);
  }).filter(Boolean);
}

function canSubmit(task: string, selectedOpt: string | null, textAnswer: string, sortItems: string[], blankAnswers: Record<string, string>, pairAnswers: Record<string, string>) {
  if (task === 'mcq' || task === 'multiple_choice' || task === 'true_false' || task === 'true_or_false') return !!selectedOpt;
  if (task === 'drag_order' || task === 'puzzle') return sortItems.length > 0;
  if (task === 'fill_blank' || task === 'fill_in_the_blank') return Object.values(blankAnswers).some(Boolean);
  if (task === 'match_pairs') return Object.values(pairAnswers).some(Boolean);
  return !!textAnswer.trim();
}

function answerPayload(task: string, selectedOpt: string | null, textAnswer: string, sortItems: string[], blankAnswers: Record<string, string>, pairAnswers: Record<string, string>) {
  if (task === 'drag_order' || task === 'puzzle') return sortItems;
  if (task === 'fill_blank' || task === 'fill_in_the_blank') {
    const answers = Object.values(blankAnswers).filter(Boolean);
    return answers.length === 1 ? answers[0] : blankAnswers;
  }
  if (task === 'match_pairs') return pairAnswers;
  return selectedOpt || textAnswer;
}

function renderCard(task: string, question: AssessmentQuestion) {
  if (task === 'mcq' || task === 'multiple_choice') return <MCQQuestionCard question={question} />;
  if (task === 'debug' || task === 'debug_task') return <DebugQuestionCard question={question} />;
  if (task === 'debug_challenge') return <DebugQuestionCard question={question} />;
  if (task === 'output_prediction' || task === 'output_prediction_challenge') return <OutputPredictionCard question={question} />;
  if (task === 'syntax' || task === 'syntax_completion') return <SyntaxCompletionCard question={question} />;
  if (task === 'coding_question' || task === 'coding_prompt' || task === 'code_reasoning_task') return <CodeWritingCard question={question} />;
  if (task === 'code_tracing' || task === 'output_reasoning') return <OutputPredictionCard question={question} />;
  if (task === 'drag_order') return <DragOrderQuestionCard question={question} />;
  if (task === 'match_pairs') return <MatchPairsQuestionCard question={question} />;
  if (task === 'fill_blank' || task === 'fill_in_the_blank') return <FillBlankQuestionCard question={question} />;
  if (task === 'true_false' || task === 'true_or_false') return <MCQQuestionCard question={question} />;
  if (task === 'puzzle' || task === 'gamified_task') return <DragOrderQuestionCard question={question} />;
  if (task === 'challenge' || task === 'challenge_question' || task === 'multi_step_challenge') return <ChallengeQuestionCard question={question} />;
  if (task === 'transfer' || task === 'transfer_question' || task === 'transfer_task' || task === 'real_world_application_question') return <TransferQuestionCard question={question} />;
  return <ShortExplanationCard question={question} />;
}

function canonicalTaskType(question: AssessmentQuestion) {
  const component = String(question.frontendComponent || question.frontend_component || '').toLowerCase();
  const raw = String(question.taskType || question.questionType || '').toLowerCase();
  const questionType = String(question.questionType || '').toLowerCase();
  if (component === 'mcqquestioncard' || raw === 'mcq' || questionType === 'mcq' || raw === 'multiple_choice') return 'mcq';
  if (component === 'debugquestioncard' || raw === 'debug_task' || raw === 'debug' || raw === 'debug_challenge') return raw === 'debug_challenge' ? 'debug_challenge' : 'debug_task';
  if (component === 'outputpredictioncard' || raw === 'output_prediction' || raw === 'output_prediction_challenge') return raw || 'output_prediction';
  if (component === 'syntaxcompletioncard' || raw === 'syntax_completion' || raw === 'syntax') return 'syntax_completion';
  if (component === 'codewritingcard' || raw === 'coding_question' || raw === 'coding_prompt' || raw === 'code_reasoning_task' || raw === 'code_writing') return raw === 'code_writing' ? 'coding_prompt' : raw;
  if (component === 'fillblankcard' || raw === 'fill_blank' || raw === 'fill_in_the_blank') return 'fill_in_the_blank';
  if (component === 'puzzlequestioncard' || raw === 'puzzle' || raw === 'drag_order' || raw === 'arrange_steps') return raw === 'drag_order' || raw === 'arrange_steps' ? 'drag_order' : 'puzzle';
  if (component === 'matchpairscard' || raw === 'match_pairs') return 'match_pairs';
  if (component === 'transferquestioncard' || raw === 'transfer' || raw === 'transfer_question' || raw === 'transfer_task' || raw === 'real_world_application_question') return raw || 'transfer_question';
  if (component === 'challengequestioncard' || raw === 'challenge' || raw === 'challenge_question' || raw === 'multi_step_challenge') return raw || 'challenge_question';
  if (raw === 'true_false' || raw === 'true_or_false') return 'true_or_false';
  return raw || questionType || 'practice_question';
}

function formatTime(seconds: number) {
  const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
  const secs = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${mins}:${secs}`;
}

function languageForSubject(subject: string) {
  const normalized = subject.toLowerCase();
  if (normalized.includes('sql') || normalized.includes('database')) return 'sql';
  if (normalized.includes('git')) return 'shell';
  if (normalized.includes('html') || normalized.includes('web')) return 'html';
  return 'python';
}

function placeholderForTask(task: string) {
  if (task.includes('real_world') || task.includes('transfer')) return 'Type your answer in 2-3 sentences...';
  if (task.includes('challenge')) return 'Type your solution and short reasoning...';
  if (task.includes('explanation')) return 'Type your explanation...';
  return 'Type your answer...';
}

function FeedbackInfo({ label, value }: { label: string; value: string }) {
  const [expanded, setExpanded] = useState(false);
  const clean = cleanLearnerText(String(value || ''));
  const isLong = clean.length > 600;
  const display = isLong && !expanded ? `${clean.slice(0, 300).trim()}...` : clean;
  return (
    <div className="rounded-2xl border border-white/70 bg-white/80 p-3 text-sm dark:border-slate-800 dark:bg-slate-950/70">
      <p className="text-xs font-black uppercase text-slate-500">{label}</p>
      <p className="mt-1 whitespace-pre-wrap font-semibold text-slate-800 dark:text-slate-100">{display}</p>
      {isLong && <button onClick={() => setExpanded((value) => !value)} className="mt-2 text-xs font-bold text-sky-700 dark:text-sky-300">{expanded ? 'Show less' : 'Show full explanation'}</button>}
    </div>
  );
}

function shortOption(option: string) {
  const clean = option.replace(/\s+/g, ' ').trim();
  return clean.length > 140 ? `${clean.slice(0, 139).trim()}...` : clean;
}

function formatExpectedAnswer(result: CodeSubmitResult, question: AssessmentQuestion, task: string) {
  if (task === 'mcq' || task === 'multiple_choice' || task === 'true_false' || task === 'true_or_false') {
    return clipLearnerText(String(result.correct_answer || question.correctAnswer || question.options?.[0] || 'Review the correct option.'), 300, 2);
  }
  const value = result.correct_answer
    || question.correctAnswer
    || question.expectedOutput
    || question.expected_idea
    || question.expected_answer
    || 'Use the expected idea from the question prompt.';
  if (typeof value === 'object' && value) {
    const record = value as Record<string, unknown>;
    const parts = Object.values(record).flatMap((item) => Array.isArray(item) ? item : [item]).map(String).filter(Boolean).slice(0, 4);
    return clipLearnerText(parts.map((part) => `- ${part}`).join('\n'), 600, 4);
  }
  const limit = task.includes('output') || task.includes('syntax') ? 300 : task.includes('debug') || task.includes('coding') ? 600 : 600;
  return clipLearnerText(String(value), limit, task.includes('output') ? 1 : 4);
}

function cleanLearnerText(value: string) {
  const labels: Record<string, string> = {
    weak_answer: 'answer too short or unclear',
    wrong_option: 'incorrect option',
    wrong_output: 'output tracing issue',
    syntax_misunderstanding: 'syntax rule issue',
    debug_error: 'debugging issue',
    exact_match: 'expected answer',
    fallback_cumulative: 'saved progress',
    none: '',
  };
  let text = String(value || '').replace(/\s+/g, ' ').trim();
  Object.entries(labels).forEach(([raw, friendly]) => {
    text = text.replace(new RegExp(`\\b${raw}\\b`, 'gi'), friendly);
  });
  return text.replace(/\s+/g, ' ').trim() || 'Review the expected idea and try again.';
}

function clipLearnerText(value: string, maxChars = 300, maxSentences = 3) {
  const text = cleanLearnerText(value);
  const bullets = text.split('\n').filter((line) => line.trim().startsWith('-')).slice(0, 4);
  if (bullets.length) {
    const compact = bullets.join('\n');
    return compact.length > maxChars ? `${compact.slice(0, maxChars - 3).trim()}...` : compact;
  }
  const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean).slice(0, maxSentences).join(' ');
  const compact = sentences || text;
  return compact.length > maxChars ? `${compact.slice(0, maxChars - 3).trim()}...` : compact;
}

function formatFocusArea(value: string) {
  return cleanLearnerText(value.replace(/_/g, ' '));
}

function normalizeFeedbackResult(result: CodeSubmitResult) {
  const correct = result.correct || result.score >= 0.8;
  if (!correct) return result;
  return {
    ...result,
    correct: true,
    feedback: result.feedback || 'Correct. You understood this concept.',
    mascot_script: 'Great answer. You understood this concept correctly. Let’s move to the next level.',
    recommended_next_activity: result.recommended_next_activity || nextForDifficulty(result.difficulty),
  };
}

function revisionRouteNeeded(result: CodeSubmitResult) {
  const activity = String(result.recommended_next_activity?.type || result.next_recommended_action || '').toLowerCase();
  return result.score < 0.8 || activity.includes('revision') || activity.includes('review') || activity.includes('practice') || activity.includes('reteach');
}

function revisionButtonLabel(result: CodeSubmitResult) {
  const activity = String(result.recommended_next_activity?.type || result.next_recommended_action || '').toLowerCase();
  if (activity.includes('practice') || result.score >= 0.45) return 'Practice weak area';
  return 'Review this concept';
}

function nextForDifficulty(difficulty?: string) {
  if (difficulty === 'easy') return { type: 'assessment' as const, label: 'Move to medium', reason: 'Correct easy answer unlocks medium practice.' };
  if (difficulty === 'medium') return { type: 'assessment' as const, label: 'Move to hard', reason: 'Correct medium answer unlocks hard practice.' };
  return { type: 'next_concept' as const, label: 'Next concept', reason: 'Correct hard answer completes this concept level.' };
}
