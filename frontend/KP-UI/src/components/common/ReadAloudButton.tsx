import { Volume2 } from 'lucide-react';
import { useState } from 'react';

export default function ReadAloudButton({ text, compact = false }: { text: string; compact?: boolean }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
  if (!supported || !text?.trim()) return null;

  const read = () => {
    window.speechSynthesis.cancel();
    if (speaking) {
      setSpeaking(false);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text.slice(0, 1200));
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <button
      type="button"
      onClick={read}
      className={`inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white font-bold text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-200 ${compact ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm'}`}
    >
      <Volume2 className="h-4 w-4" />
      {speaking ? 'Stop reading' : 'Read aloud prototype'}
    </button>
  );
}
