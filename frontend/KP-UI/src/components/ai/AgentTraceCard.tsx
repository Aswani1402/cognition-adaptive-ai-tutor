import AIModuleCard from './AIModuleCard';

export default function AgentTraceCard({ trace }: { trace: any }) {
  const stages = trace?.stages || [];
  return <AIModuleCard title="Agentic Orchestration Trace" status={trace?.status || 'success'}><p>{stages.map((s: any) => typeof s === 'string' ? s : `${s.name}: ${s.status}`).join(' -> ')}</p></AIModuleCard>;
}
