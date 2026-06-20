export default function CogniSpeechBubble({ message }: { message: string }) {
  return (
    <div className="relative rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:text-slate-200">
      <span className="absolute -left-2 top-5 h-4 w-4 rotate-45 border-b border-l border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950" />
      {message}
    </div>
  );
}
