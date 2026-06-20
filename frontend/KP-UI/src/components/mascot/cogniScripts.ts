import { Difficulty } from '../../lib/types';

export type CogniMood = 'happy' | 'thinking' | 'warning' | 'celebrating' | 'revision' | 'encouragement' | 'confused' | 'success';

export const cogniScripts = {
  auth: {
    register: "Hi, I'm Cogni! Create your account and I'll guide your learning journey.",
    login: "Welcome back! Let's continue from where you left off.",
  },
  subject_selection: {
    first_time: "Choose one subject. I'll pick the first topic and guide you step by step.",
    python: "Great! We'll begin Python from the first concept.",
    selected: "Subject selected. I will keep every lesson, question, hint, and revision in this subject.",
  },
  teaching: {
    start_easy: "We'll start with the easy level so the basics are clear.",
    start_medium: "You cleared easy. Now let's build more confidence with medium.",
    start_hard: "Ready for hard level? Let's apply what you learned.",
  },
  teaching_view_switch: {
    analogy: "I'll explain it with an analogy.",
    code: "Let's look at a code example.",
    step: "Let's go step by step.",
    misconception: "Let's look at the common mistake.",
  },
  assessment_intro: {
    quick_check: "Now let's do a quick check.",
    after_teaching: "You learned the idea. Let's see how well it sticks.",
  },
  answer_correct: {
    easy: "Nice! You cleared easy. Let's try medium.",
    medium: "Great progress! Medium is done. Let's try hard.",
    hard: "Wow! You mastered this concept. The next topic is unlocked.",
  },
  answer_partial: "Almost there. A small revision will help.",
  answer_wrong: "No worries. This mistake tells us what to practice next.",
  repeated_mistake: "I noticed this pattern again, so I'll switch the view before asking a similar question.",
  difficulty_progression: {
    easy_to_medium: "Easy level complete. Moving to medium.",
    medium_to_hard: "Medium level complete. Moving to hard.",
    hard_to_next_concept: "Concept mastered. Let's unlock the next topic.",
  },
  returning_learner: {
    minutes: "Let's continue where you stopped.",
    hours: "Quick recap first, then we continue.",
    days: "Welcome back! Let's revise before moving ahead.",
    weeks: "It's been a while, so I'll guide you through a recovery revision.",
  },
  flashcard: { start: "Let's use flashcards to remember the key points." },
  mindmap: { start: "Here's a mind map to see the whole concept clearly." },
  notebook_memory: { saved: "I saved this to your notebook for future revision." },
  doubt: { start: "Ask me your doubt. I'll explain it using the lesson context." },
  hint: {
    general: "Here is a small hint from the current concept, not the full answer.",
    syntax: "Let's fix the syntax step by step.",
    output: "Let's trace the output line by line.",
  },
  rewards: {
    xp: "You earned XP! Keep going.",
    streak: "You're building a streak. Great consistency!",
    next_concept: "Concept cleared. Your next topic is ready.",
  },
  feedback: {
    correct: "Correct. I'll update your progress and move you forward.",
    partial: "Partly right. A quick revision will make the idea clearer.",
    wrong: "Not yet. I'll show the correct idea and choose a better next step.",
  },
  revision: {
    start: "Revision comes first when memory or confidence needs support.",
    flashcard: "Use this card to strengthen recall before the next check.",
    mindmap: "Use this map to connect definition, examples, and mistakes.",
  },
  xai: { reason: "Here's why I chose this activity for you." },
  encouragement: "You're doing steady work. Keep going one step at a time.",
  mock_mode: "I'm showing demo data because backend connection is unavailable.",
};

export function correctByDifficulty(difficulty?: Difficulty) {
  return cogniScripts.answer_correct[difficulty || 'easy'];
}
