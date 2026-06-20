import { useEffect, useState } from 'react';
import { Moon, Sun, Monitor } from 'lucide-react';

type ThemeMode = 'light' | 'dark' | 'system';

const THEME_KEY = 'theme';

const getSystemDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

function applyTheme(mode: ThemeMode) {
  const isDark = mode === 'dark' || (mode === 'system' && getSystemDark());
  document.documentElement.classList.toggle('dark', isDark);
}

export function initializeTheme() {
  const saved = (localStorage.getItem(THEME_KEY) as ThemeMode | null) ?? 'light';
  applyTheme(saved);
}

export default function ThemeToggle() {
  const [mode, setMode] = useState<ThemeMode>('light');

  useEffect(() => {
    const saved = (localStorage.getItem(THEME_KEY) as ThemeMode | null) ?? 'light';
    setMode(saved);
    applyTheme(saved);

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onSystemChange = () => {
      const active = (localStorage.getItem(THEME_KEY) as ThemeMode | null) ?? 'light';
      if (active === 'system') applyTheme('system');
    };

    mq.addEventListener('change', onSystemChange);
    return () => mq.removeEventListener('change', onSystemChange);
  }, []);

  const cycleMode = () => {
    const next: ThemeMode = mode === 'light' ? 'dark' : mode === 'dark' ? 'system' : 'light';
    setMode(next);
    localStorage.setItem(THEME_KEY, next);
    applyTheme(next);
  };

  const Icon = mode === 'light' ? Sun : mode === 'dark' ? Moon : Monitor;

  return (
    <button
      onClick={cycleMode}
      className="p-2.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-sky-100 dark:hover:bg-sky-900/40 transition-colors"
      aria-label={`Theme: ${mode}`}
      title={`Theme: ${mode}`}
    >
      <Icon className="w-5 h-5" />
    </button>
  );
}
