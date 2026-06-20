import fs from 'fs';
const files = [
  'src/pages/LessonPage.tsx',
  'src/pages/DashboardPage.tsx',
  'src/components/assessment/AssessmentRenderer.tsx',
  'src/components/doubt/DoubtPanel.tsx',
  'src/pages/LearningPathPage.tsx',
  'src/pages/QuizPage.tsx',
  'src/pages/NotebookPage.tsx',
  'src/pages/ProgressPage.tsx',
  'src/pages/RewardsPage.tsx',
  'src/pages/DemoPage.tsx',
  'src/pages/LandingPage.tsx',
];

for (const file of files) {
  let content = fs.readFileSync(file, 'utf8');
  content = content.replace(/blue-/g, 'indigo-');
  fs.writeFileSync(file, content);
}
