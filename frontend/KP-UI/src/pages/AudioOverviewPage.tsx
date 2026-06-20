import { useEffect, useMemo, useState } from 'react';
import { Headphones, Pause, Play, Square } from 'lucide-react';
import { getAudioOverview } from '../lib/api';

const tabs = [
  ['Intro', 'concept_intro_voice_script'],
  ['Teaching', 'teaching_voice_script'],
  ['Revision', 'revision_voice_script'],
  ['Mistake Feedback', 'mistake_feedback_voice_script'],
  ['Doubt', 'doubt_explanation_voice_script'],
  ['Encouragement', 'encouragement_script'],
  ['Next Step', 'next_step_guidance_script'],
] as const;

export default function AudioOverviewPage() {
  const [active, setActive] = useState<(typeof tabs)[number][1]>('teaching_voice_script');
  const [packet, setPacket] = useState<Record<string, unknown>>({});
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    getAudioOverview(active).then(setPacket);
    stopSpeech();
  }, [active]);

  const voice = (packet.voice_script || packet.audio_overview || {}) as Record<string, unknown>;
  const overview = (packet.audio_overview || {}) as Record<string, unknown>;
  const script = useMemo(() => String(voice.script || overview.script || ''), [voice, overview]);
  const sections = (voice.voice_sections || overview.voice_sections || {}) as Record<string, unknown>;

  function playSpeech() {
    if (!('speechSynthesis' in window) || !script) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(script));
    setSpeaking(true);
  }

  function pauseSpeech() {
    if ('speechSynthesis' in window) window.speechSynthesis.pause();
    setSpeaking(false);
  }

  function stopSpeech() {
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    setSpeaking(false);
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 pb-20">
      <header className="rounded-3xl border border-amber-100 bg-amber-50 p-6 dark:border-amber-900/40 dark:bg-amber-900/10">
        <p className="text-sm font-black uppercase tracking-wider text-amber-700 dark:text-amber-300">CogniTutorLM voice scripts</p>
        <h1 className="mt-1 flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white"><Headphones className="h-8 w-8" /> Audio Overview</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Uses browser speechSynthesis when available. `audio_ready` means the script is ready for playback or future TTS.</p>
      </header>
      <div className="flex flex-wrap gap-2">
        {tabs.map(([label, type]) => (
          <button key={type} onClick={() => setActive(type)} className={`rounded-full px-4 py-2 text-sm font-bold ${active === type ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>
            {label}
          </button>
        ))}
      </div>
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black uppercase text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">audio_ready: {String(Boolean(voice.audio_ready ?? overview.audio_ready))}</span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-600 dark:bg-slate-800 dark:text-slate-300">duration: {String(voice.estimated_duration_sec || overview.estimated_duration_sec || 35)} sec</span>
          <div className="ml-auto flex gap-2">
            <button onClick={playSpeech} className="rounded-xl bg-emerald-600 p-2 text-white" title="Play"><Play className="h-4 w-4" /></button>
            <button onClick={pauseSpeech} className="rounded-xl bg-amber-500 p-2 text-white" title="Pause"><Pause className="h-4 w-4" /></button>
            <button onClick={stopSpeech} className="rounded-xl bg-slate-900 p-2 text-white" title="Stop"><Square className="h-4 w-4" /></button>
          </div>
        </div>
        <p className="whitespace-pre-wrap text-lg leading-8 text-slate-700 dark:text-slate-200">{script}</p>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {Object.entries(sections).map(([name, value]) => (
            <div key={name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900">
              <p className="text-xs font-black uppercase text-slate-500">{name.replaceAll('_', ' ')}</p>
              <p className="mt-1 text-sm text-slate-700 dark:text-slate-300">{String(value)}</p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs font-semibold text-slate-500">{speaking ? 'Playing in browser speechSynthesis.' : 'Ready.'}</p>
      </section>
    </div>
  );
}
