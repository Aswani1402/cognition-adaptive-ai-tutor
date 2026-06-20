import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { Subject } from '../lib/types';
import { getSubjects, selectSubject } from '../lib/api';
import SubjectCard from '../components/learning/SubjectCard';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { logFrontendEvent } from '../lib/eventLog';

export default function SubjectsPage() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loadingSubject, setLoadingSubject] = useState('');
  const [error, setError] = useState('');
  const session = useLearnerSession();

  useEffect(() => {
    getSubjects().then(setSubjects);
  }, []);

  const handleSelect = async (subject: Subject) => {
    const learnerId = localStorage.getItem('learner_id') || '';
    if (!learnerId) {
      setError('Please sign in before selecting a subject.');
      return;
    }
    setLoadingSubject(subject.id);
    setError('');
    try {
      const result = await selectSubject(learnerId, subject.name);
      const teachingView = result.selected_teaching_view || result.current_teaching_view;
      session.setSubjectContext(
        result.active_subject || subject.name,
        result.current_concept_id,
        result.current_concept_name,
        result.current_difficulty || 'easy',
        teachingView
      );
      logFrontendEvent({ action: 'subject_selected', module: 'subject_selection', status: 'success', summary: result.active_subject || subject.name });
      navigate(result.next_route || (result.current_concept_id ? `/lesson/${result.current_concept_id}` : '/dashboard'));
    } catch {
      setError('Unable to start this subject. Please try again.');
    } finally {
      setLoadingSubject('');
    }
  };

  return (
    <div className="max-w-6xl mx-auto w-full space-y-8 pb-20">
      <CogniGuideCard {...getCogniMessage({ page: 'subjects' })} />
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50">
            Concept Maps
          </h1>
          <p className="mt-2 text-slate-500 font-medium text-lg">
            Choose or change your subject.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 rounded-xl text-sm font-bold shadow-sm">
          <Sparkles className="w-4 h-4" /> Guided subject setup
        </div>
      </header>
      {error && <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {subjects.map((subject) => <SubjectCard key={subject.id} subject={subject} onSelect={handleSelect} loading={loadingSubject === subject.id} />)}
      </div>
    </div>
  );
}
