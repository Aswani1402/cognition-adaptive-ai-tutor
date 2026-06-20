import AIModuleCard from './AIModuleCard';

export default function KTBehaviourCard({ kt, behaviour }: { kt: any; behaviour: any }) {
  return <AIModuleCard title="KT + Behaviour" status={kt?.status || behaviour?.status}><p>Mastery: {kt?.mastery_score ?? 'pending'} ({kt?.mastery_label || 'new'})</p><p>Behaviour risk: {behaviour?.behaviour_risk ?? 0}</p></AIModuleCard>;
}
