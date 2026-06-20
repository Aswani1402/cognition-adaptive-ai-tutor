import { ConceptNode } from '../../lib/types';
import PathNode from './PathNode';

export default function ConceptPath({ nodes, activeId, onSelect }: { nodes: ConceptNode[]; activeId: string | null; onSelect: (node: ConceptNode) => void }) {
  return (
    <div className="relative space-y-8">
      <div className="pointer-events-none absolute bottom-8 left-1/2 top-8 w-3 -translate-x-1/2 rounded-full bg-slate-100 dark:bg-slate-800" />
      {nodes.map((node, index) => (
        <div key={node.id} className="relative z-10 flex justify-center" style={{ transform: `translateX(${index % 2 === 0 ? -52 : 52}px)` }}>
          <PathNode node={node} active={activeId === node.id} onSelect={() => onSelect(node)} />
        </div>
      ))}
    </div>
  );
}
