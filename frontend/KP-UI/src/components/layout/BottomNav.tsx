import { NavLink } from 'react-router-dom';
import { Home, Map, Code2, BookOpen, Menu } from 'lucide-react';
import clsx from 'clsx';
import { useLearnerSession } from '../../context/LearnerSessionContext';

export default function BottomNav() {
  const session = useLearnerSession();
  const subjectPath = session.active_subject ? `/subjects/${encodeURIComponent(session.active_subject)}/path` : '/subjects';
  const conceptId = session.current_concept_id;
  const navItems = [
    { label: 'Home', icon: Home, to: '/dashboard' },
    { label: 'Path', icon: Map, to: subjectPath },
    { label: 'Quiz', icon: Code2, to: conceptId ? `/quiz/${conceptId}` : '/subjects' },
    { label: 'Notebook', icon: BookOpen, to: '/notebook' },
    { label: 'More', icon: Menu, to: '/settings' },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-950 border-t border-slate-200 dark:border-slate-800 z-40">
      <div className="flex items-center justify-around h-16">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => clsx('flex flex-col items-center justify-center w-full h-full space-y-1 transition-colors', isActive ? 'text-sky-600 dark:text-sky-400' : 'text-slate-500 dark:text-slate-400')}
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] font-medium">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
