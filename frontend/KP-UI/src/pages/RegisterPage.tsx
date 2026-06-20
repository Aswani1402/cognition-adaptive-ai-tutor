import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, Target, BarChart, ArrowRight } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { ApiError, registerUser } from '../lib/api';
import { useState } from 'react';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { clearLearnerStorage, initializeCleanLearner } from '../lib/concepts';
import { logFrontendEvent } from '../lib/eventLog';

export default function RegisterPage() {
  const navigate = useNavigate();
  const session = useLearnerSession();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    const form = new FormData(e.currentTarget);
    try {
      const auth = await registerUser({
        name: form.get('name'),
        email: form.get('email'),
        password: form.get('password'),
        goal: form.get('goal'),
        level: form.get('level'),
        preferred_subject: form.get('goal'),
      });
      clearLearnerStorage();
      const token = auth.access_token || '';
      localStorage.setItem('access_token', token);
      localStorage.setItem('user_id', auth.user_id);
      localStorage.setItem('learner_id', auth.app_learner_code || auth.learner_id);
      localStorage.setItem('app_learner_code', auth.app_learner_code || auth.learner_id);
      localStorage.setItem('user_email', auth.email || String(form.get('email') || ''));
      localStorage.setItem('user_name', auth.name || String(form.get('name') || 'Learner'));
      if (auth.current_difficulty) localStorage.setItem('current_difficulty', auth.current_difficulty);
      initializeCleanLearner();
      session.setAuthSession(auth);
      logFrontendEvent({ action: 'register', module: 'auth', status: 'success', summary: 'Clean learner state initialized' });
      navigate(auth.next_route || '/subjects');
    } catch (err) {
      const message = authErrorMessage(err, 'Unable to create account. Please try again.');
      console.error('[register] failed', {
        status: err instanceof ApiError ? err.status : undefined,
        body: err instanceof ApiError ? err.body : undefined,
        error: err,
      });
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-center justify-center p-4">
      <div className="fixed top-4 right-4 z-20"><ThemeToggle /></div>
      <div className="w-full max-w-md bg-white dark:bg-slate-950 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-800 p-8 sm:p-10 relative overflow-hidden my-8">
        
        {/* Decorative background blob */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl"></div>

        <div className="flex justify-center mb-6 relative z-10">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-white font-bold shadow-lg shadow-indigo-200 dark:shadow-indigo-900/20 text-xl">
            C
          </div>
        </div>

        <h1 className="text-2xl font-bold text-center text-slate-900 dark:text-white mb-2 relative z-10">
          Create Account
        </h1>
        <p className="text-center text-slate-500 mb-8 relative z-10">
          Join CogniTutor and master new skills.
        </p>
        <div className="mb-6 relative z-10">
          <CogniGuideCard {...getCogniMessage({ page: 'register' })} compact />
        </div>

        <form onSubmit={handleRegister} className="space-y-4 relative z-10">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
              Full Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <User className="h-5 w-5 text-slate-400" />
              </div>
              <input
                name="name"
                type="text"
                required
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                placeholder="Alex Learner"
              />
            </div>
          </div>

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
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                placeholder="you@email.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Lock className="h-5 w-5 text-slate-400" />
              </div>
              <input
                name="password"
                type="password"
                required
                className="block w-full pl-10 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                placeholder="••••••••"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Goal
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                   <Target className="h-4 w-4 text-slate-400" />
                </div>
                <select name="goal" className="block w-full pl-9 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all appearance-none text-sm">
                  <option>Python</option>
                  <option>SQL / Database</option>
                  <option>HTML/Web Basics</option>
                  <option>Git</option>
                  <option>Data Structures</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Level
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                   <BarChart className="h-4 w-4 text-slate-400" />
                </div>
                <select name="level" className="block w-full pl-9 pr-3 py-3 border border-slate-200 dark:border-slate-800 rounded-2xl bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all appearance-none text-sm">
                  <option>Beginner</option>
                  <option>Intermediate</option>
                  <option>Advanced</option>
                </select>
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center items-center py-3.5 px-4 border border-transparent rounded-2xl shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors gap-2 mt-4"
          >
            {loading ? 'Creating...' : 'Create Account'} <ArrowRight className="w-4 h-4" />
          </button>
          {error && <p className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}
        </form>

        <div className="mt-8 text-center relative z-10">
          <p className="text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="font-bold text-indigo-600 hover:text-indigo-500 dark:text-indigo-400">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function authErrorMessage(err: unknown, fallback: string) {
  const message = err instanceof Error ? err.message : fallback;
  if (/already registered|already exists|duplicate/i.test(message)) {
    return 'Account already exists. Please sign in.';
  }
  if (/backend unavailable|backend url missing|failed to fetch|networkerror|abort|signal/i.test(message)) {
    return 'Backend is not reachable. Please start the backend.';
  }
  return message || fallback;
}
