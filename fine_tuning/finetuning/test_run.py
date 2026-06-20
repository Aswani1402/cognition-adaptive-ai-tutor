from datetime import datetime
from tutor.system.feedback_loop import handle_quiz_feedback
from tutor.system.db_schema import ensure_tables

# --- Mocking Teammate's Module Logic ---

class MockKTEngine:
    def update_interaction(self, learner_id, concept_id, correct):
        print(f"[KT] Interaction updated for {learner_id} on {concept_id}. Correct: {correct}")

    def predict_mastery(self, learner_id):
        # Simulated mastery prediction
        return {"P1": 0.82, "P2": 0.47}

class MockBehaviorModel:
    def predict(self, features):
        print(f"[Behavior] Inferred behavior from features: {features}")
        return {"label": "hesitant", "confidence": 0.71}

def mock_integrate_knowledge_state(learner_id, mastery_vector, behavior_state, meta):
    print(f"[Integrator] Creating unified state for {learner_id}")
    return {
        "mastery": mastery_vector,
        "behavior": behavior_state,
        "last_interaction": meta.get("last_attempt", {}).get("timestamp")
    }

def mock_save_knowledge_state(learner_id, state):
    print(f"[Module 1] Knowledge state saved for {learner_id}: {state}")

# --- Test Execution ---

DB_PATH = "python_learning.db"

# 1. Ensure tables exist
ensure_tables(DB_PATH)

# 2. Define a mock quiz attempt
mock_attempt = {
    "learner_id": "L01",
    "concept_id": "P2",
    "question_id": "Q2_03",
    "selected_option": "B",
    "is_correct": 1,
    "confidence": 4,
    "time_taken_sec": 18.4,
    "attempt_no": 1,
    "hints_used": 0,
    "timestamp": datetime.now().isoformat()
}

# 3. Create mock instances
kt_engine = MockKTEngine()
behavior_model = MockBehaviorModel()

print("\n--- Starting End-to-End Feedback Loop Test ---")

# 4. Run the handle_quiz_feedback loop
output = handle_quiz_feedback(
    db_path=DB_PATH,
    attempt=mock_attempt,
    kt_engine=kt_engine,
    behavior_model=behavior_model,
    integrate_knowledge_state=mock_integrate_knowledge_state,
    save_knowledge_state=mock_save_knowledge_state
)

# 5. Verify Output
print("\n--- Test Results ---")
import json
print(json.dumps(output, indent=2))

if output.get("knowledge_state_saved") and output.get("quiz_logged"):
    print("\n✅ SUCCESS: Feedback loop processed and persisted correctly.")
    print("You can now connect your teammate's real modules by passing them into handle_quiz_feedback.")