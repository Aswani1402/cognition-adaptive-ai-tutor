import confetti from 'canvas-confetti';
import { useEffect } from 'react';

export default function ConfettiEffect({ fire }: { fire: boolean }) {
  useEffect(() => {
    if (!fire) return;
    confetti({ particleCount: 90, spread: 70, origin: { y: 0.7 }, colors: ['#58CC02', '#1CB0F6', '#FFC800', '#CE82FF'] });
    confetti({ particleCount: 45, spread: 45, angle: 60, origin: { x: 0, y: 0.75 }, colors: ['#58CC02', '#1CB0F6', '#FFC800'] });
    confetti({ particleCount: 45, spread: 45, angle: 120, origin: { x: 1, y: 0.75 }, colors: ['#58CC02', '#1CB0F6', '#FFC800'] });
  }, [fire]);

  return null;
}
