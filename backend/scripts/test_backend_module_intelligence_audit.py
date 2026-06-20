from __future__ import annotations

from pathlib import Path

from scripts.backend_module_intelligence_audit_lib import MODULES, validate_inventory, write_reports


def main() -> None:
    validate_inventory()
    result = write_reports()
    assert result["status"] == "success"
    assert result["summary"]["total_modules_found"] >= 20
    assert any(item["module_name"] == "Knowledge Tracing" for item in MODULES)
    assert any(item["module_name"] == "Behaviour Modelling" for item in MODULES)
    for report in result["reports"]:
        assert Path(report).exists(), report
    print("backend module intelligence audit test success")
    print("total_modules_found:", result["summary"]["total_modules_found"])


if __name__ == "__main__":
    main()
