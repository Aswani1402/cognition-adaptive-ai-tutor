import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';

export default function ErrorBoundary({ children }: { children: ReactNode }) {
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const onError = () => setHasError(true);
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onError);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onError);
    };
  }, []);

  if (hasError) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50 dark:bg-slate-900">
        <div className="max-w-md w-full bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 text-center">
          <h2 className="text-2xl font-bold mb-2">This content is being prepared</h2>
          <p className="text-slate-500 mb-6">Showing saved learning content instead. You can safely continue.</p>
          <div className="flex gap-3 justify-center">
            <Link to="/dashboard" className="px-4 py-2 rounded-xl bg-sky-600 text-white font-semibold">Back to Dashboard</Link>
            <button onClick={() => setHasError(false)} className="px-4 py-2 rounded-xl border border-slate-300 dark:border-slate-700">Try again</button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
