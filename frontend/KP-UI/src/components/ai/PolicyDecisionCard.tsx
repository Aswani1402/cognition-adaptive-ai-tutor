import AIModuleCard from './AIModuleCard';

export default function PolicyDecisionCard({ policy }: { policy: any }) {
  return <AIModuleCard title="Policy/RL Decision" status={policy?.status}><p>Action: {policy?.policy_action || 'pending'}</p><p>Safe decision: {policy?.final_safe_decision || 'pending'}</p></AIModuleCard>;
}
