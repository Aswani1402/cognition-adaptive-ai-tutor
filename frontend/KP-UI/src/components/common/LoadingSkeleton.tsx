import { Loader2 } from 'lucide-react';

export default function LoadingSkeleton({ title = 'Loading...', description = 'Preparing your content.' }: { title?: string; description?: string }) {
  return (
    <div className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 text-center">
      <Loader2 className="mx-auto mb-4 h-10 w-10 animate-spin text-sky-500" />
      <h3 className="text-lg font-bold">{title}</h3>
      <p className="mt-1 text-sm text-slate-500">{description}</p>
    </div>
  );
}
