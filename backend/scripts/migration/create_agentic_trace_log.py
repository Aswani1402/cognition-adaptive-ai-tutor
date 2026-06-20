from __future__ import annotations

from tutor.system.agentic_orchestrator import create_agentic_trace_log_table


def main() -> None:
    result = create_agentic_trace_log_table()
    print("STATUS:", result["status"])
    print("MODULE: create_agentic_trace_log")
    print("TABLE:", result["table"])
    print("DB:", result["db_path"])
    print("COLUMNS_ADDED:", ", ".join(result.get("columns_added", [])) or "none")


if __name__ == "__main__":
    main()
