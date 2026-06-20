import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { LockKeyhole } from 'lucide-react';
import { hasStoredSession } from '../../lib/session';
import ThemeToggle from '../ThemeToggle';

export default function AuthGate({ children }: { children: ReactNode }) {
  if (hasStoredSession()) return <>{children}</>;

  return (
    <div className="min-h-screen bg-[#F8FAF5] px-4 py-6 text-slate-900 dark:bg-[#0b1220] dark:text-slate-50">
      <div className="mx-auto flex max-w-5xl justify-end">
        <ThemeToggle />
      </div>
      <main className="mx-auto grid min-h-[80vh] max-w-lg place-items-center">
        <section className="w-full rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-800 dark:bg-slate-950">
          <div className="mx-auto mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-300">
            <LockKeyhole className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-black">Sign in to continue</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            This CogniTutor page uses your learner session for progress, notebook memory, rewards, and adaptive recommendations.
          </p>
          <Link to="/login" className="mt-6 inline-flex rounded-2xl bg-sky-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-sky-500/20">
            Go to login
          </Link>
        </section>
      </main>
    </div>
  );
}
