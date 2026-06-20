import { AlertTriangle } from 'lucide-react';

export default function ErrorState({ message = 'Something went wrong.', onRetry }: { message?: string; onRetry?: () => void }) {
  return (
    <div className="rounded-3xl border border-rose-200 dark:border-rose-900/40 bg-rose-50 dark:bg-rose-900/20 p-8 text-center">
      <AlertTriangle className="mx-auto mb-4 h-10 w-10 text-rose-500" />
      <h3 className="text-lg font-bold text-rose-800 dark:text-rose-200">This content is being prepared</h3>
      <p className="mt-1 text-sm text-rose-700/80 dark:text-rose-200/80">{message || 'Showing saved learning content instead.'}</p>
      {onRetry && <button onClick={onRetry} className="mt-4 rounded-xl bg-rose-600 px-4 py-2 text-sm font-semibold text-white">Try again</button>}
    </div>
  );
}
