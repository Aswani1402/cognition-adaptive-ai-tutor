import { BookOpen, Code, CornerDownRight, HelpCircle, Lightbulb, PlayCircle, X, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import { AssessmentQuestion, CodeSubmitResult, Flashcard, GuidedActivityType, MindMap, RewardState, TeachingContent } from '../../lib/types';
import SelectedTeachingViewRenderer from '../teaching/SelectedTeachingViewRenderer';
import AssessmentRenderer from '../assessment/AssessmentRenderer';
import FlashcardDeck from '../visual/FlashcardDeck';
import MindMapView from '../visual/MindMapView';
import SessionCelebration from './SessionCelebration';
import DoubtPanel from '../doubt/DoubtPanel';

type TeachingView = string;

const teachingActions: { label: string; view?: TeachingView; icon: typeof Lightbulb; iconClass: string; kind?: 'doubt' }[] = [
  { label: 'Explanation', view: 'explanation', icon: Lightbulb, iconClass: 'text-amber-500' },
  { label: 'Definition', view: 'definition_view', icon: BookOpen, iconClass: 'text-indigo-500' },
  { label: 'Example', view: 'simple_example_view', icon: Lightbulb, iconClass: 'text-amber-500' },
  { label: 'Give analogy', view: 'analogy_view', icon: PlayCircle, iconClass: 'text-emerald-500' },
  { label: 'Show code example', view: 'code_view', icon: Code, iconClass: 'text-sky-500' },
  { label: 'Step-by-step', view: 'step_by_step_view', icon: BookOpen, iconClass: 'text-violet-500' },
  { label: 'Common mistake', view: 'misconception_view', icon: CornerDownRight, iconClass: 'text-rose-500' },
  { label: 'Debug', view: 'debug_view', icon: Code, iconClass: 'text-rose-500' },
  { label: 'Predict output', view: 'output_prediction_view', icon: PlayCircle, iconClass: 'text-cyan-500' },
  { label: 'Transfer', view: 'transfer_view', icon: CornerDownRight, iconClass: 'text-emerald-500' },
  { label: 'Challenge', view: 'challenge_view', icon: Sparkles, iconClass: 'text-fuchsia-500' },
  { label: 'Revision', view: 'revision_summary_view', icon: BookOpen, iconClass: 'text-slate-500' },
  { label: 'Compare', view: 'comparison_view', icon: CornerDownRight, iconClass: 'text-orange-500' },
  { label: 'Real world', view: 'real_world_connection_view', icon: PlayCircle, iconClass: 'text-teal-500' },
  { label: 'Ask doubt', icon: HelpCircle, iconClass: 'text-indigo-500', kind: 'doubt' },
];

export default function ActivityRenderer({
  activity,
  lesson,
  questions,
  questionIndex,
  feedback,
  flashcards,
  mindmap,
  reward,
  busyView,
  doubtOpen,
  setDoubtOpen,
  onTeachingView,
  onAssessmentResult,
  onQuestionComplete,
  onFlashcardsComplete,
  onTrySimilarQuestion,
  onReviewRecommendedView,
  onContinue,
}: {
  activity: GuidedActivityType;
  lesson: TeachingContent | null;
  questions: AssessmentQuestion[];
  questionIndex: number;
  feedback: CodeSubmitResult | null;
  flashcards: Flashcard[];
  mindmap: MindMap | null;
  reward: RewardState | null;
  busyView?: string | null;
  doubtOpen: boolean;
  setDoubtOpen: (open: boolean) => void;
  onTeachingView: (view: TeachingView) => void;
  onAssessmentResult: (result: CodeSubmitResult) => void;
  onQuestionComplete: () => void;
  onFlashcardsComplete: () => void;
  onTrySimilarQuestion?: () => void;
  onReviewRecommendedView?: (view: string) => void;
  onContinue?: () => void;
}) {
  if ((activity === 'teaching' || activity === 'misconception_review' || activity === 'revision_summary') && lesson) {
    return (
      <div className="space-y-6">
        <SelectedTeachingViewRenderer lesson={lesson} />
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7">
          {teachingActions.map((action) => {
            const Icon = action.icon;
            const active = action.view && (lesson.selectedView === action.view || (lesson.selectedView === 'explanation_view' && action.view === 'explanation'));
            return (
              <button
                key={action.label}
                onClick={() => action.kind === 'doubt' ? setDoubtOpen(true) : action.view && onTeachingView(action.view)}
                disabled={Boolean(busyView)}
                className={clsx(
                  'flex min-h-20 flex-col items-center justify-center gap-2 rounded-xl border p-3 text-center transition disabled:cursor-wait disabled:opacity-60',
                  active
                    ? 'border-indigo-300 bg-indigo-50 text-indigo-800 dark:border-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-200'
                    : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-300 dark:hover:bg-slate-900'
                )}
              >
                <Icon className={clsx('h-5 w-5', action.iconClass)} />
                <span className="text-sm font-bold">{busyView === action.view ? 'Loading...' : action.label}</span>
              </button>
            );
          })}
        </div>
        {doubtOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            <button aria-label="Close doubt panel" className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setDoubtOpen(false)} />
            <div className="relative flex h-full w-full max-w-md flex-col bg-white shadow-2xl dark:bg-slate-950">
              <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
                <h2 className="flex items-center gap-2 text-lg font-bold"><Sparkles className="h-5 w-5 text-indigo-500" /> Ask a Doubt</h2>
                <button onClick={() => setDoubtOpen(false)} className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800"><X className="h-5 w-5" /></button>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto">
                <DoubtPanel conceptName={lesson.conceptName} conceptId={lesson.conceptId} currentTeachingView={lesson.selectedView} />
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (activity === 'assessment' || activity === 'mini_check' || activity === 'code_practice') {
    const question = questions[questionIndex];
    if (!question) return <EmptyPanel title="No question available" body="Cogni could not load a check, so you can continue from the next action." />;
    return (
      <AssessmentRenderer
        key={question.questionId}
        question={question}
        questionIndex={questionIndex}
        questionTotal={Math.min(questions.length, 10)}
        onResult={onAssessmentResult}
        onComplete={onQuestionComplete}
      />
    );
  }

  if (activity === 'feedback' && feedback) {
    return (
      <section className={clsx('rounded-3xl border-2 p-6', feedback.score >= 0.8 ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/40 dark:bg-emerald-900/20' : feedback.score >= 0.45 ? 'border-amber-200 bg-amber-50 dark:border-amber-900/40 dark:bg-amber-900/20' : 'border-rose-200 bg-rose-50 dark:border-rose-900/40 dark:bg-rose-900/20')}>
        <p className="text-xs font-black uppercase tracking-wider text-slate-500">Feedback</p>
        <h3 className="mt-2 text-2xl font-black text-slate-900 dark:text-white">Score: {Math.round(feedback.score * 100)}%</h3>
        <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-200">{shortInfo(feedback.feedback, 360)}</p>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Info label="Result" value={feedback.correct ? 'Correct' : feedback.score >= 0.45 ? 'Partial' : 'Needs review'} />
          <Info label="Learner answer" value={String(feedback.learner_answer || 'Recorded with submission')} />
          <Info label="Correct answer" value={String(feedback.correct_answer || 'Shown in the question feedback')} />
          <Info label="Why" value={String(feedback.explanation || feedback.recommended_next_activity?.reason || 'The tutor evaluated the answer and selected the next step.')} />
          {!feedback.correct && <Info label="Focus area" value={feedback.weakest_skill || feedback.mistake_type || feedback.taskType || 'current skill'} />}
          <Info label="Next recommended action" value={feedback.recommended_next_activity?.label || feedback.next_recommended_action || feedback.nextAction || 'Continue'} />
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <button onClick={onTrySimilarQuestion} className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200">
            Try Similar Question
          </button>
          <button
            onClick={() => onReviewRecommendedView?.(feedback.recommended_teaching_view || feedback.recommended_view || 'misconception_view')}
            className="rounded-full border border-indigo-200 bg-indigo-50 px-4 py-2 text-sm font-bold text-indigo-700 hover:bg-indigo-100 dark:border-indigo-900/40 dark:bg-indigo-900/20 dark:text-indigo-200"
          >
            Review with Recommended Teaching View
          </button>
          <button onClick={onContinue} className="rounded-full bg-sky-600 px-5 py-2 text-sm font-bold text-white hover:bg-sky-700">
            Continue
          </button>
        </div>
      </section>
    );
  }

  if (activity === 'flashcard_revision') {
    return <FlashcardDeck cards={flashcards} onComplete={onFlashcardsComplete} />;
  }

  if (activity === 'mindmap_revision' && mindmap) {
    return <MindMapView mindmap={mindmap} />;
  }

  if (activity === 'reward') {
    return <SessionCelebration reward={reward} message={lesson ? `Wow! You completed ${lesson.conceptName}. The next step is unlocked.` : 'Great job!'} />;
  }

  if (activity === 'complete') {
    const total = Math.min(questions.length, 10);
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-950">
        <p className="text-xs font-black uppercase tracking-wider text-slate-500">Assessment summary</p>
        <h3 className="mt-2 text-2xl font-black text-slate-900 dark:text-white">{lesson?.conceptName || 'Current concept'}</h3>
        <div className="mt-5 grid gap-3 sm:grid-cols-4">
          <Info label="Total" value={String(total)} />
          <Info label="Latest result" value={feedback?.correct ? 'Correct' : feedback && feedback.score >= 0.45 ? 'Partial' : 'Needs review'} />
          <Info label="Latest score" value={feedback ? `${Math.round(feedback.score * 100)}%` : '0%'} />
          <Info label="Weakest skill" value={feedback?.weakest_skill || feedback?.mistake_type || 'current skill'} />
        </div>
        <p className="mt-5 rounded-2xl border border-sky-100 bg-sky-50 p-4 text-sm font-semibold text-sky-800 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-200">
          Next step: {feedback?.recommended_next_activity?.label || feedback?.next_recommended_action || 'Continue with the guided recommendation.'}
        </p>
      </section>
    );
  }

  return <EmptyPanel title="Guided session ready" body="Cogni is preparing your next activity." />;
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/70">
      <p className="text-xs font-black uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-slate-900 dark:text-white">{shortInfo(value, 220)}</p>
    </div>
  );
}

function shortInfo(value: string, max = 220) {
  const labels: Record<string, string> = {
    wrong_option: 'incorrect option',
    weak_answer: 'answer too short or unclear',
    wrong_output: 'output tracing issue',
    syntax_misunderstanding: 'syntax rule issue',
    debug_error: 'debugging issue',
    needs_review: 'needs review',
    none: '',
  };
  let clean = String(value || '').replace(/\s+/g, ' ').trim();
  Object.entries(labels).forEach(([raw, friendly]) => {
    clean = clean.replace(new RegExp(`\\b${raw}\\b`, 'gi'), friendly);
  });
  return clean.length > max ? `${clean.slice(0, max - 3).trim()}...` : clean;
}

function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-8 text-center dark:border-slate-800 dark:bg-slate-950">
      <h3 className="text-xl font-black text-slate-900 dark:text-white">{title}</h3>
      <p className="mt-2 text-sm text-slate-500">{body}</p>
    </div>
  );
}
