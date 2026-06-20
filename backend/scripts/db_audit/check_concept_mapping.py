import sqlite3


def map_pipeline_concept_to_questionbank_id(conn, pipeline_concept_id: str):
    c = conn.cursor()

    row = c.execute("""
        SELECT system_concept_id
        FROM concept_id_map
        WHERE content_concept_id = ?
        LIMIT 1
    """, (pipeline_concept_id,)).fetchone()

    if not row:
        return None

    return str(row[0]).strip()


def main():
    conn = sqlite3.connect("external/core_data/tutor.db")
    c = conn.cursor()

    print("=== SPECIFIC CONCEPT CHECK ===")
    concept_ids = ["P1", "P2", "P3", "P4", "P5", "D1", "D2", "D3", "S1", "S2", "H1", "G1"]

    for cid in concept_ids:
        rows = c.execute("""
            SELECT system_concept_id, content_concept_id, content_domain
            FROM concept_id_map
            WHERE content_concept_id = ? OR system_concept_id = ?
        """, (cid, cid)).fetchall()
        print(f"{cid} -> {rows}")

    print("\n=== MAPPING FUNCTION TEST ===")
    for cid in concept_ids:
        mapped = map_pipeline_concept_to_questionbank_id(conn, cid)
        print(f"{cid} -> {mapped}")

    conn.close()


if __name__ == "__main__":
    main()