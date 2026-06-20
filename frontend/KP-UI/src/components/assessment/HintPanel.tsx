import { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import ReadAloudButton from '../common/ReadAloudButton';

export default function HintPanel({ hints }: { hints: string[] }) {
  const [level, setLevel] = useState(0);
  const current = hints[level] || 'No more hints';
  const [typeLabel, body] = splitHint(current);
  return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/40 dark:bg-amber-900/20">
      <div className="mb-2 flex flex-wrap items-center gap-2 font-bold text-amber-700 dark:text-amber-300">
        <Lightbulb className="h-4 w-4" />
        Hint {Math.min(level + 1, hints.length)}
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] uppercase tracking-wider text-amber-800 dark:bg-amber-950 dark:text-amber-200">{typeLabel}</span>
      </div>
      <p className="text-sm text-amber-900 dark:text-amber-100">{shortHint(body, level)}</p>
      <div className="mt-3"><ReadAloudButton text={shortHint(body, level)} compact /></div>
      {hints.length > 1 && level < hints.length - 1 && (
        <button onClick={() => setLevel((v) => Math.min(v + 1, hints.length - 1))} className="mt-3 rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-white">
          Show stronger hint
        </button>
      )}
    </div>
  );
}

function shortHint(text: string, level: number) {
  const clean = text.replace(/\s+/g, ' ').trim();
  const sentences = clean.split(/(?<=[.!?])\s+/).filter(Boolean);
  const maxSentences = level === 0 ? 1 : 2;
  const clipped = (sentences.length ? sentences.slice(0, maxSentences).join(' ') : clean);
  return clipped.length > 180 ? `${clipped.slice(0, 179).trim()}...` : clipped;
}

function splitHint(text: string): [string, string] {
  const match = text.match(/^([a-z_ ]+)(?: level \d+)?:\s*(.*)$/i);
  if (!match) return ['guided hint', text];
  return [match[1].replaceAll('_', ' '), match[2] || text];
}
