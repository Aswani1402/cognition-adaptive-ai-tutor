import sqlite3

def inspect_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print(f"\nConnected to: {db_path}")

        # 🔹 Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        if not tables:
            print("No tables found.")
            return

        print("\nTables found:")
        print(len(tables))
        for table in tables:
            table_name = table[0]
            print("-------------------------------------")
            print(f"📌 Table: {table_name}")
            print("-------------------------------------")

            # 🔹 Get columns of each table
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()

            print("Columns:")
            for col in columns:
                print(f" - {col[1]} ({col[2]})")

        conn.close()

    except Exception as e:
        print("Error:", e)


# ---- CHANGE PATH HERE ----
db_path = "Updated_DB/tutor.db"

inspect_db(db_path)