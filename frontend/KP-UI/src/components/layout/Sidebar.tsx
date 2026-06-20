import { NavLink } from 'react-router-dom';
import {
  Home, BookOpen, Map, GraduationCap, Code,
  Puzzle, GalleryVerticalEnd, Library, BarChart2, Award,
  AlertTriangle, BrainCircuit, HelpCircle, Settings
} from 'lucide-react';
import clsx from 'clsx';
import { useLearnerSession } from '../../context/LearnerSessionContext';

export default function Sidebar() {
  const session = useLearnerSession();
  const subjectPath = session.active_subject ? `/subjects/${encodeURIComponent(session.active_subject)}/path` : '/subjects';
  const conceptId = session.current_concept_id;
  const lessonPath = conceptId ? `/lesson/${conceptId}` : '/subjects';
  const quizPath = conceptId ? `/quiz/${conceptId}` : '/subjects';
  const puzzlePath = conceptId ? `/puzzle/${conceptId}` : '/subjects';
  const mindmapPath = conceptId ? `/mindmap/${conceptId}` : '/subjects';
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Home, to: '/dashboard' },
    { id: 'subject-selection', label: 'Subject Selection', icon: BookOpen, to: '/subjects' },
    { id: 'guided-session', label: 'Learn / Guided Session', icon: GraduationCap, to: lessonPath },
    { id: 'learning-path', label: 'Learning Path', icon: Map, to: subjectPath },
    { id: 'assessment', label: 'Assessment', icon: Code, to: quizPath },
    { id: 'puzzle', label: 'Challenges / Puzzle', icon: Puzzle, to: puzzlePath },
    { id: 'flashcards', label: 'Flashcards', icon: GalleryVerticalEnd, to: '/flashcards' },
    { id: 'mindmap', label: 'Mindmap', icon: Library, to: mindmapPath },
    { id: 'notebook', label: 'Notebook', icon: BookOpen, to: '/notebook' },
    { id: 'mistakes', label: 'Mistakes & Weakness', icon: AlertTriangle, to: '/mistakes' },
    { id: 'revision', label: 'Revision', icon: BarChart2, to: '/revision' },
    { id: 'doubts', label: 'Doubts', icon: HelpCircle, to: '/doubts' },
    { id: 'progress', label: 'Progress', icon: BarChart2, to: '/progress' },
    { id: 'rewards', label: 'Rewards', icon: Award, to: '/rewards' },
    { id: 'xai', label: 'XAI / Why-this', icon: BrainCircuit, to: '/xai' },
    { id: 'reviewer-evidence', label: 'Reviewer Evidence', icon: BarChart2, to: '/reviewer/evidence' },
    { id: 'settings', label: 'Settings', icon: Settings, to: '/settings' },
  ];
  const uniqueNavItems = navItems.filter((item, index, arr) => arr.findIndex((candidate) => candidate.id === item.id) === index);

  return (
    <aside className="hidden md:flex flex-col w-64 h-full bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 fixed left-0 top-0 z-40">
      <div className="p-6 flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-emerald-500 flex items-center justify-center shadow-lg shadow-sky-200 dark:shadow-sky-900/20">
          <GraduationCap className="w-6 h-6 text-white" />
        </div>
        <span className="font-bold text-xl tracking-tight text-slate-800 dark:text-white">
          CogniTutor
        </span>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1 scrollbar-hide">
        {uniqueNavItems.map((item) => (
          <NavLink
            key={item.id}
            to={item.to}
            className={({ isActive }) => clsx(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl font-medium transition-all duration-200",
              isActive 
                ? "bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-300" 
                : "text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-200"
            )}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
