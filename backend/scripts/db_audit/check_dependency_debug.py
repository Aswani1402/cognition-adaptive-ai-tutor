import sqlite3

from tutor.concept_dependency.run_dependency_module_final import run_dependency_module_final

conn = sqlite3.connect("external/core_data/tutor.db")

out = run_dependency_module_final(conn, "14")
print(out)

conn.close()