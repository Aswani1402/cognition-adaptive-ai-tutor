import clsx from 'clsx';
import { CogniMood } from './cogniScripts';

export default function CogniParrot({ mood = 'happy', size = 'md' }: { mood?: CogniMood; size?: 'sm' | 'md' | 'lg' }) {
  const face = mood === 'celebrating' || mood === 'success' ? '🦜' : mood === 'warning' || mood === 'confused' ? '🦉' : '🦜';
  return (
    <div className={clsx(
      'grid shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-emerald-400 via-sky-400 to-indigo-500 shadow-lg shadow-sky-500/20',
      size === 'sm' ? 'h-10 w-10 text-2xl' : size === 'lg' ? 'h-20 w-20 text-5xl' : 'h-14 w-14 text-3xl',
      mood === 'celebrating' && 'animate-pulse'
    )}>
      <span aria-label={`Cogni ${mood}`} role="img">{face}</span>
    </div>
  );
}
