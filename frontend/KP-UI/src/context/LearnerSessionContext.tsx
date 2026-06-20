import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { clearLearnerStorage } from '../lib/concepts';

type SessionState = {
  access_token: string;
  user_id: string;
  learner_id: string;
  app_learner_code: string;
  name: string;
  email: string;
  active_subject: string;
  current_concept_id: string;
  current_concept_name: string;
  current_difficulty: string;
  selected_teaching_view: string;
  backendConnected: boolean;
  mockFallbackUsed: boolean;
};

type SessionContextValue = SessionState & {
  setAuthSession: (auth: { access_token?: string; user_id?: string; learner_id?: string; app_learner_code?: string; name?: string; email?: string; active_subject?: string; selected_subject?: string; current_concept?: string; current_concept_id?: string; current_concept_name?: string; current_difficulty?: string }) => void;
  setSubjectContext: (subject: string, conceptId: string, conceptName: string, difficulty?: string, teachingView?: string) => void;
  updateCurrentConcept: (conceptId: string, conceptName: string) => void;
  clearSession: () => void;
  getCurrentLearnerId: () => string;
  setBackendState: (backendConnected: boolean, mockFallbackUsed?: boolean) => void;
};

const read = (key: string, fallback = '') => localStorage.getItem(key) || fallback;

const initialState = (): SessionState => ({
  access_token: read('access_token'),
  user_id: read('user_id'),
  learner_id: read('learner_id'),
  app_learner_code: read('app_learner_code'),
  name: read('user_name'),
  email: read('user_email'),
  active_subject: read('active_subject'),
  current_concept_id: read('current_concept_id'),
  current_concept_name: read('current_concept_name'),
  current_difficulty: read('current_difficulty', 'easy'),
  selected_teaching_view: read('selected_teaching_view', 'explanation'),
  backendConnected: false,
  mockFallbackUsed: false,
});

const LearnerSessionContext = createContext<SessionContextValue | null>(null);

export function LearnerSessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>(initialState);

  const value = useMemo<SessionContextValue>(() => ({
    ...state,
    setAuthSession(auth) {
      const accessToken = auth.access_token || '';
      const userId = auth.user_id || '';
      const learnerId = auth.app_learner_code || auth.learner_id || '';
      if (accessToken) localStorage.setItem('access_token', accessToken);
      if (userId) localStorage.setItem('user_id', userId);
      if (learnerId) localStorage.setItem('learner_id', learnerId);
      if (auth.app_learner_code || learnerId) localStorage.setItem('app_learner_code', auth.app_learner_code || learnerId);
      if (auth.name) localStorage.setItem('user_name', auth.name);
      if (auth.email) localStorage.setItem('user_email', auth.email);
      const activeSubject = auth.active_subject || auth.selected_subject || '';
      const conceptId = auth.current_concept_id || '';
      const conceptName = auth.current_concept_name || auth.current_concept || '';
      if (activeSubject) localStorage.setItem('active_subject', activeSubject);
      if (conceptId) localStorage.setItem('current_concept_id', conceptId);
      if (conceptName) localStorage.setItem('current_concept_name', conceptName);
      if (auth.current_difficulty) localStorage.setItem('current_difficulty', auth.current_difficulty);
      setState((curr) => ({
        ...curr,
        access_token: accessToken || curr.access_token,
        user_id: userId || curr.user_id,
        learner_id: learnerId || curr.learner_id,
        app_learner_code: auth.app_learner_code || learnerId || curr.app_learner_code,
        name: auth.name || curr.name,
        email: auth.email || curr.email,
        active_subject: activeSubject || curr.active_subject,
        current_concept_id: conceptId || curr.current_concept_id,
        current_concept_name: conceptName || curr.current_concept_name,
        current_difficulty: auth.current_difficulty || curr.current_difficulty,
      }));
    },
    setSubjectContext(subject, conceptId, conceptName, difficulty = 'easy', teachingView) {
      localStorage.setItem('active_subject', subject);
      localStorage.setItem('current_concept_id', conceptId);
      localStorage.setItem('current_concept_name', conceptName);
      localStorage.setItem('current_difficulty', difficulty);
      if (teachingView) localStorage.setItem('selected_teaching_view', teachingView);
      setState((curr) => ({
        ...curr,
        active_subject: subject,
        current_concept_id: conceptId,
        current_concept_name: conceptName,
        current_difficulty: difficulty,
        selected_teaching_view: teachingView || curr.selected_teaching_view,
      }));
    },
    updateCurrentConcept(conceptId, conceptName) {
      localStorage.setItem('current_concept_id', conceptId);
      localStorage.setItem('current_concept_name', conceptName);
      setState((curr) => ({ ...curr, current_concept_id: conceptId, current_concept_name: conceptName }));
    },
    clearSession() {
      clearLearnerStorage();
      setState(initialState());
    },
    getCurrentLearnerId() {
      return localStorage.getItem('learner_id') || state.learner_id || '';
    },
    setBackendState(backendConnected, mockFallbackUsed = false) {
      setState((curr) => ({ ...curr, backendConnected, mockFallbackUsed }));
    },
  }), [state]);

  return <LearnerSessionContext.Provider value={value}>{children}</LearnerSessionContext.Provider>;
}

export function useLearnerSession() {
  const ctx = useContext(LearnerSessionContext);
  if (!ctx) throw new Error('useLearnerSession must be used inside LearnerSessionProvider');
  return ctx;
}
