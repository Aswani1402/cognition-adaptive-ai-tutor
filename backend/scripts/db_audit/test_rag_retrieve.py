# scripts/db_audit/test_rag_retrieve.py

from tutor.rag.retrieve import retrieve_rag_context
import json

result = retrieve_rag_context("1")
print(json.dumps(result, indent=2))