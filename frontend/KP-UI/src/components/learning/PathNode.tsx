import { Check, Crown, Lock, Target } from 'lucide-react';
import clsx from 'clsx';
import { ConceptNode } from '../../lib/types';

export default function PathNode({ node, active, onSelect }: { node: ConceptNode; active: boolean; onSelect: () => void }) {
  const locked = node.status === 'locked';
  return (
    <button
      onClick={onSelect}
      disabled={locked}
      className={clsx(
        'grid h-20 w-20 place-items-center rounded-full text-white shadow-xl transition hover:scale-105',
        locked ? 'bg-gradient-to-b from-slate-300 to-slate-500 cursor-not-allowed' : node.status === 'mastered' ? 'bg-gradient-to-b from-emerald-400 to-emerald-600' : node.status === 'challenge' ? 'bg-gradient-to-b from-rose-400 to-rose-600' : 'bg-gradient-to-b from-sky-400 to-indigo-600',
        active && 'ring-4 ring-amber-300/50'
      )}
    >
      {locked ? <Lock className="h-6 w-6" /> : node.type === 'boss' ? <Crown className="h-6 w-6" /> : node.status === 'mastered' ? <Check className="h-6 w-6" /> : <Target className="h-6 w-6" />}
    </button>
  );
}
