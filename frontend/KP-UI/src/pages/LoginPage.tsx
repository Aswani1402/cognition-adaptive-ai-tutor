import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, ArrowRight } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { ApiError, getLearnerContext, loginUser } from '../lib/api';
import { useState } from 'react';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { clearLearnerStorage } from '../lib/concepts';
import { logFrontendEvent } from '../lib/eventLog';

export default function LoginPage() {
  const navigate = useNavigate();
  const session = useLearnerSession();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [forgotMessage, setForgotMessage] = useState('');

  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const form = new FormData(e.currentTarget);
    try {
      const auth = await loginUser({ email: form.get('email'), password: form.get('password') });
      clearLearnerStorage();
      localStorage.setItem('access_token', auth.access_token);
      localStorage.setItem('user_id', auth.user_id);
      localStorage.setItem('learner_id', auth.app_learner_code || auth.learner_id);
      localStorage.setItem('app_learner_code', auth.app_learner_code || auth.learner_id);
      localStorage.setItem('user_email', auth.email || String(form.get('email') || ''));
      if (auth.name) localStorage.setItem('user_name', auth.name);
      if (auth.active_subject || auth.selected_subject) localStorage.setItem('active_subject', auth.active_subject || auth.selected_subject || '');
      if (auth.current_concept_id) localStorage.setItem('current_concept_id', auth.current_concept_id);
      if (auth.current_concept_name || auth.current_concept) localStorage.setItem('current_concept_name', auth.current_concept_name || auth.current_concept || '');
      if (auth.current_difficulty) localStorage.setItem('current_difficulty', auth.current_difficulty);
      session.setAuthSession(auth);
      logFrontendEvent({ action: 'login', module: 'auth', status: 'success', summary: 'Learner logged in' });
      const context = await getLearnerContext(auth.app_learner_code || auth.learner_id);
      if (context.activeSubject && context.currentConceptId) {
        session.setSubjectContext(context.activeSubject, context.currentConceptId, context.currentConceptName || context.currentConceptId, localStorage.getItem('current_difficulty') || 'easy');
        navigate(`/lesson/${context.currentConceptId}`);
      } else {
        navigate('/subjects');
      }
    } catch (err) {
      console.error('[login] failed', {
        status: err instanceof ApiError ? err.status : undefined,
        body: err instanceof ApiError ? err.body : undefined,
        error: err,
      });
      logFrontendEvent({ action: 'login', module: 'auth', status: 'failed', summary: 'Invalid email or password' });
      setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <div className="fixed top-4 right-4 z-20"><ThemeToggle /></div>
      <div className="w-full max-w-md bg-white dark:bg-slate-950 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-8 sm:p-10 relative overflow-hidden">
        
        {/* Decorative background blob */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl"></div>

        <div className="flex justify-center mb-8 relative z-10">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-200 dark:shadow-indigo-900/20 text-xl">
            C
          </div>
        </div>

        <h1 className="text-2xl font-bold text-center text-slate-900 dark:text-white mb-2 relative z-10">
          Welcome back
        </h1>
        <p className="text-center text-slate-500 mb-8 relative z-10">
          Sign in to continue your learning journey.
        </p>
        <div className="mb-6 relative z-10">
          <CogniGuideCard {...getCogniMessage({ page: 'login' })} compact />
        </div>

        <form onSubmit={handleLogin} className="space-y-5 relative z-10">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Mail className="h-5 w-5 text-slate-400" />
              </div>
              <input
                name="email"
                type="email"
                required
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                placeholder="you@demo.com"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                Password
              </label>
              <button type="button" onClick={() => setForgotMessage('Password reset is not implemented in this prototype.')} className="text-sm font-bold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
                Forgot password?
              </button>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-slate-400" />
              </div>
              <input
                name="password"
                type="password"
                required
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center items-center py-3.5 px-4 border border-transparent rounded-2xl shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors gap-2"
          >
            {loading ? 'Signing in...' : 'Sign In'} <ArrowRight className="w-4 h-4" />
          </button>
          {error && <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}
          {forgotMessage && <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">{forgotMessage}</p>}
        </form>

        <div className="mt-8 text-center relative z-10">
          <p className="text-sm text-slate-500">
            Don't have an account?{' '}
            <Link to="/register" className="font-bold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
              Start learning for free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function authErrorMessage(err: unknown) {
  const message = err instanceof Error ? err.message : '';
  if (/backend unavailable|backend url missing|failed to fetch|networkerror|abort|signal/i.test(message)) {
    return 'Backend is not reachable. Please start the backend.';
  }
  if (/invalid email or password|unauthorized|401/i.test(message)) return 'Invalid email or password';
  return message || 'Invalid email or password';
}
