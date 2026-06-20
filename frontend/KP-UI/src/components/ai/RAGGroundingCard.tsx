import AIModuleCard from './AIModuleCard';

export default function RAGGroundingCard({ rag }: { rag: any }) {
  return <AIModuleCard title="RAG Grounding" status={rag?.status}><p>Sources: {(rag?.source_sections || []).join(', ') || 'none'}</p><p>Safe to generate: {String(rag?.safe_to_generate ?? 'unknown')}</p></AIModuleCard>;
}
