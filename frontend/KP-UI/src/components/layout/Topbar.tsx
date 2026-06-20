import { useEffect, useState } from 'react';
import { Search, Flame, Bell, LogOut, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ThemeToggle from '../ThemeToggle';
import { getBackendHealth, getRewardState } from '../../lib/api';
import { useLearnerSession } from '../../context/LearnerSessionContext';
import { getConceptDisplayName } from '../../lib/concepts';
import { mergeRewardWithLocal, readLocalProgress } from '../../lib/localProgress';
import { logFrontendEvent } from '../../lib/eventLog';

export default function Topbar() {
  const [backendMode, setBackendMode] = useState<'checking' | 'backend' | 'missing' | 'error'>('checking');
  const [backendDetail, setBackendDetail] = useState('');
  const [reward, setReward] = useState({ xp: 0, streak: 0 });
  const [menu, setMenu] = useState<'profile' | 'notifications' | 'backend' | null>(null);
  const [message, setMessage] = useState('');
  const [query, setQuery] = useState('');
  const session = useLearnerSession();
  const navigate = useNavigate();

  useEffect(() => {
    getBackendHealth().then((result) => { setBackendMode(result.mode); setBackendDetail(result.detail); });
    const loadReward = () => getRewardState(session.getCurrentLearnerId())
      .then((state) => {
        const merged = mergeRewardWithLocal(state);
        setReward({ xp: merged.totalXp, streak: merged.currentStreak });
      })
      .catch(() => {
        const local = readLocalProgress();
        setReward({ xp: local.xp, streak: local.streak });
      });
    loadReward();
    window.addEventListener('cognitutor-progress-updated', loadReward);
    return () => window.removeEventListener('cognitutor-progress-updated', loadReward);
  }, [session.learner_id]);

  const badgeClass = backendMode === 'backend'
    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
    : backendMode === 'error'
      ? 'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300'
      : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300';

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6 lg:px-8 h-16 bg-white/90 dark:bg-slate-950/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
      <div className="flex-1 flex px-2 md:px-0">
        <div className="max-w-md w-full relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-400" aria-hidden="true" />
          </div>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && query.trim()) {
                const result = searchConcept(query);
                logFrontendEvent({ action: 'search', module: 'topbar', status: result ? 'success' : 'empty', summary: query });
                if (result) navigate(result);
                else setMenu('notifications');
              }
            }}
            className="absolute inset-0 block w-full pl-10 pr-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 sm:text-sm"
            placeholder="Search concepts, notes..."
            type="search"
          />
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 mr-1">
          <button onClick={() => setMenu(menu === 'backend' ? null : 'backend')} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold ${badgeClass}`}>
            <span className={`h-2 w-2 rounded-full ${backendMode === 'backend' ? 'bg-emerald-500' : backendMode === 'checking' ? 'bg-amber-400' : backendMode === 'error' ? 'bg-rose-500' : 'bg-slate-400'}`} />
            {backendMode === 'backend' ? 'Live backend' : backendMode === 'checking' ? 'Checking backend' : 'Saved content'}
          </button>
          <button onClick={() => navigate('/rewards')} className="flex items-center gap-1.5 text-orange-600 dark:text-orange-300 font-bold bg-orange-50 dark:bg-orange-500/10 px-3 py-1.5 rounded-full">
            <Flame className="w-4 h-4 fill-current" />
            <span>{reward.streak}</span>
          </button>
          <button onClick={() => navigate('/rewards')} className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 font-bold bg-amber-50 dark:bg-amber-500/10 px-3 py-1.5 rounded-full">
            <span className="text-xs uppercase tracking-wider">XP</span>
            <span>{reward.xp}</span>
          </button>
        </div>
        <ThemeToggle />
        <button onClick={() => setMenu(menu === 'notifications' ? null : 'notifications')} className="p-2 text-slate-500 dark:text-slate-300 relative">
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full border-2 border-white dark:border-slate-950"></span>
          <Bell className="w-6 h-6" />
        </button>
        <button onClick={() => setMenu(menu === 'profile' ? null : 'profile')} className="w-9 h-9 rounded-full bg-gradient-to-br from-sky-500 to-violet-500 flex items-center justify-center text-white shadow-sm" title={session.user_id || session.learner_id || 'Learner'}>
          <User className="w-5 h-5" />
        </button>
        <button
          type="button"
          onClick={() => {
            session.clearSession();
            logFrontendEvent({ action: 'logout', module: 'auth', status: 'success', summary: 'Session cleared' });
            navigate('/login');
          }}
          className="grid h-9 w-9 place-items-center rounded-full border border-slate-200 text-slate-500 hover:bg-slate-50 dark:border-slate-800 dark:text-slate-300 dark:hover:bg-slate-900"
          title="Log out"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
      {menu && (
        <div className="absolute right-4 top-14 z-50 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-800 dark:bg-slate-950">
          {menu === 'profile' && (
            <div className="space-y-3">
              <h3 className="font-black">Learner Profile</h3>
              <Info label="Name" value={session.name || localStorage.getItem('user_name') || 'Learner'} />
              <Info label="Email" value={session.email || localStorage.getItem('user_email') || 'Not shown'} />
              <Info label="Learner ID" value={session.app_learner_code || session.learner_id || localStorage.getItem('app_learner_code') || 'Not available'} />
              <Info label="Active subject" value={session.active_subject || 'Not selected'} />
              <Info label="Current concept" value={getConceptDisplayName(session.current_concept_id, session.current_concept_name)} />
              {message && <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">{message}</p>}
              <button onClick={() => setMessage('Change password backend route not available yet.')} className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm font-bold dark:border-slate-700">Change password</button>
              <button onClick={() => { session.clearSession(); logFrontendEvent({ action: 'logout', module: 'auth', status: 'success', summary: 'Session cleared' }); navigate('/login'); }} className="w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-bold text-white dark:bg-white dark:text-slate-900">Logout</button>
            </div>
          )}
          {menu === 'notifications' && (
            <div className="space-y-3">
              <h3 className="font-black">Notifications</h3>
              <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm font-semibold dark:bg-slate-900">{reward.xp > 0 ? 'Daily goal progress is active today.' : 'No new notifications. Start one quick check to mark today complete.'}</p>
              <p className="rounded-xl bg-slate-50 px-3 py-2 text-sm font-semibold dark:bg-slate-900">Revision reminders appear here when due.</p>
              {query.trim() && <p className="rounded-xl bg-amber-50 px-3 py-2 text-sm font-semibold text-amber-800">No result for "{query}". Try a topic like Variables, SELECT, or Database Basics.</p>}
            </div>
          )}
          {menu === 'backend' && (
            <div className="space-y-2">
              <h3 className="font-black">Backend Status</h3>
              <Info label="Mode" value={backendMode === 'backend' ? 'Live backend connected' : 'Saved learning content fallback'} />
              <Info label="Last checked" value={backendDetail || 'Checked by frontend'} />
              <Info label="API base" value={import.meta.env.VITE_API_BASE_URL || 'Not configured'} />
            </div>
          )}
        </div>
      )}
    </header>
  );
}

function searchConcept(query: string) {
  const q = query.toLowerCase();
  const pairs: [string, string][] = [
    ['variables', '/lesson/P1'],
    ['data types', '/lesson/P2'],
    ['conditionals', '/lesson/P3'],
    ['loops', '/lesson/P4'],
    ['functions', '/lesson/P5'],
    ['database', '/lesson/S1'],
    ['select', '/lesson/S2'],
    ['where', '/lesson/S3'],
    ['join', '/lesson/S4'],
    ['notebook', '/notebook'],
    ['mistakes', '/mistakes'],
    ['revision', '/revision'],
    ['rewards', '/rewards'],
  ];
  return pairs.find(([term]) => q.includes(term))?.[1] || '';
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-black uppercase text-slate-400">{label}</p>
      <p className="break-words text-sm font-semibold text-slate-700 dark:text-slate-200">{value}</p>
    </div>
  );
}
