import { Link } from 'react-router-dom';
import { PlayCircle, Target, Brain, Flame, ArrowRight, Zap, RefreshCw, Trophy, Sparkles, BookOpen } from 'lucide-react';
import { useEffect, useState } from 'react';
import { LearnerProfile, RewardState } from '../lib/types';
import { getLearnerContext, getStreakXP } from '../lib/api';
import TutorMascot from '../components/rewards/TutorMascot';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName } from '../lib/concepts';
import { mergeRewardWithLocal, readLocalProgress } from '../lib/localProgress';

export default function DashboardPage() {
  const session = useLearnerSession();
  const [rewards, setRewards] = useState<RewardState | null>(null);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);

  useEffect(() => {
    const learnerId = session.getCurrentLearnerId();
    getStreakXP(learnerId).then((state) => setRewards(mergeRewardWithLocal(state)));
    getLearnerContext(learnerId).then(setProfile);
  }, [session]);

  const activeSubject = profile?.activeSubject || session.active_subject || 'Select a subject';
  const activeConceptId = profile?.currentConceptId || session.current_concept_id;
  const activeConceptName = getConceptDisplayName(activeConceptId, profile?.currentConceptName || session.current_concept_name || 'Choose your first concept');
  const lessonRoute = activeConceptId ? `/lesson/${activeConceptId}` : '/subjects';
  const dailyGoalXp = rewards?.dailyGoalXp || 50;
  const xpToday = rewards?.xpAwardedToday || 0;
  const xpRemaining = Math.max(0, dailyGoalXp - xpToday);
  const localProgress = readLocalProgress();
  const conceptMastery = activeConceptId ? localProgress.concepts[activeConceptId] : undefined;
  const hasActivity = localProgress.completedQuestions > 0 || (rewards?.totalXp || 0) > 0;

  return (
    <div className="flex flex-col xl:flex-row gap-6 max-w-7xl mx-auto w-full pb-20">
      {/* Main Content Area */}
      <div className="flex-1 space-y-6">
        <header className="mb-8 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-end">
          <div>
             <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-50">
               Welcome back, {profile?.displayName || 'Learner'}!
             </h1>
             <p className="mt-2 text-slate-600 dark:text-slate-400">
               You're on a {rewards?.currentStreak || 0}-day streak. Let's keep the momentum going.
             </p>
          </div>
          <Link
            to="/subjects"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 shadow-sm transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200 dark:hover:bg-slate-900"
          >
            <BookOpen className="h-4 w-4" />
            Change Subject
          </Link>
        </header>
        <CogniGuideCard {...getCogniMessage({ page: 'dashboard', activityType: profile?.returningRevisionNeeded ? 'returning_revision' : 'teaching', timeGapCategory: profile?.returningRevisionNeeded ? 'days' : undefined })} />

        {/* Mascot Encouragement */}
        <TutorMascot
          emotion="encouraging"
          event="streak_maintained"
          compact
          message={`Your ${activeSubject} session is ready. ${xpRemaining} XP left to hit your daily goal.`}
        />

        {/* Hero: Continue Learning */}
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 to-indigo-700 text-white shadow-xl shadow-indigo-500/10">
          {/* Background pattern */}
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-white/10 blur-3xl mix-blend-overlay"></div>
          
          <div className="px-8 py-10 sm:px-10 flex flex-col sm:flex-row items-center gap-8 relative z-10">
            <div className="flex-1 text-center sm:text-left">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 backdrop-blur-sm text-sm font-medium mb-4 text-indigo-50">
                <PlayCircle className="w-4 h-4" /> Up Next
              </span>
              <h2 className="text-2xl sm:text-3xl font-bold mb-2">{activeConceptName}</h2>
              <p className="text-indigo-100 mb-6 text-sm sm:text-base max-w-md line-clamp-2">
                Continue your guided {activeSubject} lesson at {session.current_difficulty || 'easy'} difficulty.
              </p>
              <Link 
                to={lessonRoute}
                className="inline-flex items-center justify-center bg-white text-indigo-600 px-6 py-3 rounded-2xl font-bold tracking-wide hover:bg-slate-50 transition-all active:scale-95 shadow-sm"
              >
                Continue Lesson
              </Link>
            </div>
            
            {/* Visual element */}
            <div className="hidden sm:flex relative w-32 h-32 items-center justify-center">
              <div className="absolute inset-0 border-8 border-white/20 rounded-full"></div>
              <div 
                className="absolute inset-0 border-8 border-white rounded-full transition-all duration-1000 ease-out z-10" 
                style={{ clipPath: 'polygon(50% 50%, 50% 0, 100% 0, 100% 100%, 50% 100%)' }}
              ></div>
              <span className="text-center text-xl font-black relative z-20">{hasActivity && conceptMastery ? `${conceptMastery}%` : 'New'}</span>
            </div>
          </div>
        </section>

        {/* Quick Actions / Activity cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          
          {/* Today's Review */}
          <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow group flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-orange-100 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <RefreshCw className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold">Today's Review</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
                Review flashcards and saved mistakes for your current {activeSubject} concept.
              </p>
            </div>
            <Link to="/flashcards" className="mt-6 flex items-center gap-2 text-sm font-semibold text-orange-600 dark:text-orange-400 hover:text-orange-700 dark:hover:text-orange-300">
              Start Review <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>

          {/* Weak Areas Focus */}
          <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow group flex flex-col justify-between">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-rose-100 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Brain className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold">Weak Areas</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 mb-2">
                Your recent answers decide whether you review, retry, or move to the next difficulty.
              </p>
              <div className="inline-flex text-xs font-bold text-rose-500 bg-rose-50 dark:bg-rose-900/20 px-2 py-1 rounded">Recommended Fix</div>
            </div>
            <Link to="/mistakes" className="mt-6 flex items-center gap-2 text-sm font-semibold text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300">
              Practice Now <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>

        </div>
      </div>

      {/* Right Progress Sidebar */}
      <div className="w-full xl:w-80 flex flex-col gap-6">
        
        {/* Daily Goal */}
        <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Target className="w-20 h-20" />
          </div>
          <div className="relative z-10">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold flex items-center gap-2 text-slate-800 dark:text-slate-200">
                <Target className="w-4 h-4 text-emerald-500" /> Daily XP Goal
              </h3>
            </div>
            <div className="flex items-end gap-2 mb-2">
              <span className="text-4xl font-black text-slate-900 dark:text-white">{xpToday}</span>
              <span className="text-slate-500 mb-1 font-bold">/ {dailyGoalXp} XP</span>
            </div>
            
            <div className="h-4 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden mt-6 mb-2 shadow-inner">
              <div 
                className={`h-full bg-emerald-500 transition-all duration-1000 rounded-full`}
                style={{ width: `${Math.min(100, (xpToday / dailyGoalXp) * 100)}%` }}
              ></div>
            </div>
            <p className="text-xs text-slate-400 font-medium text-center">{xpRemaining} XP to reach your goal today.</p>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col items-center justify-center text-center group">
            <Flame className="w-8 h-8 text-orange-500 mb-3 fill-current group-hover:scale-110 transition-transform drop-shadow-md" />
            <div className="text-3xl font-black text-slate-900 dark:text-white">{rewards?.currentStreak || 0}</div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Day Streak</div>
          </div>
          <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col items-center justify-center text-center group">
            <Zap className="w-8 h-8 text-amber-400 mb-3 fill-current group-hover:scale-110 transition-transform drop-shadow-md" />
            <div className="text-3xl font-black text-slate-900 dark:text-white">{rewards?.totalXp || 0}</div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Total XP</div>
          </div>
        </div>
        
        {/* Current Level */}
        <div className="bg-white dark:bg-slate-950 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm flex items-center gap-5">
          <div className="w-16 h-16 rounded-[1.5rem] bg-gradient-to-tr from-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-pink-500/20 shrink-0 transform -rotate-3 hover:rotate-0 transition-transform cursor-pointer">
            <Trophy className="w-7 h-7 text-white drop-shadow-md" />
          </div>
          <div>
            <h4 className="font-black text-lg text-slate-900 dark:text-white">Level {rewards?.currentLevel || 1} Scholar</h4>
            <div className="text-sm text-slate-500 font-medium leading-tight mt-1">
              {1500 - (rewards?.totalXp || 0)} XP to Next Level
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
}


