import sqlite3

from concept_dependency import run_dependency_module


def get_concept_details(db_path, concept_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT name, difficulty, description
        FROM concepts
        WHERE concept_id = ?
        """

        cursor.execute(query, (concept_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            json_mapping["concept_name"] = row[0]
            json_mapping["difficulty"] = row[1]
            json_mapping["description"] = row[2]
        else:
            for key in json_mapping: 
                json_mapping[key] = "None"
            json_mapping['status'] = "Failed"

    except Exception as e:
        return {"error": str(e)}

def get_content_concept_id_and_domain_and_db(db_path,system_concept_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        Select content_concept_id,domain,source_db from concept_id_map
        where system_concept_id = ?
        """
        
        cursor.execute(query, (system_concept_id,))
        row = cursor.fetchone()

        if not row:
            for key in json_mapping:
                json_mapping[key] = "None"
            json_mapping['status'] = "Failed"
            return

        conn.close()

        json_mapping["content_concept_id"] = row[0]
        json_mapping["domain"] = row[1]
        json_mapping["source_db"] = row[2]

    except Exception as e:
        print(f"Error fetcing content_concept_id {e}")

def get_teaching_content(db_path, concept_id, strategy_type, content_type, difficulty):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT *
        FROM teaching_content
        WHERE concept_id = ?
        AND strategy = ?
        AND content_type = ?
        AND difficulty = ?
        LIMIT 1
        """

        cursor.execute(query, (concept_id, strategy_type, content_type, difficulty))
        row = cursor.fetchone()

        conn.close()
        return row

    except Exception as e:
        print("Error fetching teaching content:", e)
        return None

# json_mapping["system_concept_id"] = input("Enter the System Concept ID : ")

tutor_DB = "Updated_DB/tutor.db"

DB_PATHS = [
    "Updated_DB/python_learning.db",
    "Updated_DB/database_sql.db",
    "Updated_DB/html_web_basics.db",
    "Updated_DB/git_version_control.db",
    "Updated_DB/data_structures.db",
]
result = run_dependency_module(
    tutor_db=tutor_DB,
    db_paths=DB_PATHS,
    learner_id="387766"
)

print("\nUnlocked:", result["unlocked_concepts"])

for concept in result["unlocked_concepts"]:
    json_mapping = {
        "system_concept_id" : "",
        "content_concept_id" : "",
        "domain":"",
        "concept_name" : "",
        "description" : "",
        "teaching_strategy" : {},
        "difficulty" : "",
        # "content_type" : "",
        # "instruction" : "",
        "source_db" : "",
        "status": "" 
    }

    json_mapping["system_concept_id"] = concept
    get_content_concept_id_and_domain_and_db(f"Updated_DB/tutor.db",json_mapping["system_concept_id"])

    get_concept_details(f"Updated_DB/{json_mapping['source_db']}", json_mapping['content_concept_id'])

    computed_difficulty = result["difficulty_map"].get(concept, "medium")
    strategy_type = result["strategy_map"].get(concept, "practice")
    content_type = result["content_type_map"].get(concept, "guided_practice")

    json_mapping["teaching_strategy"] = {
        "recommended_difficulty": computed_difficulty,
        "strategy_type": strategy_type,
        "content_type": content_type
    }
      
    if json_mapping["status"] != "Failed":
        json_mapping["status"] = "Success"

    print("======================================")
    for key in json_mapping:
        print(f"{key} : {json_mapping[key]}")


import sqlite3

from concept_dependency import run_dependency_module


def get_concept_details(db_path, concept_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT name, difficulty, description
        FROM concepts
        WHERE concept_id = ?
        """

        cursor.execute(query, (concept_id,))
        row = cursor.fetchone()

        conn.close()

        if row:
            json_mapping["concept_name"] = row[0]
            json_mapping["difficulty"] = row[1]
            json_mapping["description"] = row[2]
        else:
            for key in json_mapping:
                json_mapping[key] = "None"
            json_mapping['status'] = "Failed"

    except Exception as e:
        return {"error": str(e)}

def get_content_concept_id_and_domain_and_db(db_path,system_concept_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        Select content_concept_id,domain,source_db from concept_id_map
        where system_concept_id = ?
        """
        
        cursor.execute(query, (system_concept_id,))
        row = cursor.fetchone()

        if not row:
            for key in json_mapping:
                json_mapping[key] = "None"
            json_mapping['status'] = "Failed"
            return

        conn.close()

        json_mapping["content_concept_id"] = row[0]
        json_mapping["domain"] = row[1]
        json_mapping["source_db"] = row[2]

    except Exception as e:
        print(f"Error fetcing content_concept_id {e}")

def get_teaching_content(db_path, concept_id, strategy_type, content_type, difficulty):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
        SELECT *
        FROM teaching_content
        WHERE concept_id = ?
        AND strategy = ?
        AND content_type = ?
        AND difficulty = ?
        LIMIT 1
        """

        cursor.execute(query, (concept_id, strategy_type, content_type, difficulty))
        row = cursor.fetchone()

        conn.close()
        return row

    except Exception as e:
        print("Error fetching teaching content:", e)
        return None

# json_mapping["system_concept_id"] = input("Enter the System Concept ID : ")

tutor_DB = "Updated_DB/tutor.db"

DB_PATHS = [
    "Updated_DB/python_learning.db",
    "Updated_DB/database_sql.db",
    "Updated_DB/html_web_basics.db",
    "Updated_DB/git_version_control.db",
    "Updated_DB/data_structures.db",
]
result = run_dependency_module(
    tutor_db=tutor_DB,
    db_paths=DB_PATHS,
    learner_id="387766"
)

print("\nUnlocked:", result["unlocked_concepts"])

teaching_contents = [] 

for concept in result["unlocked_concepts"]:
    json_mapping = {
        "system_concept_id" : "",
        "content_concept_id" : "",
        "domain":"",
        "concept_name" : "",
        "description" : "",
        "teaching_strategy" : {},
        "difficulty" : "",
        # "content_type" : "",
        # "instruction" : "",
        "source_db" : "",
        "status": "" 
    }

    json_mapping["system_concept_id"] = concept
    get_content_concept_id_and_domain_and_db(f"Updated_DB/tutor.db",json_mapping["system_concept_id"])

    get_concept_details(f"Updated_DB/{json_mapping['source_db']}", json_mapping['content_concept_id'])

    computed_difficulty = result["difficulty_map"].get(concept, "medium")
    strategy_type = result["strategy_map"].get(concept, "practice")
    content_type = result["content_type_map"].get(concept, "guided_practice")

    json_mapping["teaching_strategy"] = {
        "recommended_difficulty": computed_difficulty,
        "strategy_type": strategy_type,
        "content_type": content_type
    }

    if json_mapping["content_concept_id"][0] == 'P':

        row = get_teaching_content(
            "Updated_DB/python_learning.db",
            json_mapping["content_concept_id"],
            strategy_type,
            content_type,
            computed_difficulty
        )

        if row:
            try:
                question = row[5]   # content_text column

                teaching_contents.append({
                    "concept_id": json_mapping["content_concept_id"],
                    "concept_name": json_mapping["concept_name"],
                    "strategy": strategy_type,
                    "content_type": content_type,
                    "difficulty": computed_difficulty,
                    "question": question
                })

            except:
                teaching_contents.append({
                    "concept_id": json_mapping["content_concept_id"],
                    "error": "Content column issue"
                })

        else:
            teaching_contents.append({
                "concept_id": json_mapping["content_concept_id"],
                "error": "No matching content found"
            })
      
    if json_mapping["status"] != "Failed":
        json_mapping["status"] = "Success"

    print("======================================")
    for key in json_mapping:
        print(f"{key} : {json_mapping[key]}")

print("\n\n========= FINAL TEACHING CONTENT =========")

for item in teaching_contents:
    print("--------------------------------------")
    for key in item:
        print(f"{key} : {item[key]}")


