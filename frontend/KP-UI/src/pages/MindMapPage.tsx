import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getMindmap } from '../lib/api';
import { MindMap } from '../lib/types';
import MindMapView from '../components/visual/MindMapView';
import CogniGuideCard from '../components/mascot/CogniGuideCard';
import { getCogniMessage } from '../components/mascot/useCogniGuide';
import { useLearnerSession } from '../context/LearnerSessionContext';

export default function MindMapPage() {
  const { conceptId } = useParams();
  const [mindmap, setMindmap] = useState<MindMap | null>(null);
  const [variant, setVariant] = useState('Concept Map');
  const session = useLearnerSession();

  useEffect(() => {
    const activeConcept = conceptId || session.current_concept_id || 'P1';
    if (activeConcept) getMindmap(activeConcept, session.active_subject).then(setMindmap);
  }, [conceptId, session.active_subject, session.current_concept_id]);

  if (!mindmap) {
    return <div className="grid h-[45vh] place-items-center text-slate-500">This content is being prepared. Showing saved learning content instead.</div>;
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6 pb-20">
      <CogniGuideCard {...getCogniMessage({ page: 'mindmap', activityType: 'mindmap_revision' })} compact />
      <div className="flex flex-wrap gap-2">
        {['Concept Map', 'Comparison Map', 'Revision Map', 'Misconception Map'].map((item) => (
          <button key={item} onClick={() => setVariant(item)} className={`rounded-full px-4 py-2 text-sm font-bold ${variant === item ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900' : 'border border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>{item}</button>
        ))}
      </div>
      <p className="text-sm font-semibold text-slate-500">Showing {variant}. Nodes are built from definition, key points, examples, mistakes, real-world use, and next step when provided by CogniTutorLM.</p>
      <MindMapView mindmap={mindmap} selectedType={mindmapType(variant)} />
    </div>
  );
}

function mindmapType(label: string) {
  if (label === 'Comparison Map') return 'comparison_mindmap';
  if (label === 'Revision Map') return 'revision_mindmap';
  if (label === 'Misconception Map') return 'misconception_mindmap';
  return 'concept_mindmap';
}
