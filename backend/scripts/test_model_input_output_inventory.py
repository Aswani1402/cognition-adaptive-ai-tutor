from __future__ import annotations

from scripts.backend_module_intelligence_audit_lib import MODULES, write_reports


def main() -> None:
    write_reports()
    for item in MODULES:
        assert item["inputs"], item["module_name"]
        assert item["output"], item["module_name"]
        assert item["model_algorithm_formula"], item["module_name"]
    comparison = [item for item in MODULES if item["status"] == "COMPARISON ONLY"]
    assert comparison, "Expected at least one comparison-only module."
    assert any("Policy" in item["module_name"] and "RL" in item["module_name"] for item in comparison)
    print("model input output inventory test success")
    print("modules_checked:", len(MODULES))


if __name__ == "__main__":
    main()
