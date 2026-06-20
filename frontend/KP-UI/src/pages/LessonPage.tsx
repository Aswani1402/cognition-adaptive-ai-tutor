import { Navigate, useParams } from 'react-router-dom';
import GuidedTutorJourney from '../components/session/GuidedTutorJourney';
import { useLearnerSession } from '../context/LearnerSessionContext';
import { getConceptDisplayName, subjectForConcept } from '../lib/concepts';

export default function LessonPage() {
  const { conceptId } = useParams();
  const session = useLearnerSession();
  const activeConcept = conceptId || session.current_concept_id;
  if (activeConcept && !session.active_subject) {
    session.setSubjectContext(subjectForConcept(activeConcept), activeConcept, getConceptDisplayName(activeConcept), 'easy');
  }
  if (!activeConcept) return <Navigate to="/subjects" replace />;
  return <GuidedTutorJourney conceptId={activeConcept} />;
}
