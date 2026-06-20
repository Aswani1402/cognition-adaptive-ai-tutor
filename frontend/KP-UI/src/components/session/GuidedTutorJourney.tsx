import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AssessmentQuestion, CodeSubmitResult, Flashcard, GuidedActivityType, MindMap, NextRecommendedActivity, RewardState, TeachingContent } from '../../lib/types';
import { getAdaptiveSession, getAssessment, getFlashcards, getLesson, getMindmap, getRetentionPrediction, getRewardState, getSimilarQuestion } from '../../lib/api';
import ActivityRenderer from './ActivityRenderer';
import CogniGuideCard from '../mascot/CogniGuideCard';
import { getCogniMessage } from '../mascot/useCogniGuide';
import NextActionCard from './NextActionCard';
import SessionProgressTimeline from './SessionProgressTimeline';
import DifficultyProgressTracker from './DifficultyProgressTracker';
import LoadingSkeleton from '../common/LoadingSkeleton';
import { Difficulty, DifficultyProgress } from '../../lib/types';
import { useLearnerSession } from '../../context/LearnerSessionContext';
import { logFrontendEvent } from '../../lib/eventLog';

export default function GuidedTutorJourney({ conceptId }: { conceptId: string }) {
  const navigate = useNavigate();
  const sessionContext = useLearnerSession();
  const learnerId = sessionContext.getCurrentLearnerId();
  const subject = sessionContext.active_subject;
  const [activity, setActivity] = useState<GuidedActivityType>('teaching');
  const [lesson, setLesson] = useState<TeachingContent | null>(null);
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [feedback, setFeedback] = useState<CodeSubmitResult | null>(null);
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [mindmap, setMindmap] = useState<MindMap | null>(null);
  const [reward, setReward] = useState<RewardState | null>(null);
  const [guideMessage, setGuideMessage] = useState("Let's learn this concept first.");
  const [nextAction, setNextAction] = useState<NextRecommendedActivity>({ type: 'assessment', label: 'Try quick check', reason: 'Check understanding after teaching' });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyView, setBusyView] = useState<string | null>(null);
  const [doubtOpen, setDoubtOpen] = useState(false);
  const [difficulty, setDifficulty] = useState<Difficulty>('easy');
  const [difficultyProgress, setDifficultyProgress] = useState<DifficultyProgress>({ easy: 'current', medium: 'locked', hard: 'locked' });
  const [whyOpen, setWhyOpen] = useState(false);
  const [correctCount, setCorrectCount] = useState(0);
  const [attemptedCount, setAttemptedCount] = useState(0);
  const [summaryNextAction, setSummaryNextAction] = useState<NextRecommendedActivity | null>(null);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    let alive = true;
    async function load() {
      setLoading(true);
      setLoadError('');
      logFrontendEvent({ action: 'lesson_opened', module: 'guided_session', status: 'started', summary: conceptId });
      let session;
      let retention;
      let firstLesson;
      try {
        [session, retention, firstLesson] = await Promise.all([
          getAdaptiveSession(learnerId),
          getRetentionPrediction(learnerId),
          getLesson(conceptId, { learnerId, difficulty, subject }),
        ]);
      } catch (error) {
        if (!alive) return;
        const fallbackLesson = await getLesson(conceptId, { learnerId, difficulty, subject });
        setLesson(fallbackLesson);
        sessionContext.updateCurrentConcept(fallbackLesson.conceptId, fallbackLesson.conceptName);
        setGuideMessage('This content is being prepared. Showing saved learning content instead.');
        setNextAction({ type: 'assessment', label: 'Try quick check', reason: 'Check understanding after the saved lesson content' });
        setLoadError('');
        setLoading(false);
        return;
      }
      if (!alive) return;
      setLesson(firstLesson);
      logFrontendEvent({ action: 'lesson_opened', module: 'guided_session', status: 'success', summary: firstLesson.conceptName });
      sessionContext.updateCurrentConcept(firstLesson.conceptId, firstLesson.conceptName);
      setDifficulty(firstLesson.difficulty);
      setDifficultyProgress(firstLesson.difficultyProgress || { easy: firstLesson.difficulty === 'easy' ? 'current' : 'passed', medium: firstLesson.difficulty === 'medium' ? 'current' : 'locked', hard: firstLesson.difficulty === 'hard' ? 'current' : 'locked' });
      const highRetentionRisk = retention.riskLevel === 'high' || retention.reviewDueInDays <= 0;
      if (highRetentionRisk || session.current_activity?.type === 'returning_revision') {
        setActivity('returning_revision');
        setGuideMessage(session.guide_message || "Welcome back! It's been a while, so let's revise before continuing.");
        setNextAction({ type: 'flashcard_revision', label: 'Start revision', reason: 'Retention risk suggests a short review first' });
      } else {
        setActivity('teaching');
        setGuideMessage(firstLesson.backendConnected === false ? 'This content is being prepared. Showing saved learning content instead.' : "Let's learn this concept first.");
        setNextAction(firstLesson.nextActivity === 'quiz'
          ? { type: 'assessment', label: 'Try quick check', reason: 'Check understanding after teaching' }
          : { type: 'assessment', label: 'Continue practice', reason: 'Backend recommends checking this concept' });
      }
      setLoading(false);
    }
    load();
    return () => { alive = false; };
  }, [conceptId, learnerId, subject]);

  const mode = lesson?.backendConnected === false || lesson?.mockFallbackUsed ? 'unavailable' : 'backend';

  const stepLabel = useMemo(() => {
    if (activity === 'returning_revision') return 'Returning revision';
    return activity.replaceAll('_', ' ');
  }, [activity]);

  const handleTeachingView = async (view: string) => {
    setBusyView(view);
    const next = await getLesson(conceptId, { learnerId, view, difficulty, subject });
    setLesson(next);
    setActivity(view === 'misconception_view' ? 'misconception_review' : 'teaching');
    setGuideMessage(view === 'misconception_view' ? "Let's look at this in a different way." : "Here's another way to learn it.");
    setBusyView(null);
  };

  const loadAssessment = async () => {
    setBusy(true);
    const loaded = await getAssessment(learnerId, conceptId, { difficulty, subject });
    logFrontendEvent({ action: 'question_loaded', module: 'assessment', status: 'success', summary: `${loaded.length} questions` });
    setQuestions(selectBalancedQuestions(loaded, 10));
    setQuestionIndex(0);
    setCorrectCount(0);
    setAttemptedCount(0);
    setSummaryNextAction(null);
    setActivity('assessment');
    setGuideMessage('Now let’s do a quick check.');
    setNextAction({ type: 'assessment', label: 'Submit answer', reason: 'Cogni will evaluate and choose the next activity' });
    setBusy(false);
  };

  const loadFlashcards = async () => {
    setBusy(true);
    const cards = await getFlashcards(learnerId, conceptId, subject);
    setFlashcards(cards);
    setActivity('flashcard_revision');
    setGuideMessage('Almost there. I’ll show a quick revision before the next question.');
    setNextAction({ type: 'assessment', label: 'Continue check', reason: 'Use revision memory before trying again' });
    setBusy(false);
  };

  const loadMindmap = async () => {
    setBusy(true);
    const map = await getMindmap(conceptId, subject);
    setMindmap(map);
    setActivity('mindmap_revision');
    setGuideMessage('Let’s connect the idea with a quick overview.');
    setNextAction({ type: 'assessment', label: 'Try again', reason: 'The overview should help with the next check' });
    setBusy(false);
  };

  const loadReward = async () => {
    setBusy(true);
    const rewardState = await getRewardState(learnerId);
    setReward(rewardState);
    setActivity('reward');
    setGuideMessage('Yahoo! You scored well. Let’s unlock the next step.');
    setNextAction({ type: 'next_concept', label: 'Continue journey', reason: 'Strong score means you can move forward' });
    setBusy(false);
  };

  const handleAssessmentResult = (result: CodeSubmitResult) => {
    setFeedback(result);
    if (result.score >= 0.8) setCorrectCount((count) => count + 1);
    setAttemptedCount((count) => count + 1);
    setActivity('feedback');
    if (result.difficulty) setDifficulty(result.difficulty);
    if (result.difficulty_progress) setDifficultyProgress(result.difficulty_progress);
    const recommended = result.recommended_next_activity;
    const hasMoreQuestions = questionIndex < Math.min(questions.length, 10) - 1;
    if (hasMoreQuestions) {
      setSummaryNextAction(recommended || null);
      setNextAction({ type: 'assessment', label: 'Continue to next question', reason: `Question ${questionIndex + 1} is complete. Continue the mixed assessment set.` });
      setGuideMessage(result.guide_message || 'Keep going. The next question checks a different skill.');
      return;
    }
    if (questions.length > 1) {
      setSummaryNextAction(recommended || { type: 'assessment', label: 'Continue practice', reason: 'Assessment set finished; continue with the recommended activity.' });
      setNextAction({ type: 'complete', label: 'Show assessment summary', reason: 'The full mixed question set is complete.' });
      setGuideMessage('Assessment set complete. Review your summary before the next activity.');
      return;
    }
    if (recommended) {
      setNextAction(recommended);
      setGuideMessage(result.guide_message || recommended.reason);
      return;
    }
    if (result.score >= 0.8) {
      setGuideMessage('Great job! You understood this.');
      setNextAction({ type: 'reward', label: 'Show reward', reason: 'High score updates mastery and unlock progress' });
    } else if (result.score >= 0.45) {
      setGuideMessage('Almost there. I’ll show a quick revision before the next question.');
      setNextAction({ type: 'flashcard_revision', label: 'Review flashcards', reason: 'Partial score benefits from recall practice' });
    } else if (result.mistake_type === 'syntax_misunderstanding') {
      setGuideMessage('Let’s fix the syntax step by step.');
      setNextAction({ type: 'misconception_review', label: 'Review syntax', reason: 'Syntax mistake detected' });
    } else if (result.weakest_skill === 'output_prediction' || result.mistake_type === 'wrong_output') {
      setGuideMessage('Let’s trace the output line by line.');
      setNextAction({ type: 'mindmap_revision', label: 'Open overview', reason: 'Output prediction needs concept structure' });
    } else {
      setGuideMessage('No worries. This mistake tells us what to practice next.');
      setNextAction({ type: 'misconception_review', label: 'Review another way', reason: 'Weak score needs reteaching before another check' });
    }
  };

  const handleQuestionComplete = () => {
    if (feedback?.score && feedback.score >= 0.8 && questionIndex < Math.min(questions.length, 10) - 1) {
      setQuestionIndex((curr) => curr + 1);
      setFeedback(null);
      setActivity('assessment');
      setGuideMessage('Great job! You understood this. Let’s continue.');
    }
  };

  const handleTrySimilarQuestion = async () => {
    setBusy(true);
    const current = questions[questionIndex];
    const similar = await getSimilarQuestion({
      learner_id: learnerId,
      concept_id: conceptId,
      concept_name: lesson?.conceptName,
      subject,
      difficulty,
      question_id: current?.questionId,
      question_type: current?.questionType || current?.taskType,
      exclude_question_ids: questions.map((q) => q.questionId),
    });
    setFeedback(null);
    if (similar) {
      setQuestions((curr) => [...curr, similar]);
      setQuestionIndex(questions.length);
    }
    setActivity('assessment');
    setGuideMessage(similar ? 'Try this similar question.' : 'I could not load a similar question, so try the current check again.');
    setBusy(false);
  };

  const handleReviewRecommendedView = async (view: string) => {
    await handleTeachingView(view || feedback?.recommended_teaching_view || feedback?.recommended_view || 'misconception_view');
    setFeedback(null);
  };

  const runNextAction = async () => {
    if (nextAction.type === 'next_difficulty') {
      const nextDifficulty = feedback?.next_difficulty || (difficulty === 'easy' ? 'medium' : difficulty === 'medium' ? 'hard' : 'hard');
      setDifficulty(nextDifficulty);
      localStorage.setItem('current_difficulty', nextDifficulty);
      setDifficultyProgress((curr) => ({
        easy: nextDifficulty === 'easy' ? 'current' : 'passed',
        medium: nextDifficulty === 'medium' ? 'current' : curr.medium === 'passed' ? 'passed' : 'locked',
        hard: nextDifficulty === 'hard' ? 'current' : 'locked',
      }));
      const nextLesson = await getLesson(conceptId, { learnerId, difficulty: nextDifficulty, subject });
      setLesson(nextLesson);
      setFeedback(null);
      setQuestions([]);
      setActivity('teaching');
      setGuideMessage(nextDifficulty === 'medium' ? 'Nice! You cleared the easy level. Let’s try medium.' : 'Great progress! Now let’s try the hard level.');
      setNextAction({ type: 'assessment', label: 'Try quick check', reason: `Check ${nextDifficulty} understanding before moving on` });
      return;
    }
    if (nextAction.type === 'complete') {
      setActivity('complete');
      setNextAction(summaryNextAction || { type: 'assessment', label: 'Continue practice', reason: 'Continue with the backend-recommended activity.' });
      setGuideMessage('Here is your assessment summary and next step.');
      return;
    }
    if (nextAction.type === 'assessment' || nextAction.type === 'mini_check' || nextAction.type === 'code_practice') {
      if (questions.length && activity !== 'teaching' && questionIndex < Math.min(questions.length, 10) - 1) {
        setQuestionIndex((curr) => curr + 1);
        setFeedback(null);
        setActivity('assessment');
        setGuideMessage('Now let’s do the next quick check.');
      } else {
        await loadAssessment();
      }
      return;
    }
    if (nextAction.type === 'flashcard_revision' || nextAction.type === 'returning_revision') {
      await loadFlashcards();
      return;
    }
    if (nextAction.type === 'mindmap_revision') {
      await loadMindmap();
      return;
    }
    if (nextAction.type === 'misconception_review') {
      await handleTeachingView('misconception_view');
      return;
    }
    if (nextAction.type === 'reward') {
      await loadReward();
      return;
    }
    if (nextAction.type === 'next_concept') {
      navigate('/subjects');
      return;
    }
    setActivity(nextAction.type);
  };

  if (loading || !lesson) {
    if (loadError) {
      return (
        <div className="mx-auto max-w-3xl rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-800 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-100">
          <p className="font-bold">This content is being prepared</p>
          <p className="mt-2 text-sm">Showing saved learning content instead.</p>
        </div>
      );
    }
    return <LoadingSkeleton title="Loading guided session" description="Cogni is preparing the next learning step." />;
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 pb-20">
      <CogniGuideCard {...getCogniMessage({
        page: 'lesson',
        activityType: activity,
        difficulty,
        score: feedback?.score,
        mistakeType: feedback?.mistake_type,
        weakestSkill: feedback?.weakest_skill,
        nextAction: nextAction.type,
        backendConnected: mode === 'backend',
        mockFallbackUsed: mode !== 'backend',
        backendMessage: guideMessage,
      })} />
      <SessionProgressTimeline current={activity} />
      <DifficultyProgressTracker conceptName={lesson.conceptName} currentDifficulty={difficulty} progress={difficultyProgress} />
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-300">Guided tutor session</p>
          <h1 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">{lesson.conceptName}</h1>
          <p className="mt-1 text-sm text-slate-500">Difficulty: {difficulty} · Selected view: {lesson.selectedView.replaceAll('_', ' ')}</p>
        </div>
        <span className="rounded-full border border-slate-200 px-3 py-1 text-xs font-bold text-slate-500 dark:border-slate-700">
          {mode === 'backend' ? 'Live backend' : 'Saved content'} · {mode === 'backend' ? import.meta.env.VITE_API_BASE_URL || 'Configured API' : 'fallback active'}
        </span>
      </header>
      <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <button onClick={() => setWhyOpen((open) => !open)} className="text-sm font-bold text-sky-700 dark:text-sky-300">
          Why this?
        </button>
        {whyOpen && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
            You are working on {lesson.conceptName} in {subject || 'your selected subject'} at {difficulty} level. {nextAction.reason}
          </p>
        )}
      </div>
      {subject && lesson.subject && lesson.subject.toLowerCase() !== subject.toLowerCase() && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-100">
          This section is being prepared for your selected subject. Continue with available content.
        </div>
      )}
      <ActivityRenderer
        activity={activity}
        lesson={lesson}
        questions={questions}
        questionIndex={questionIndex}
        feedback={feedback}
        flashcards={flashcards}
        mindmap={mindmap}
        reward={reward}
        busyView={busyView}
        doubtOpen={doubtOpen}
        setDoubtOpen={setDoubtOpen}
        onTeachingView={handleTeachingView}
        onAssessmentResult={handleAssessmentResult}
        onQuestionComplete={handleQuestionComplete}
        onFlashcardsComplete={() => {
          setGuideMessage('Nice revision! Now you’re ready to continue.');
          setNextAction({ type: 'assessment', label: 'Try quick check', reason: 'Revision is complete' });
          setActivity('feedback');
        }}
        onTrySimilarQuestion={handleTrySimilarQuestion}
        onReviewRecommendedView={handleReviewRecommendedView}
        onContinue={runNextAction}
      />
      {activity === 'feedback' && questions.length > 1 && (
        <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-200">
          Assessment set progress: {attemptedCount} of {Math.min(questions.length, 10)} answered, {correctCount} correct so far.
        </div>
      )}
      {activity !== 'assessment' && (
        <NextActionCard action={nextAction} onClick={runNextAction} loading={busy} />
      )}
      {(feedback?.memory_update || activity === 'feedback') && (
        <p className="rounded-2xl border border-cyan-200 bg-cyan-50 px-4 py-3 text-sm font-semibold text-cyan-800 dark:border-cyan-900/40 dark:bg-cyan-900/20 dark:text-cyan-200">
          {feedback?.memory_update?.mistake_logged ? 'Mistake saved for review.' : 'Saved to your notebook and revision memory.'}
        </p>
      )}
    </div>
  );
}

function selectBalancedQuestions(questions: AssessmentQuestion[], limit: number) {
  const preferred = [
    'mcq',
    'fill_in_the_blank',
    'fill_blank',
    'true_or_false',
    'true_false',
    'output_prediction',
    'debug_task',
    'syntax_completion',
    'coding_prompt',
    'coding_question',
    'code_reasoning_task',
    'explanation_check',
    'transfer_question',
    'challenge_question',
  ];
  const selected: AssessmentQuestion[] = [];
  const used = new Set<string>();
  for (const type of preferred) {
    const match = questions.find((q) => !used.has(q.questionId) && (q.questionType || q.taskType).toLowerCase() === type);
    if (match) {
      selected.push(match);
      used.add(match.questionId);
    }
    if (selected.length >= limit) return selected;
  }
  for (const question of questions) {
    if (!used.has(question.questionId)) selected.push(question);
    if (selected.length >= limit) break;
  }
  return selected;
}
