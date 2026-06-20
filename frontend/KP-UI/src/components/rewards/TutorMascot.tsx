import clsx from 'clsx';

type MascotEmotion = 'happy' | 'encouraging' | 'supportive';
type MascotEvent =
  | 'correct_answer'
  | 'partial_answer'
  | 'wrong_attempt'
  | 'lesson_completed'
  | 'quiz_completed'
  | 'concept_mastered'
  | 'concept_unlocked'
  | 'streak_maintained'
  | 'xp_gained';

const eventMessages: Record<MascotEvent, string> = {
  correct_answer: 'Great job! You predicted the output correctly.',
  partial_answer: 'Almost there - let us try a simpler example.',
  wrong_attempt: 'Good attempt. Let us retry together with one hint.',
  lesson_completed: 'Strong work! Ready for a challenge?',
  quiz_completed: 'Nice debugging! You found the mistake.',
  concept_mastered: 'You cleared this concept. Next one unlocked!',
  concept_unlocked: 'New concept unlocked. Your path just expanded.',
  streak_maintained: 'Your streak is alive today!',
  xp_gained: 'XP gained. Progress saved and momentum rising.',
};

const emotionTone = {
  happy: {
    body: '#2E95D8',
    bodyDeep: '#156CB8',
    shell: '#13223F',
    shellLight: '#20345E',
    face: '#53B8ED',
    belly: '#57BCEB',
    cheek: '#FF7B78',
    bubble: 'bg-sky-50 border-sky-200 text-sky-950 dark:bg-sky-900/20 dark:border-sky-900/40 dark:text-sky-100',
  },
  encouraging: {
    body: '#319BE0',
    bodyDeep: '#176FB9',
    shell: '#123055',
    shellLight: '#1F4B79',
    face: '#63C3F0',
    belly: '#6BC6EF',
    cheek: '#FF8A8A',
    bubble: 'bg-cyan-50 border-cyan-200 text-cyan-950 dark:bg-cyan-900/20 dark:border-cyan-900/40 dark:text-cyan-100',
  },
  supportive: {
    body: '#3CA3E6',
    bodyDeep: '#2173BB',
    shell: '#1F3154',
    shellLight: '#2B4C78',
    face: '#7DCEF4',
    belly: '#7DD0F2',
    cheek: '#FFA0A0',
    bubble: 'bg-amber-50 border-amber-200 text-amber-950 dark:bg-amber-900/20 dark:border-amber-900/40 dark:text-amber-100',
  },
} as const;

const positiveEvents: MascotEvent[] = [
  'correct_answer',
  'lesson_completed',
  'quiz_completed',
  'concept_mastered',
  'concept_unlocked',
  'streak_maintained',
  'xp_gained',
];

