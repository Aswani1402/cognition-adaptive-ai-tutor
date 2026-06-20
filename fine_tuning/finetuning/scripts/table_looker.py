import sqlite3

def view_table(db_path, table_name):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"\nTable: {table_name}")

        # 🔹 Show columns
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()

        print("\nColumns:")
        col_names = []
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            col_names.append(col[1])

        # 🔹 Show data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10;")
        rows = cursor.fetchall()

        print("\nSample Data:")
        for row in rows:
            print(row)

        conn.close()

    except Exception as e:
        print("Error:", e)

# ---- CHANGE THESE ----
db_path = "Updated_DB/tutor.db"
table_name = "concept_id_map"

view_table(db_path, table_name)
