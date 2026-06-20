import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAssessment } from '../lib/api';
import { AssessmentQuestion } from '../lib/types';
import AssessmentRenderer from '../components/assessment/AssessmentRenderer';
import { X, Heart } from 'lucide-react';
import { useLearnerSession } from '../context/LearnerSessionContext';

export default function QuizPage() {
  const { conceptId } = useParams();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<AssessmentQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [filter, setFilter] = useState('All');
  const [loading, setLoading] = useState(true);
  const session = useLearnerSession();

  useEffect(() => {
    const activeConcept = conceptId || session.current_concept_id || 'P1';
    if (!activeConcept) {
      navigate('/subjects');
      return;
    }
    getAssessment(session.getCurrentLearnerId(), activeConcept, { subject: session.active_subject, difficulty: session.current_difficulty }).then((res) => {
      setQuestions(res);
      setLoading(false);
    });
  }, [conceptId, session.active_subject, session.current_concept_id, session.current_difficulty]);

  if (loading) return <div className="flex justify-center items-center h-[50vh]">Loading Practice...</div>;
  const filtered = filter === 'All' ? questions : questions.filter((q) => taskMatches(q, filter));
  const activeQuestions = filtered.length ? filtered : [fallbackQuestion(filter, conceptId || session.current_concept_id || 'P1', session.active_subject)];
  if (!questions.length) return <div>No practice found.</div>;

  const handleComplete = (_score: number) => {
    if (currentIndex < activeQuestions.length - 1) {
      setCurrentIndex(curr => curr + 1);
    } else {
      navigate('/progress'); // Temp navigate after complete
    }
  };

  const progressPct = ((currentIndex) / activeQuestions.length) * 100;

  return (
    <div className="max-w-3xl mx-auto w-full pt-4 pb-24">
      {/* Quiz Top Bar */}
      <div className="flex items-center gap-4 mb-8">
        <button onClick={() => navigate(-1)} className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
           <X className="w-6 h-6" />
        </button>
        <div className="flex-1 h-3 rounded-full bg-slate-200 dark:bg-slate-800 overflow-hidden relative">
           <div 
             className="absolute top-0 left-0 h-full bg-indigo-500 transition-all duration-500 ease-out rounded-full"
             style={{ width: `${progressPct}%` }}
           >
             <div className="w-full h-1/3 bg-white/20"></div>
           </div>
        </div>
        <div className="flex items-center gap-1.5 text-rose-500 font-bold">
           <Heart className="w-5 h-5 fill-current" /> 5
        </div>
      </div>
      <div className="mb-5 flex gap-2 overflow-x-auto">
        {['All', 'MCQ', 'Debug', 'Output', 'Fill Blank', 'True/False', 'Code', 'Transfer', 'Challenge', 'Puzzle'].map((item) => (
          <button key={item} onClick={() => { setFilter(item); setCurrentIndex(0); }} className={`shrink-0 rounded-full px-4 py-2 text-sm font-bold ${filter === item ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>{item}</button>
        ))}
      </div>

      <AssessmentRenderer 
        key={activeQuestions[currentIndex].questionId}
        question={activeQuestions[currentIndex]} 
        onComplete={handleComplete} 
      />
    </div>
  );
}

function taskMatches(question: AssessmentQuestion, filter: string) {
  const type = `${question.questionType || ''} ${question.taskType || ''} ${question.frontendComponent || ''}`.toLowerCase();
  const map: Record<string, string[]> = {
    MCQ: ['mcq', 'multiple_choice'],
    Debug: ['debug'],
    Output: ['output', 'prediction', 'tracing'],
    'Fill Blank': ['fill_blank', 'fill_in_the_blank', 'syntax_completion'],
    'True/False': ['true_false', 'true_or_false'],
    Code: ['code', 'coding'],
    Transfer: ['transfer'],
    Challenge: ['challenge'],
    Puzzle: ['puzzle', 'logic', 'gamified'],
  };
  return (map[filter] || [filter.toLowerCase()]).some((needle) => type.includes(needle));
}

function fallbackQuestion(filter: string, conceptId: string, subject: string): AssessmentQuestion {
  const base = {
    questionId: `${conceptId}-${filter.toLowerCase().replace(/\W+/g, '-')}-fallback`,
    sourceConcept: conceptId,
    concept_id: conceptId,
    subject,
    difficulty: 'easy' as const,
  };
  if (filter === 'Debug') return { ...base, taskType: 'debug_task', questionType: 'debug_task', prompt: 'Find and fix the error in this small snippet.', buggyCode: 'score = 10\nprint(scroe)', correctAnswer: 'score' };
  if (filter === 'Output') return { ...base, taskType: 'output_prediction', questionType: 'output_prediction', prompt: 'What output does this code produce?', code: 'value = 3\nprint(value + 2)', expectedOutput: '5', correctAnswer: '5' };
  if (filter === 'Fill Blank') return { ...base, taskType: 'fill_blank', questionType: 'fill_blank', prompt: 'Fill the missing part.', blanks: [{ id: 'answer', label: 'answer', answer: '=' }], correctAnswer: '=' };
  if (filter === 'True/False') return { ...base, taskType: 'true_false', questionType: 'true_false', prompt: 'A concept should be tested with a small example.', options: ['True', 'False'], correctAnswer: 'True' };
  if (filter === 'Code') return { ...base, taskType: 'coding_prompt', questionType: 'coding_prompt', prompt: 'Write a tiny example for this concept.', starterCode: '', correctAnswer: 'A valid small example' };
  if (filter === 'Transfer') return { ...base, taskType: 'transfer_question', questionType: 'transfer_question', prompt: 'Apply this concept to one new case.', correctAnswer: 'Reasonable transfer answer' };
  if (filter === 'Challenge' || filter === 'Puzzle') return { ...base, taskType: 'challenge_question', questionType: 'challenge_question', prompt: 'Solve this short reasoning challenge using the concept.', correctAnswer: 'Reasoned answer' };
  return { ...base, taskType: 'mcq', questionType: 'mcq', prompt: 'Which statement best describes this concept?', options: ['A named idea used in practice', 'A random long paragraph', 'An unrelated tool', 'A saved password'], correctAnswer: 'A named idea used in practice' };
}