export default function TutorMascot({
  emotion = 'happy',
  event,
  message,
  compact = false,
  className,
}: {
  emotion?: MascotEmotion;
  event?: MascotEvent;
  message?: string;
  compact?: boolean;
  className?: string;
}) {
  const tone = emotionTone[emotion];
  const activeEvent = event || 'concept_mastered';
  const copy = message || eventMessages[activeEvent];
  const showPositiveReaction = Boolean(event && positiveEvents.includes(event) && emotion !== 'supportive');
  const showEncouragingReaction = event === 'partial_answer';
  const showSupportiveReaction = event === 'wrong_attempt' || emotion === 'supportive';
  const mascotAnimation = showPositiveReaction
    ? 'nova-mascot--cheer'
    : showEncouragingReaction
      ? 'nova-mascot--nod'
      : showSupportiveReaction
        ? 'nova-mascot--support'
        : 'nova-mascot--breathe';

  return (
    <div className={clsx('rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900', className)}>
      <div className={clsx('flex items-center gap-4', compact && 'gap-3')}>
        <div className={clsx('relative shrink-0', compact ? 'h-28 w-28' : 'h-40 w-40')}>
          <svg viewBox="0 0 220 220" className="h-full w-full animate-[novaFloat_3.6s_ease-in-out_infinite]" aria-hidden>
            <defs>
              <linearGradient id="novaShell" x1="54" y1="32" x2="168" y2="192">
                <stop offset="0%" stopColor={tone.shellLight} />
                <stop offset="100%" stopColor={tone.shell} />
              </linearGradient>
              <linearGradient id="novaFace" x1="74" y1="58" x2="146" y2="148">
                <stop offset="0%" stopColor="#FFFBEA" />
                <stop offset="100%" stopColor="#F2E7C5" />
              </linearGradient>
              <radialGradient id="novaEye" cx="35%" cy="28%" r="70%">
                <stop offset="0%" stopColor="#5B6B86" />
                <stop offset="70%" stopColor="#101A32" />
                <stop offset="100%" stopColor="#07102B" />
              </radialGradient>
              <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <ellipse
              className={clsx('nova-shadow', showPositiveReaction && 'nova-shadow--cheer')}
              cx="110"
              cy="195"
              rx="48"
              ry="10"
              fill="#0f172a"
              opacity="0.14"
            />

            {(showPositiveReaction || showEncouragingReaction) && (
              <g className="animate-[novaSparkle_2.8s_ease-in-out_infinite]" opacity="0.95">
                <path d="M43 50 L48 61 L59 66 L48 71 L43 82 L38 71 L27 66 L38 61Z" fill="#62E5D1" />
                <path d="M176 46 L180 55 L189 59 L180 63 L176 72 L172 63 L163 59 L172 55Z" fill="#6F86FF" />
                <path d="M170 90 L173 96 L179 99 L173 102 L170 108 L167 102 L161 99 L167 96Z" fill="#FBBF24" />
              </g>
            )}

            <g
              className={clsx('nova-mascot', mascotAnimation)}
            >
              <path
                className={clsx('nova-wing nova-wing-left', showPositiveReaction && 'nova-wing-left--cheer')}
                d="M39 126 C28 132 27 151 40 160 C52 168 66 159 68 143 C58 143 48 137 39 126Z"
                fill={tone.shell}
                opacity="0.92"
              />
              <path
                className={clsx('nova-wing nova-wing-right', showPositiveReaction && 'nova-wing-right--cheer')}
                d="M181 126 C192 132 193 151 180 160 C168 168 154 159 152 143 C162 143 172 137 181 126Z"
                fill={tone.shell}
                opacity="0.92"
              />

              <path
                d="M48 99 C48 56 75 34 110 34 C145 34 172 56 172 99 L172 128 C172 169 146 191 110 191 C74 191 48 169 48 128Z"
                fill="url(#novaShell)"
              />
              <path
                d="M61 73 C70 49 92 38 110 38 C128 38 150 49 159 73 C148 67 132 64 110 64 C88 64 72 67 61 73Z"
                fill={tone.body}
                opacity="0.2"
              />

              <path d="M67 87 C73 63 94 55 110 60 C126 55 147 63 153 87 C163 125 142 154 110 158 C78 154 57 125 67 87Z" fill="url(#novaFace)" />
              <path d="M86 152 C93 166 101 173 110 173 C119 173 127 166 134 152 C130 179 120 190 110 190 C100 190 90 179 86 152Z" fill="#FFF2D2" opacity="0.72" />

              <circle cx="88" cy="101" r="14" fill="#FFFFFF" />
              <circle cx="132" cy="101" r="14" fill="#FFFFFF" />
              <ellipse className={showEncouragingReaction ? 'nova-eye--encourage' : undefined} cx="88" cy="103" rx="7" ry="7" fill="url(#novaEye)">
                <animate
                  attributeName="ry"
                  dur="4.8s"
                  repeatCount="indefinite"
                  values="7;7;1.2;7;7"
                  keyTimes="0;0.46;0.5;0.54;1"
                />
              </ellipse>
              <ellipse className={showEncouragingReaction ? 'nova-eye--encourage' : undefined} cx="132" cy="103" rx="7" ry="7" fill="url(#novaEye)">
                <animate
                  attributeName="ry"
                  dur="4.8s"
                  repeatCount="indefinite"
                  values="7;7;1.2;7;7"
                  keyTimes="0;0.46;0.5;0.54;1"
                />
              </ellipse>
              <circle cx="85" cy="98" r="2.5" fill="#FFFFFF" />
              <circle cx="129" cy="98" r="2.5" fill="#FFFFFF" />

              <ellipse cx="76" cy="120" rx="5" ry="8" fill={tone.cheek} opacity="0.6" transform="rotate(58 76 120)" />
              <ellipse cx="144" cy="120" rx="5" ry="8" fill={tone.cheek} opacity="0.6" transform="rotate(-58 144 120)" />

              <path d="M110 109 L122 121 L110 130 L98 121Z" fill="#F59E0B" />

              <path d="M85 187 C78 191 75 197 82 200 H102 C105 194 98 188 85 187Z" fill="#F59E0B" />
              <path d="M135 187 C142 191 145 197 138 200 H118 C115 194 122 188 135 187Z" fill="#F59E0B" />
            </g>
          </svg>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-[11px] font-black uppercase tracking-[0.16em] text-slate-500">Nova - Tutor Mascot</p>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-black uppercase text-slate-500 dark:bg-slate-800 dark:text-slate-300">
              {emotion}
            </span>
          </div>
          <div className={clsx('mt-2 rounded-2xl border px-3 py-2.5 text-sm font-medium leading-relaxed', tone.bubble)}>{copy}</div>
        </div>
      </div>

      <style>{`
        .nova-mascot,
        .nova-wing,
        .nova-shadow,
        .nova-eye--encourage {
          transform-box: fill-box;
        }
        .nova-mascot {
          transform-origin: center 58%;
          will-change: transform;
        }
        .nova-wing-left {
          transform-origin: 78% 55%;
          will-change: transform;
        }
        .nova-wing-right {
          transform-origin: 22% 55%;
          will-change: transform;
        }
        .nova-shadow {
          transform-origin: center;
          will-change: transform, opacity;
        }
        .nova-mascot--breathe {
          animation: novaBreathe 3.8s ease-in-out infinite;
        }
        .nova-mascot--cheer {
          animation: novaCheer 1.55s cubic-bezier(.2, 1.25, .35, 1) infinite;
        }
        .nova-mascot--nod {
          animation: novaNod 2.2s ease-in-out infinite;
        }
        .nova-mascot--support {
          animation: novaSupport 2.6s ease-in-out infinite;
        }
        .nova-wing-left--cheer {
          animation: novaWingLeft 1.55s ease-in-out infinite;
        }
        .nova-wing-right--cheer {
          animation: novaWingRight 1.55s ease-in-out infinite;
        }
        .nova-shadow--cheer {
          animation: novaShadowCheer 1.55s ease-in-out infinite;
        }
        .nova-eye--encourage {
          animation: novaEyesEncourage 2.2s ease-in-out infinite;
        }
        @keyframes novaFloat {
          0%, 100% { transform: translateY(0) rotate(0deg); }
          50% { transform: translateY(-4px) rotate(-1deg); }
        }
        @keyframes novaBreathe {
          0%, 100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-2px) scale(1.018); }
        }
        @keyframes novaCheer {
          0%, 100% { transform: translateY(0) scale(1) rotate(0deg); }
          18% { transform: translateY(-12px) scale(1.055) rotate(-2deg); }
          34% { transform: translateY(2px) scale(0.985) rotate(1.5deg); }
          52% { transform: translateY(-6px) scale(1.025) rotate(0deg); }
          72% { transform: translateY(0) scale(1) rotate(0deg); }
        }
        @keyframes novaNod {
          0%, 100% { transform: translateY(0) rotate(0deg) scale(1); }
          32% { transform: translateY(5px) rotate(3deg) scale(1.01); }
          62% { transform: translateY(-2px) rotate(-2deg) scale(1); }
        }
        @keyframes novaSupport {
          0%, 100% { transform: translateX(0) rotate(0deg) scale(1); }
          32% { transform: translateX(-5px) rotate(-3deg) scale(1.006); }
          66% { transform: translateX(5px) rotate(3deg) scale(1.006); }
        }
        @keyframes novaWingLeft {
          0%, 100% { transform: rotate(0deg); }
          18% { transform: rotate(-22deg) translateY(-4px); }
          36% { transform: rotate(8deg); }
          54% { transform: rotate(-14deg) translateY(-2px); }
        }
        @keyframes novaWingRight {
          0%, 100% { transform: rotate(0deg); }
          18% { transform: rotate(22deg) translateY(-4px); }
          36% { transform: rotate(-8deg); }
          54% { transform: rotate(14deg) translateY(-2px); }
        }
        @keyframes novaShadowCheer {
          0%, 100% { transform: scaleX(1); opacity: 0.14; }
          18% { transform: scaleX(0.72); opacity: 0.08; }
          34% { transform: scaleX(1.08); opacity: 0.18; }
          52% { transform: scaleX(0.86); opacity: 0.11; }
        }
        @keyframes novaEyesEncourage {
          0%, 100% { transform: translateY(0); }
          35% { transform: translateY(1.5px); }
          65% { transform: translateY(-1px); }
        }
        @keyframes novaSparkle {
          0%, 100% { opacity: 0.25; transform: translateY(4px) scale(0.86) rotate(0deg); }
          24% { opacity: 1; transform: translateY(-3px) scale(1.08) rotate(8deg); }
          48% { opacity: 0.6; transform: translateY(1px) scale(0.94) rotate(-4deg); }
          72% { opacity: 1; transform: translateY(-2px) scale(1.02) rotate(5deg); }
        }
      `}</style>
    </div>
  );
}
