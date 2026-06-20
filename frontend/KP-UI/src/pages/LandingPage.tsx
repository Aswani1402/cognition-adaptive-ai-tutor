import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import type { ReactNode } from 'react';
import { ArrowRight, BookOpen, Brain, CheckCircle2, Code2, Flame, NotebookTabs, PlayCircle, Sparkles, Star, Trophy, Zap } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

const proof = [
  { label: 'Always know', value: 'what to learn next', color: 'text-sky-600 dark:text-sky-300' },
  { label: 'Practice with', value: 'instant feedback', color: 'text-amber-600 dark:text-amber-300' },
  { label: 'Review only', value: 'what you forget', color: 'text-emerald-600 dark:text-emerald-300' },
];

const pathNodes = [
  { label: 'Intro', state: 'done', x: 'left-4', color: 'from-[#58CC02] to-[#2FC26E]' },
  { label: 'Variables', state: 'now', x: 'left-24', color: 'from-[#21B8F9] to-[#198FE6]' },
  { label: 'Review', state: 'review', x: 'left-12', color: 'from-[#FF9E2C] to-[#F08800]' },
  { label: 'Boss', state: 'locked', x: 'left-32', color: 'from-[#7B61FF] to-[#6448EE]' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden bg-[#f8faf5] text-slate-950 dark:bg-[#0b1220] dark:text-slate-50">
      <header className="fixed left-0 right-0 top-0 z-50 border-b border-slate-200/70 bg-white/78 text-slate-950 shadow-sm shadow-slate-200/40 backdrop-blur-xl dark:border-white/20 dark:bg-[#0c2239]/70 dark:text-white dark:shadow-none">
        <div className="mx-auto flex h-18 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-10">
          <Link to="/" className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-[#21B8F9] to-[#2FC26E] shadow-lg shadow-sky-500/30">
              <Brain className="h-5 w-5 text-white" />
            </div>
            <p className="text-xl font-black tracking-tight">CogniTutor</p>
          </Link>

          <nav className="hidden items-center gap-8 text-sm font-semibold text-slate-600 md:flex dark:text-white/85">
            <a href="#approach" className="transition hover:text-sky-600 dark:hover:text-white">Approach</a>
            <a href="#experience" className="transition hover:text-sky-600 dark:hover:text-white">Experience</a>
            <a href="#demo-story" className="transition hover:text-sky-600 dark:hover:text-white">Demo story</a>
          </nav>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link to="/login" className="hidden text-sm font-semibold text-slate-600 hover:text-sky-600 sm:block dark:text-white/90 dark:hover:text-white">Log in</Link>
            <Link to="/register" className="rounded-full bg-[#13223F] px-4 py-2 text-sm font-bold text-white transition hover:scale-[1.02] dark:bg-white dark:text-[#0f2f4d]">
              Start Learning
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative min-h-[100svh] overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_12%_18%,rgba(33,184,249,0.26),transparent_38%),radial-gradient(circle_at_86%_12%,rgba(88,204,2,0.24),transparent_34%),radial-gradient(circle_at_58%_88%,rgba(255,213,74,0.28),transparent_42%),linear-gradient(135deg,#F8FAF5_0%,#ECFBF2_46%,#EAF7FF_100%)] dark:bg-[radial-gradient(circle_at_10%_15%,rgba(33,184,249,0.42),transparent_42%),radial-gradient(circle_at_85%_10%,rgba(123,97,255,0.38),transparent_40%),radial-gradient(circle_at_52%_90%,rgba(47,194,110,0.35),transparent_45%),linear-gradient(135deg,#0A1B31_0%,#0F2C44_52%,#112739_100%)]" />
          <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.12),rgba(248,250,245,0.82))] dark:bg-[linear-gradient(to_bottom,rgba(7,13,24,0.04),rgba(7,13,24,0.58))]" />
          <div className="absolute left-[6%] top-28 h-20 w-20 rounded-[2rem] bg-[#58CC02]/20 blur-xl dark:bg-[#58CC02]/15" />
          <div className="absolute right-[8%] top-28 h-28 w-28 rounded-full bg-[#21B8F9]/20 blur-2xl" />
          <div className="absolute bottom-16 left-[42%] h-24 w-24 rounded-full bg-[#FFD54A]/25 blur-2xl" />

          <div className="relative mx-auto grid min-h-[100svh] w-full max-w-7xl items-center gap-10 px-4 pb-16 pt-28 sm:px-6 lg:grid-cols-[minmax(0,590px)_1fr] lg:px-10">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: 'easeOut' }}
              className="max-w-2xl"
            >
              <p className="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-white/78 px-3 py-1 text-xs font-bold uppercase tracking-[0.16em] text-sky-700 shadow-sm dark:border-white/10 dark:bg-white/14 dark:text-white/90">
                <Sparkles className="h-3.5 w-3.5" /> Adaptive tutor for code learners
              </p>
              <h1 className="mt-5 max-w-3xl text-5xl font-black leading-[0.98] tracking-tight text-slate-950 dark:text-white sm:text-6xl lg:text-7xl">
                A learning path that reacts to how you think.
              </h1>
              <p className="mt-6 max-w-xl text-base leading-relaxed text-slate-700 dark:text-sky-100/90 sm:text-lg">
                CogniTutor blends guided progression, personal learning memory, and short daily coding practice into one adaptive tutor.
              </p>

              <div className="mt-8 flex flex-wrap gap-3">
                <Link to="/register" className="inline-flex items-center gap-2 rounded-2xl bg-[#21B8F9] px-6 py-3 text-sm font-black text-white shadow-lg shadow-sky-500/30 transition hover:-translate-y-0.5 hover:shadow-sky-500/40">
                  Start Learning <ArrowRight className="h-4 w-4" />
                </Link>
                <Link to="/demo" className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white/82 px-6 py-3 text-sm font-bold text-slate-800 shadow-sm backdrop-blur-sm transition hover:-translate-y-0.5 hover:bg-white dark:border-white/35 dark:bg-white/10 dark:text-white dark:hover:bg-white/20">
                  <PlayCircle className="h-4 w-4" /> View Demo
                </Link>
              </div>

              <div className="mt-8 grid max-w-xl grid-cols-3 gap-2 sm:gap-3">
                {proof.map((item, index) => (
                  <motion.div
                    key={item.label}
                    initial={{ opacity: 0, y: 14 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.45, delay: 0.25 + index * 0.08 }}
                    className="rounded-2xl border border-white/80 bg-white/72 p-3 shadow-sm backdrop-blur dark:border-white/10 dark:bg-white/10"
                  >
                    <p className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-500 dark:text-slate-300">{item.label}</p>
                    <p className={`mt-1 text-sm font-black ${item.color}`}>{item.value}</p>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            <HeroPlayground />
          </div>
        </section>

        <section id="approach" className="relative mx-auto grid w-full max-w-7xl gap-8 px-4 py-18 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-10">
          <div>
            <p className="text-xs font-black uppercase tracking-[0.14em] text-[#0EA5E9] dark:text-cyan-300">Why it works</p>
            <h2 className="mt-2 text-3xl font-black tracking-tight sm:text-4xl">It feels playful, but the system is doing serious tutoring work.</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <StoryCard icon={<Brain className="h-5 w-5" />} title="Chooses a teaching view" body="Explains with the format that fits the learner now: simpler, analogy, code, or step-by-step." tone="sky" />
            <StoryCard icon={<Flame className="h-5 w-5" />} title="Keeps momentum visible" body="XP, streaks, review prompts, and unlocks make progress feel concrete every day." tone="amber" />
            <StoryCard icon={<NotebookTabs className="h-5 w-5" />} title="Builds memory" body="Structured study notes preserve weak areas, sources, and revision plans." tone="emerald" />
            <StoryCard icon={<Code2 className="h-5 w-5" />} title="Practices with feedback" body="Run code, predict output, debug mistakes, and transfer ideas into new problems." tone="violet" />
          </div>
        </section>

        <section id="experience" className="mx-auto w-full max-w-7xl px-4 pb-20 sm:px-6 lg:px-10">
          <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.14em] text-emerald-600 dark:text-emerald-300">Product experience</p>
              <h2 className="mt-2 text-3xl font-black tracking-tight">Three familiar learning patterns, one tutor flow.</h2>
            </div>
            <Link to="/demo" className="inline-flex w-fit items-center gap-2 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:-translate-y-0.5 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
              Explore demo <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            <Feature title="Guided skill path" body="Unlocked nodes, review loops, boss challenges, XP, streaks, and clear next actions." accent="from-[#58CC02] to-[#21B8F9]" icon={<Trophy className="h-5 w-5" />} />
            <Feature title="Personal learning memory" body="Grounded notes, concept sources, summaries, revision plans, and tutor questions from your notebook." accent="from-[#21B8F9] to-[#7B61FF]" icon={<BookOpen className="h-5 w-5" />} />
            <Feature title="Short daily practice" body="Short sessions, varied quiz types, feedback cards, and approachable repetition for coding confidence." accent="from-[#FF9E2C] to-[#F24F75]" icon={<Zap className="h-5 w-5" />} />
          </div>
        </section>

        <section id="demo-story" className="border-y border-slate-200/80 bg-white/72 py-16 dark:border-slate-800 dark:bg-slate-950/40">
          <div className="mx-auto grid w-full max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-10">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.14em] text-violet-600 dark:text-violet-300">Demo ready</p>
              <h2 className="mt-2 text-3xl font-black tracking-tight">Show the full learner loop without a backend.</h2>
              <p className="mt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                The UI is mock-data driven, but the experience is real: selected teaching view, assessment, notebook memory, reward output, mistake review, and demo JSON panels.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {['Selected teaching view', 'Assessment JSON', 'Learning memory', 'Reward output', 'Mistake review', 'Demo panel'].map((item, index) => (
                <motion.div
                  key={item}
                  initial={{ opacity: 0, y: 10 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-80px' }}
                  transition={{ duration: 0.35, delay: index * 0.04 }}
                  className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900"
                >
                  <CheckCircle2 className="h-5 w-5 text-[#58CC02]" />
                  <span className="text-sm font-bold">{item}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden py-16">
          <div className="absolute inset-x-10 top-8 h-36 rounded-full bg-[#21B8F9]/10 blur-3xl dark:bg-[#21B8F9]/15" />
          <div className="relative mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-6 px-4 sm:flex-row sm:items-center sm:px-6 lg:px-10">
            <div>
              <h3 className="text-3xl font-black tracking-tight">Ready to see your personalized learning path?</h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Start with one concept. The tutor handles adaptation, practice, memory, and momentum.</p>
            </div>
            <div className="flex gap-3">
              <Link to="/register" className="rounded-xl bg-[#21B8F9] px-5 py-3 text-sm font-black text-white shadow-lg shadow-sky-500/25">Start Learning</Link>
              <Link to="/demo" className="rounded-xl border border-slate-300 bg-white px-5 py-3 text-sm font-bold text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">View Demo</Link>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function HeroPlayground() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96, y: 18 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.8, ease: 'easeOut', delay: 0.12 }}
      className="relative mx-auto hidden h-[570px] w-full max-w-[520px] lg:block"
    >
      <div className="absolute left-10 top-6 h-[500px] w-[330px] rounded-[2.25rem] border border-slate-200 bg-white/82 p-5 shadow-2xl shadow-sky-200/50 backdrop-blur-xl dark:border-white/15 dark:bg-white/8 dark:shadow-none">
        <div className="flex items-center justify-between">
          <p className="text-xs font-black uppercase tracking-[0.14em] text-slate-500 dark:text-cyan-100/90">Today's adaptive session</p>
          <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-black text-amber-700 dark:bg-amber-400/15 dark:text-amber-200">+20 XP</span>
        </div>
        <div className="relative mt-8 h-[310px]">
          <div className="absolute left-[86px] top-2 h-[285px] w-3 rounded-full bg-slate-100 dark:bg-slate-800" />
          {pathNodes.map((node, index) => (
            <motion.div
              key={node.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: 0.35 + index * 0.12 }}
              className={`absolute ${node.x}`}
              style={{ top: index * 78 }}
            >
              <div className={`grid h-16 w-16 place-items-center rounded-full bg-gradient-to-b ${node.color} text-white shadow-xl ${node.state === 'now' ? 'animate-[homeNode_2s_ease-in-out_infinite] ring-4 ring-sky-300/35' : ''}`}>
                {node.state === 'done' ? <CheckCircle2 className="h-7 w-7" /> : node.state === 'locked' ? <Star className="h-7 w-7" /> : <Code2 className="h-7 w-7" />}
              </div>
              <p className="mt-2 rounded-full bg-white px-2 py-1 text-center text-[11px] font-black text-slate-700 shadow-sm dark:bg-slate-900 dark:text-slate-200">{node.label}</p>
            </motion.div>
          ))}
        </div>
      </div>

      <motion.div
        animate={{ y: [0, -8, 0], rotate: [0, -1.5, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute right-0 top-24 w-64 rounded-[1.75rem] border border-slate-200 bg-white p-4 shadow-2xl shadow-emerald-200/50 dark:border-white/15 dark:bg-slate-950/90 dark:shadow-none"
      >
        <div className="mb-3 flex items-center gap-2 text-sm font-black"><NotebookTabs className="h-4 w-4 text-sky-500" /> Learning memory</div>
        <div className="space-y-2 text-xs text-slate-600 dark:text-slate-300">
          <p className="rounded-xl bg-sky-50 p-3 dark:bg-sky-900/20">Weakest skill: output prediction</p>
          <p className="rounded-xl bg-emerald-50 p-3 dark:bg-emerald-900/20">Revision: variables + string quotes</p>
          <p className="rounded-xl bg-amber-50 p-3 dark:bg-amber-900/20">Next: debug challenge</p>
        </div>
      </motion.div>

      <motion.div
        animate={{ y: [0, 7, 0], rotate: [0, 1.5, 0] }}
        transition={{ duration: 4.6, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute bottom-8 right-8 w-72 rounded-[1.75rem] border border-slate-800 bg-[#08111F] p-4 text-slate-100 shadow-2xl shadow-slate-400/30"
      >
        <div className="mb-3 flex items-center gap-2 text-sm font-black"><Code2 className="h-4 w-4 text-emerald-300" /> Code practice</div>
        <pre className="text-xs leading-relaxed text-slate-300"><code>{`name = "Asha"\nprint(name)\n# stdout: Asha`}</code></pre>
      </motion.div>

      <style>{`
        @keyframes homeNode {
          0%, 100% { transform: translateY(0) scale(1); }
          50% { transform: translateY(-5px) scale(1.05); }
        }
      `}</style>
    </motion.div>
  );
}

function StoryCard({ icon, title, body, tone }: { icon: ReactNode; title: string; body: string; tone: 'sky' | 'amber' | 'emerald' | 'violet' }) {
  const tones = {
    sky: 'bg-sky-50 text-sky-700 dark:bg-sky-900/20 dark:text-sky-200',
    amber: 'bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-200',
    emerald: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-200',
    violet: 'bg-violet-50 text-violet-700 dark:bg-violet-900/20 dark:text-violet-200',
  };

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-lg dark:border-slate-800 dark:bg-slate-900">
      <div className={`mb-4 grid h-11 w-11 place-items-center rounded-2xl ${tones[tone]}`}>{icon}</div>
      <h3 className="font-black tracking-tight">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{body}</p>
    </article>
  );
}

function Feature({ title, body, accent, icon }: { title: string; body: string; accent: string; icon: ReactNode }) {
  return (
    <article className="group relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-1 hover:shadow-xl dark:border-slate-800 dark:bg-slate-900">
      <div className={"absolute inset-x-0 top-0 h-1.5 bg-gradient-to-r " + accent} />
      <div className="mb-5 flex items-center justify-between">
        <div className={"grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br text-white shadow-lg " + accent}>{icon}</div>
        <ArrowRight className="h-5 w-5 text-slate-300 transition group-hover:translate-x-1 group-hover:text-sky-500" />
      </div>
      <h4 className="text-lg font-black tracking-tight">{title}</h4>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">{body}</p>
    </article>
  );
}



