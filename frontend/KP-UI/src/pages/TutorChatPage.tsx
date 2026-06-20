import TutorChatPanel from '../components/chat/TutorChatPanel';

export default function TutorChatPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-5 pb-20">
      <header>
        <p className="text-sm font-bold uppercase tracking-wider text-sky-600 dark:text-sky-300">Tutor chat</p>
        <h1 className="text-3xl font-black">Full Tutor Chat</h1>
      </header>
      <TutorChatPanel fullPage />
    </div>
  );
}

