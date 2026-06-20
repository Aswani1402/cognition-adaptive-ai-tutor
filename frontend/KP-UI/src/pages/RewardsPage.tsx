import { useEffect, useMemo, useState } from 'react';
import XPBadge from '../components/rewards/XPBadge';
import StreakWidget from '../components/rewards/StreakWidget';
import DailyGoalCard from '../components/rewards/DailyGoalCard';
import LevelProgressBar from '../components/rewards/LevelProgressBar';
import AchievementBadge from '../components/rewards/AchievementBadge';
import RewardPopup from '../components/rewards/RewardPopup';
import TutorMascot from '../components/rewards/TutorMascot';
import CelebrationModal from '../components/rewards/CelebrationModal';
import ConfettiEffect from '../components/rewards/ConfettiEffect';
import EncouragementToast from '../components/rewards/EncouragementToast';
import { getProgress, getRewardState } from '../lib/api';
import { ProgressData, RewardState } from '../lib/types';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { mergeRewardWithLocal, readLocalProgress } from '../lib/localProgress';
import { getConceptDisplayName } from '../lib/concepts';
import { logFrontendEvent } from '../lib/eventLog';

export default function RewardsPage() {
  const [rewardState, setRewardState] = useState<RewardState | null>(null);
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [showCelebration, setShowCelebration] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [toast, setToast] = useState('');
  const session = useLearnerSession();

  useEffect(() => {
    logFrontendEvent({ action: 'reward_checked', module: 'reward', status: 'started', summary: 'Rewards opened' });
    const learnerId = session.getCurrentLearnerId();
    Promise.all([getRewardState(learnerId), getProgress(learnerId, session.active_subject)]).then(([reward, progressData]) => {
      setRewardState(mergeRewardWithLocal(reward));
      setProgress(progressData);
    });
    const refresh = () => getRewardState(learnerId).then((reward) => setRewardState(mergeRewardWithLocal(reward)));
    window.addEventListener('cognitutor-progress-updated', refresh);
    return () => window.removeEventListener('cognitutor-progress-updated', refresh);
  }, [session.active_subject, session.learner_id]);

  const localProgress = readLocalProgress();
  const streakDays = useMemo(() => {
    const days = (progress?.streakCalendar ?? []).map((d) => ({ day: d.day, completed: d.completed }));
    if (localProgress.completedQuestions > 0 && !days.some((d) => d.day.toLowerCase() === 'today')) {
      return [{ day: 'Today', completed: true }, ...days].slice(0, 7);
    }
    return days.map((d, index) => index === 0 && localProgress.completedQuestions > 0 ? { ...d, completed: true } : d);
  }, [progress, localProgress.completedQuestions]);
  const achievements = useMemo(() => {
    const badges = rewardState?.badges || [];
    return [
      { title: 'First Lesson', achieved: rewardState ? rewardState.totalXp > 0 : false },
      { title: '7-day streak', achieved: rewardState ? rewardState.currentStreak >= 7 : false },
      { title: 'Debug Practice', achieved: badges.includes('Debug Practice') },
      { title: 'Concept Master', achieved: (progress?.conceptsMastered || 0) > 0 },
    ];
  }, [rewardState, progress]);

  if (!rewardState || !progress) {
    return <LoadingSkeleton title="Loading rewards" description="Checking XP, streak, and badges." />;
  }

  const celebrate = () => {
    setShowCelebration(true);
    setShowPopup(true);
    setToast('Strong work! Ready for a challenge?');
    setTimeout(() => setShowPopup(false), 1800);
    setTimeout(() => setToast(''), 2600);
  };

  return (
    <div className="max-w-6xl mx-auto w-full space-y-6 pb-24">
      <RewardPopup show={showPopup} message="+20 XP awarded" />
      <EncouragementToast message={toast} />
      <ConfettiEffect fire={showCelebration} />
      <CelebrationModal open={showCelebration} message={`Great work on ${session.current_concept_name || 'your current concept'}.`} xpAwarded={20} onClose={() => setShowCelebration(false)} />
      <CogniGuideCard {...getCogniMessage({ page: 'rewards' })} />

      <header className="rounded-3xl border border-sky-200 bg-gradient-to-r from-sky-500 via-cyan-500 to-violet-500 p-6 text-white">
        <h1 className="text-3xl font-black">Rewards & Momentum</h1>
        <p className="mt-1 text-white/90">Track XP, streaks, and unlocks with a Duolingo-like feedback loop.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <XPBadge value={rewardState.totalXp} />
          <button onClick={celebrate} className="rounded-full bg-white/20 px-4 py-1.5 text-sm font-semibold">Trigger celebration</button>
        </div>
      </header>

      <TutorMascot emotion="happy" event="correct_answer" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <DailyGoalCard current={rewardState.xpAwardedToday} goal={rewardState.dailyGoalXp} />
        <LevelProgressBar currentLevel={rewardState.currentLevel} totalXp={rewardState.totalXp} nextLevelXp={rewardState.nextLevelXp} />
        <StreakWidget streak={rewardState.currentStreak} days={streakDays} />
      </div>

      <section className="rounded-3xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-900/40 dark:bg-emerald-900/20">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-black text-emerald-900 dark:text-emerald-100">Today activity</h2>
            <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-200">
              {localProgress.completedQuestions > 0 ? 'Day 1 / Today completed' : 'No completed assessment recorded in this browser session yet.'}
            </p>
          </div>
          <div className="rounded-2xl bg-white px-4 py-3 text-sm font-black text-emerald-700 shadow-sm dark:bg-slate-950 dark:text-emerald-200">
            {localProgress.completedQuestions} questions · {localProgress.correctAnswers} correct · {localProgress.xp} local XP
          </div>
        </div>
        <p className="mt-3 text-sm text-emerald-800 dark:text-emerald-100">
          Concept progress: {getConceptDisplayName(session.current_concept_id, session.current_concept_name)} {localProgress.concepts[session.current_concept_id] || 0}%
        </p>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-black">Achievement badges</h2>
          <span className="text-sm text-slate-500">{achievements.filter((a) => a.achieved).length}/{achievements.length} earned</span>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {achievements.map((a) => <AchievementBadge key={a.title} title={a.title} achieved={a.achieved} />)}
        </div>
      </section>
    </div>
  );
}
