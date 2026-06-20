from __future__ import annotations

from pathlib import Path

from scripts.production_readiness_checks import JSON_DIR, REPORT_DIR, write_final_reports


REQUIRED = [
    "final_production_readiness_report",
    "full_frontend_backend_feature_connection_report",
    "full_module_feature_status_matrix",
    "final_missing_work_and_limitations_report",
]


def main() -> None:
    write_final_reports()
    for name in REQUIRED:
        md = REPORT_DIR / f"{name}.md"
        js = JSON_DIR / f"{name}.json"
        assert md.exists() and md.stat().st_size > 100, md
        assert js.exists() and js.stat().st_size > 100, js
        text = md.read_text(encoding="utf-8")
        assert "Module / Feature" in text and "Remaining Limitations" in text, md
    print("final reports exist test success")


if __name__ == "__main__":
    main()
