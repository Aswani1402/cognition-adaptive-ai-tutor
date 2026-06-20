import { MindMap } from '../../lib/types';
import { useEffect, useState } from 'react';

export default function MindMapView({ mindmap, selectedType }: { mindmap: MindMap; selectedType?: string }) {
  const [activeType, setActiveType] = useState(selectedType || 'concept_mindmap');
  const variants = mindmap.mindmap_variants || {};
  const types = mindmap.available_mindmap_types || Object.keys(variants);
  useEffect(() => {
    if (selectedType) setActiveType(selectedType);
  }, [selectedType]);
  const nodes = normalizeNodes({ ...mindmap, nodes: variants[activeType] || mindmap.nodes });
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="mb-5">
        <p className="text-xs font-black uppercase tracking-wider text-indigo-600 dark:text-indigo-300">Mindmap revision</p>
        <h3 className="text-2xl font-black text-slate-900 dark:text-white">{mindmap.title}</h3>
      </div>
      {types.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {types.map((type) => (
            <button key={type} onClick={() => setActiveType(type)} className={`rounded-full px-3 py-1 text-xs font-bold ${activeType === type ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-200'}`}>
              {type.replaceAll('_', ' ')}
            </button>
          ))}
        </div>
      )}
      <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto mb-5 max-w-sm rounded-3xl bg-indigo-600 px-8 py-5 text-center text-white shadow-xl shadow-indigo-600/20">
          <p className="text-xs font-black uppercase tracking-wider text-white/75">Core concept</p>
          <p className="text-2xl font-black">{mindmap.center}</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {nodes.map((node) => (
            <article key={node.id} className="min-h-40 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-950">
              <p className="mb-2 text-xs font-black uppercase tracking-wider" style={{ color: node.color }}>{node.title}</p>
              <BulletBody body={node.body} />
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function normalizeNodes(mindmap: MindMap) {
  const fallback = [
    { id: 'definition', title: 'Definition', body: `${mindmap.center} is the selected concept for this revision map.`, color: '#2563eb', x: 50, y: 16 },
    { id: 'examples', title: 'Examples', body: `Use one concrete ${mindmap.center} example and compare it with the expected result.`, color: '#16a34a', x: 82, y: 32 },
    { id: 'key-points', title: 'Key Points', body: `Define ${mindmap.center}, try a small example, and check the result.`, color: '#7c3aed', x: 78, y: 72 },
    { id: 'mistakes', title: 'Common Mistakes', body: `Do not apply ${mindmap.center} syntax without checking its meaning.`, color: '#e11d48', x: 22, y: 72 },
    { id: 'real-world', title: 'Real-world Use', body: `${mindmap.center} appears in practical learner tasks for the selected subject.`, color: '#0891b2', x: 18, y: 32 },
  ];
  const nodes = mindmap.nodes.length ? mindmap.nodes : fallback;
  const required = ['Definition', 'Examples', 'Key Points', 'Common Mistakes', 'Real-world Use', 'Next Concept'];
  const merged = required.map((title, index) => nodes.find((node) => node.title.toLowerCase() === title.toLowerCase()) || fallback[index % fallback.length] || nodes[index % nodes.length]);
  return merged.map((node, index) => ({
    ...node,
    title: required[index] || node.title,
    color: node.color.startsWith('#') ? node.color : ['#2563eb', '#16a34a', '#7c3aed', '#e11d48', '#0891b2', '#f59e0b'][index % 6],
    x: Math.max(12, Math.min(88, node.x || fallback[index % fallback.length].x)),
    y: Math.max(12, Math.min(88, node.y || fallback[index % fallback.length].y)),
  }));
}

function BulletBody({ body }: { body: string }) {
  const bullets = body
    .split(/\n|\. |; /)
    .map((item) => item.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)
    .slice(0, 3);
  return (
    <ul className="space-y-1 text-sm leading-6 text-slate-700 dark:text-slate-200">
      {(bullets.length ? bullets : [body]).map((item, idx) => <li key={idx}>- {item.length > 120 ? `${item.slice(0, 119).trim()}...` : item}</li>)}
    </ul>
  );
}
