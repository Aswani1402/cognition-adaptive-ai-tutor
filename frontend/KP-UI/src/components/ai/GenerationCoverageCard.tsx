import AIModuleCard from './AIModuleCard';

export default function GenerationCoverageCard({ coverage }: { coverage: any }) {
  return (
    <AIModuleCard title="Generation Coverage" status={coverage?.status || 'success'}>
      <p>Source: {coverage?.source || 'CogniTutorLM/RAG/fallback'}</p>
      <p>Categories: {(coverage?.categories || []).join(', ') || 'teaching, assessment, hints, feedback, revision'}</p>
      <p>Voice-ready scripts are text scripts, not audio/TTS.</p>
    </AIModuleCard>
  );
}
