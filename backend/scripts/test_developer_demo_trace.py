from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "developer_demo"))

from trace_builder import build_trace  # noqa: E402


def main() -> None:
    trace = build_trace("14", "Python", "Variables")
    required = ["Answer Evaluation", "Knowledge Tracing", "Behaviour Signals", "RAG Retrieval", "CogniTutorLM / Guarded Generation", "Notebook Memory", "Reward", "XAI"]
    flow = trace.get("flow", [])
    missing = [item for item in required if item not in flow]
    ok = not missing
    print(json.dumps({"status": "pass" if ok else "fail", "missing": missing, "final_source": trace.get("final_source")}, indent=2))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
