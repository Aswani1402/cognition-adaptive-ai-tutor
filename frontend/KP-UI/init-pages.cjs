const fs = require('fs');
const path = require('path');

const pagesDir = path.join(__dirname, 'src', 'pages');

if (!fs.existsSync(pagesDir)) {
  fs.mkdirSync(pagesDir, { recursive: true });
}

const pages = [
  'LandingPage', 'LoginPage', 'RegisterPage', 'DashboardPage', 'SubjectsPage',
  'LearningPathPage', 'LessonPage', 'QuizPage', 'PuzzlePage', 'FlashcardsPage',
  'MindMapPage', 'NotebookPage', 'ProgressPage', 'RewardsPage', 'MistakesPage',
  'SettingsPage', 'DemoPage'
];

pages.forEach(page => {
  const fileContent = `export default function ${page}() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">${page}</h1>
      <p className="mt-4 text-slate-600">This page is under construction.</p>
    </div>
  );
}
`;
  fs.writeFileSync(path.join(pagesDir, `${page}.tsx`), fileContent);
});

console.log('Pages created successfully.');
