/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import LoadingSkeleton from './components/common/LoadingSkeleton';
import { LearnerSessionProvider } from './context/LearnerSessionContext';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const SubjectsPage = lazy(() => import('./pages/SubjectsPage'));
const LearningPathPage = lazy(() => import('./pages/LearningPathPage'));
const LessonPage = lazy(() => import('./pages/LessonPage'));
const QuizPage = lazy(() => import('./pages/QuizPage'));
const PuzzlePage = lazy(() => import('./pages/PuzzlePage'));
const FlashcardsPage = lazy(() => import('./pages/FlashcardsPage'));
const MindMapPage = lazy(() => import('./pages/MindMapPage'));
const NotebookPage = lazy(() => import('./pages/NotebookPage'));
const AudioOverviewPage = lazy(() => import('./pages/AudioOverviewPage'));
const ProgressPage = lazy(() => import('./pages/ProgressPage'));
const RewardsPage = lazy(() => import('./pages/RewardsPage'));
const MistakesPage = lazy(() => import('./pages/MistakesPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const DemoPage = lazy(() => import('./pages/DemoPage'));
const XAIPage = lazy(() => import('./pages/XAIPage'));
const ReviewerInsightsPage = lazy(() => import('./pages/ReviewerInsightsPage'));
const ReviewerEvidencePage = lazy(() => import('./pages/ReviewerEvidencePage'));
const NotebookGuidePage = lazy(() => import('./pages/NotebookGuidePage'));
const TutorChatPage = lazy(() => import('./pages/TutorChatPage'));
const DoubtsPage = lazy(() => import('./pages/DoubtsPage'));
const RevisionPage = lazy(() => import('./pages/RevisionPage'));
const MainLayout = lazy(() => import('./components/layout/MainLayout'));

export default function App() {
  return (
    <LearnerSessionProvider>
      <Router>
        <ErrorBoundary>
          <Suspense fallback={<LoadingSkeleton title="Loading CogniTutor" description="Preparing your learning space." />}>
            <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            
            {/* Protected Routes wrapped in MainLayout */}
            <Route element={<MainLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/subjects" element={<SubjectsPage />} />
              <Route path="/subjects/:subjectId/path" element={<LearningPathPage />} />
              <Route path="/lesson/:conceptId" element={<LessonPage />} />
              <Route path="/quiz/:conceptId" element={<QuizPage />} />
              <Route path="/assessment" element={<QuizPage />} />
              <Route path="/puzzle/:conceptId" element={<PuzzlePage />} />
              <Route path="/flashcards" element={<FlashcardsPage />} />
              <Route path="/mindmap" element={<MindMapPage />} />
              <Route path="/mindmap/:conceptId" element={<MindMapPage />} />
              <Route path="/notebook" element={<NotebookPage />} />
              <Route path="/notebook/guide" element={<NotebookGuidePage />} />
              <Route path="/tutor/chat" element={<TutorChatPage />} />
              <Route path="/revision" element={<RevisionPage />} />
              <Route path="/doubts" element={<DoubtsPage />} />
              <Route path="/audio-overview" element={<AudioOverviewPage />} />
              <Route path="/progress" element={<ProgressPage />} />
              <Route path="/rewards" element={<RewardsPage />} />
              <Route path="/mistakes" element={<MistakesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/xai" element={<XAIPage />} />
              <Route path="/reviewer-insights" element={<ReviewerInsightsPage />} />
              <Route path="/reviewer/evidence" element={<ReviewerEvidencePage />} />
              <Route path="/demo" element={<DemoPage />} />
            </Route>
            </Routes>
          </Suspense>
        </ErrorBoundary>
      </Router>
    </LearnerSessionProvider>
  );
}
