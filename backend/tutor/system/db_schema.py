import sqlite3
import os

def ensure_tables(db_path: str) -> None:
    """
    Creates the required Logging & Feedback tables according to the spec.
    Drops existing incompatible tables to ensure schema compliance.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Drop existing tables that might have incompatible schemas from previous versions
    tables_to_reset = [
        "quiz_results", 
        "learning_path_log", 
        "teaching_strategy_log", 
        "xai_log", 
        "behavior_state"
    ]
    
    for table in tables_to_reset:
        cur.execute(f"DROP TABLE IF EXISTS {table}")

    # 1. Table for quiz results
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        concept_id TEXT,
        question_id TEXT,
        selected_option TEXT,
        is_correct INTEGER,
        confidence INTEGER,
        time_taken_sec REAL,
        attempt_no INTEGER,
        timestamp TEXT
    )""")

    # 2. Table for learning path logging
    cur.execute("""
    CREATE TABLE IF NOT EXISTS learning_path_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        from_concept_id TEXT,
        to_concept_id TEXT,
        action TEXT,
        reason_json TEXT,
        timestamp TEXT
    )""")

    # 3. Table for teaching strategy logging
    cur.execute("""
    CREATE TABLE IF NOT EXISTS teaching_strategy_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        concept_id TEXT,
        strategy TEXT,
        strategy_source TEXT,
        timestamp TEXT
    )""")

    # 4. Table for XAI explanations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS xai_log (
        xai_id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        concept_id TEXT,
        decision_type TEXT,
        explanation_text TEXT,
        evidence_json TEXT,
        timestamp TEXT
    )""")

    # 5. Table for behavior tracking
    cur.execute("""
    CREATE TABLE IF NOT EXISTS behavior_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        behavior_json TEXT,
        timestamp TEXT
    )""")

    conn.commit()
    conn.close()
    print(f"✅ Tables initialized for: {os.path.basename(db_path)}")

if __name__ == "__main__":
    # Subject-specific databases found in the directory
    db_files = [
        "data_structures.db",
        "database_sql.db",
        "git_version_control.db",
        "html_web_basics.db",
        "python_learning.db"
    ]
    
    print("--- Starting Multi-Database Migration ---")
    for db_file in db_files:
        if os.path.exists(db_file):
            ensure_tables(db_file)
        else:
            print(f"⚠️ Skipping {db_file} (file not found)")
    print("--- Migration Complete ---")