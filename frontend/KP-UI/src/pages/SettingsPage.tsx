import { useEffect, useState } from 'react';
import { Settings, User, Bell, Paintbrush, Loader2, Save } from 'lucide-react';
import clsx from 'clsx';
import ThemeToggle from '../components/ThemeToggle';
import { getLearnerContext } from '../lib/api';
import { useLearnerSession } from '../context/LearnerSessionContext';

export default function SettingsPage() {
  const session = useLearnerSession();
  const [saving, setSaving] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');

  const [formData, setFormData] = useState({
    name: session.name || localStorage.getItem('user_name') || 'Learner',
    email: session.email || localStorage.getItem('user_email') || '',
    goal: '',
    level: 'beginner',
    activeSubject: session.active_subject || '',
    dailyReminder: localStorage.getItem('pref_daily_reminder') === 'true',
    weeklyReport: localStorage.getItem('pref_weekly_report') === 'true',
  });

  useEffect(() => {
    const learnerId = session.getCurrentLearnerId();
    if (!learnerId) return;
    setLoadingProfile(true);
    getLearnerContext(learnerId)
      .then((profile) => {
        setFormData((curr) => ({
          ...curr,
          name: profile.displayName || session.name || localStorage.getItem('user_name') || curr.name,
          email: session.email || localStorage.getItem('user_email') || curr.email,
          goal: profile.goal || curr.goal,
          level: profile.level || curr.level,
          activeSubject: profile.activeSubject || session.active_subject || curr.activeSubject,
        }));
      })
      .catch(() => {
        setSaveMessage('Profile editing is not connected yet.');
      })
      .finally(() => setLoadingProfile(false));
  }, [session.active_subject, session.email, session.name]);

  const handleSave = () => {
    setSaving(true);
    localStorage.setItem('pref_daily_reminder', String(formData.dailyReminder));
    localStorage.setItem('pref_weekly_report', String(formData.weeklyReport));
    window.setTimeout(() => {
      setSaving(false);
      setShowSaved(true);
      setSaveMessage('Profile editing is not connected yet.');
      window.setTimeout(() => setShowSaved(false), 3000);
    }, 300);
  };

  return (
    <div className="max-w-4xl mx-auto w-full pb-20">
      <header className="mb-10 text-center sm:text-left flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4">
           <div className="w-16 h-16 rounded-2xl bg-slate-900 dark:bg-white flex items-center justify-center shadow-lg shadow-slate-900/10 dark:shadow-white/10 text-white dark:text-slate-900">
              <Settings className="w-8 h-8" />
           </div>
           <div>
             <h1 className="text-3xl font-black tracking-tight text-slate-900 dark:text-slate-50 uppercase">
               Settings
             </h1>
             <p className="mt-1 text-slate-500 font-medium">Manage your profile and local preferences.</p>
             {loadingProfile && <p className="mt-1 text-xs font-bold uppercase text-slate-400">Loading backend profile</p>}
           </div>
        </div>
        
        <button 
          onClick={handleSave}
          disabled={saving || showSaved}
          className={clsx(
            "px-6 py-3 rounded-full font-bold text-white shadow-lg transition-all flex items-center gap-2",
            showSaved ? "bg-emerald-500 shadow-emerald-500/20" : "bg-indigo-600 hover:bg-indigo-700 shadow-indigo-600/20 active:scale-95",
            saving && "opacity-70 cursor-not-allowed"
          )}
        >
          {saving ? <Loader2 className="w-5 h-5 animate-spin" /> : showSaved ? <CheckBadge /> : <Save className="w-5 h-5" />}
          {saving ? 'Saving...' : showSaved ? 'Saved locally' : 'Save Changes'}
        </button>
      </header>
      {saveMessage && <p className="mb-6 rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm font-semibold text-sky-900 dark:border-sky-900/40 dark:bg-sky-900/20 dark:text-sky-100">{saveMessage}</p>}

      <div className="space-y-8">
         
         {/* Profile Section */}
         <section className="bg-white dark:bg-slate-950 p-6 md:p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl transform translate-x-1/3 -translate-y-1/3 pointer-events-none"></div>
            
            <h2 className="text-xl font-bold flex items-center gap-3 mb-6 text-slate-900 dark:text-white relative z-10">
               <div className="p-2 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-xl">
                 <User className="w-5 h-5" />
               </div>
               Account Profile
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
               <div className="space-y-2">
                 <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Display Name</label>
                 <input 
                   type="text" 
                   value={formData.name}
                   onChange={e => setFormData({...formData, name: e.target.value})}
                   className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all"
                 />
               </div>
               <div className="space-y-2">
                 <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Email Address</label>
                 <input 
                   type="email" 
                   value={formData.email}
                   readOnly
                   className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all"
                 />
               </div>
               <div className="space-y-2 md:col-span-2">
                 <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Learning Goal</label>
                 <input 
                   type="text" 
                   value={formData.goal}
                   onChange={e => setFormData({...formData, goal: e.target.value})}
                   className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-all"
                 />
                 <p className="text-xs text-slate-500 mt-1">CogniTutor uses your goal to personalize examples.</p>
               </div>
               <div className="space-y-2">
                 <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Active Subject</label>
                 <input type="text" value={formData.activeSubject || 'Not selected'} readOnly className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white" />
               </div>
               <div className="space-y-2">
                 <label className="text-sm font-bold text-slate-700 dark:text-slate-300">Level</label>
                 <input type="text" value={formData.level || 'beginner'} readOnly className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-slate-900 dark:text-white" />
               </div>
            </div>
         </section>

         {/* Notifications Section */}
         <section className="bg-white dark:bg-slate-950 p-6 md:p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <h2 className="text-xl font-bold flex items-center gap-3 mb-6 text-slate-900 dark:text-white">
               <div className="p-2 bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 rounded-xl">
                 <Bell className="w-5 h-5" />
               </div>
               Notifications
            </h2>
            
            <div className="space-y-4">
              <label className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-600 transition-colors cursor-pointer gap-4">
                 <div>
                   <h4 className="font-bold text-slate-900 dark:text-white">Daily Learning Reminder</h4>
                   <p className="text-sm text-slate-500">Get notified to keep your streak alive.</p>
                 </div>
                 <div className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={formData.dailyReminder}
                      onChange={(e) => setFormData({...formData, dailyReminder: e.target.checked})}
                    />
                    <div className="w-14 h-7 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
                 </div>
              </label>
              
              <label className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-600 transition-colors cursor-pointer gap-4">
                 <div>
                   <h4 className="font-bold text-slate-900 dark:text-white">Weekly Progress Report</h4>
                   <p className="text-sm text-slate-500">Summary of your mastered concepts and XP.</p>
                 </div>
                 <div className="relative inline-flex items-center cursor-pointer shrink-0">
                    <input 
                      type="checkbox" 
                      className="sr-only peer" 
                      checked={formData.weeklyReport}
                      onChange={(e) => setFormData({...formData, weeklyReport: e.target.checked})}
                    />
                    <div className="w-14 h-7 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-0.5 after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-6 after:w-6 after:transition-all dark:border-gray-600 peer-checked:bg-indigo-600"></div>
                 </div>
              </label>
            </div>
         </section>

         {/* Appearance Section */}
         <section className="bg-white dark:bg-slate-950 p-6 md:p-8 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <h2 className="text-xl font-bold flex items-center gap-3 mb-6 text-slate-900 dark:text-white">
               <div className="p-2 bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 rounded-xl">
                 <Paintbrush className="w-5 h-5" />
               </div>
               Appearance
            </h2>
            <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                 <h4 className="font-bold text-slate-900 dark:text-white">Dark Mode</h4>
                 <p className="text-sm text-slate-500">Toggle dark and light themes.</p>
              </div>
              <ThemeToggle />
            </div>
         </section>

      </div>
    </div>
  );
}

function CheckBadge() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  );
}
