import sqlite3
import json
import re
from datetime import datetime
from pathlib import Path


# ==============================
# PATH SETUP
# ==============================
BASE_DIR = Path(__file__).resolve().parents[2]
CORE_DATA_DIR = BASE_DIR / "Updated_DB"
TUTOR_DB_PATH = CORE_DATA_DIR / "tutor.db"


def get_db_connection(db_path):
    return sqlite3.connect(str(db_path))


# ==============================
# NORMALIZE TEXT
# ==============================
def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s=]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


# ==============================
# GET CONCEPT MAPPING
# ==============================
def get_concept_mapping(system_concept_id):
    conn = get_db_connection(TUTOR_DB_PATH)
    cursor = conn.cursor()

    query = """
    SELECT system_concept_id, content_concept_id, domain, source_db
    FROM concept_id_map
    WHERE system_concept_id = ?
    """

    cursor.execute(query, (system_concept_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "system_concept_id": row[0],
        "content_concept_id": row[1],
        "domain": row[2],
        "source_db": row[3]
    }


# ==============================
# FETCH CONCEPT DETAILS
# ==============================
def fetch_concept_details(content_concept_id, source_db):
    db_path = CORE_DATA_DIR / source_db

    if not db_path.exists():
        return "", ""

    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    concept_name = ""
    reference_text = ""

    try:
        # Get concept name + description
        cursor.execute("""
        SELECT name, description
        FROM concepts
        WHERE concept_id = ?
        """, (content_concept_id,))

        row = cursor.fetchone()

        if row:
            concept_name = row[0]
            if row[1]:
                reference_text += row[1] + " "

        # Try teaching content
        try:
            cursor.execute("""
            SELECT *
            FROM teaching_content
            WHERE concept_id = ?
            """, (content_concept_id,))

            rows = cursor.fetchall()

            for r in rows:
                for val in r:
                    if isinstance(val, str):
                        reference_text += val + " "

        except:
            pass

    except:
        pass

    conn.close()
    return concept_name, reference_text


# ==============================
# BUILD KEY POINTS
# ==============================
def build_expected_key_points(concept_name):

    concept_name = concept_name.lower()

    predefined = {
        "variables": [
            "stores a value",
            "has a name",
            "used in program",
            "value can change",
            "example provided"
        ],
        "loops": [
            "repeats code",
            "for or while",
            "iteration",
            "reduces repetition"
        ],
        "conditionals": [
            "decision making",
            "if else",
            "condition",
            "controls flow"
        ],
        "functions": [
            "reusable code",
            "performs task",
            "input",
            "output"
        ]
    }

    return predefined.get(concept_name, ["basic understanding"])


# ==============================
# MATCH KEY POINT (IMPROVED)
# ==============================
def match_key_point(response, key_point):

    rules = {
        "stores a value": ["store", "value"],
        "has a name": ["name", "variable"],
        "used in program": ["program", "code"],
        "value can change": ["change", "update"],
        "example provided": ["=", "example"],
        "repeats code": ["repeat", "loop"],
        "for or while": ["for", "while"],
        "iteration": ["iteration", "iterate"],
        "reduces repetition": ["repeat"],
        "decision making": ["decision"],
        "if else": ["if", "else"],
        "condition": ["condition"],
        "controls flow": ["flow"],
        "reusable code": ["function", "reusable"],
        "performs task": ["task"],
        "input": ["input", "parameter"],
        "output": ["output", "return"]
    }

    keywords = rules.get(key_point, key_point.split())

    return any(k in response for k in keywords)


# ==============================
# SAVE RESULT TO DB 🔥
# ==============================
def save_explanation_result(result):
    conn = get_db_connection(TUTOR_DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS explanation_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id TEXT,
        system_concept_id TEXT,
        content_concept_id TEXT,
        response_text TEXT,
        score REAL,
        coverage_ratio REAL,
        matched_key_points TEXT,
        missing_key_points TEXT,
        quality_label TEXT,
        feedback TEXT,
        created_at TEXT
    )
    """)

    # Insert
    cursor.execute("""
    INSERT INTO explanation_results (
        learner_id,
        system_concept_id,
        content_concept_id,
        response_text,
        score,
        coverage_ratio,
        matched_key_points,
        missing_key_points,
        quality_label,
        feedback,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["learner_id"],
        result["system_concept_id"],
        result["content_concept_id"],
        result["response_text"],
        result["score"],
        result["coverage_ratio"],
        json.dumps(result["matched_key_points"]),
        json.dumps(result["missing_key_points"]),
        result["quality_label"],
        result["feedback"],
        result["evaluated_at"]
    ))

    conn.commit()
    conn.close()


# ==============================
# MAIN FUNCTION
# ==============================
def evaluate_explanation(learner_id, system_concept_id, response_text):

    # Handle empty response
    if not response_text or response_text.strip() == "":
        return {
            "status": "failed",
            "message": "Empty response"
        }

    mapping = get_concept_mapping(system_concept_id)

    if not mapping:
        return {"status": "failed", "message": "Concept mapping not found"}

    content_concept_id = mapping["content_concept_id"]
    source_db = mapping["source_db"]

    concept_name, reference_text = fetch_concept_details(
        content_concept_id, source_db
    )

    if not concept_name:
        concept_name = "Unknown Concept"

    expected_points = build_expected_key_points(concept_name)

    normalized_response = normalize_text(response_text)

    matched = []
    missing = []

    for point in expected_points:
        if match_key_point(normalized_response, point):
            matched.append(point)
        else:
            missing.append(point)

    total = len(expected_points)
    score = round(len(matched) / total, 2) if total > 0 else 0

    if score >= 0.8:
        quality = "good"
    elif score >= 0.5:
        quality = "partial"
    else:
        quality = "weak"

    # Feedback
    if quality == "good":
        feedback = f"Good explanation of {concept_name}. You covered most key ideas."
    elif quality == "partial":
        feedback = f"Your explanation is partially correct. Improve: {', '.join(missing)}"
    else:
        feedback = f"Your explanation is weak. Focus on: {', '.join(missing)}"

    result = {
        "status": "success",
        "learner_id": learner_id,
        "system_concept_id": system_concept_id,
        "content_concept_id": content_concept_id,
        "concept_name": concept_name,
        "score": score,
        "coverage_ratio": score,
        "matched_key_points": matched,
        "missing_key_points": missing,
        "quality_label": quality,
        "feedback": feedback,
        "evaluated_at": datetime.now().isoformat(),
        "response_text": response_text
    }

    # 🔥 SAVE TO DB
    save_explanation_result(result)

    return result


# ==============================
# TEST
# ==============================
if __name__ == "__main__":

    test_cases = [
        ("1", "A variable stores value like x = 10"),
        ("2", "Loops repeat code using for loop"),
        ("3", "If else is used for decision making"),
        ("1", "")
    ]

    for concept_id, response in test_cases:
        print("\n==============================")
        print(f"Testing Concept ID: {concept_id}")

        result = evaluate_explanation(
            learner_id="14",
            system_concept_id=concept_id,
            response_text=response
        )

        print(json.dumps(result, indent=2))