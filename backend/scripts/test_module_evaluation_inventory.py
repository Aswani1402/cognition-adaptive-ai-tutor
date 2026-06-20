from __future__ import annotations

from scripts.audit_full_system_module_connections import build_evaluation_inventory, run_audit


def main() -> None:
    run_audit()
    inventory = build_evaluation_inventory()
    assert inventory["items"], "No inventory rows produced."
    for item in inventory["items"]:
        assert item["status"] in {"success", "warning"}, item
        if item["status"] == "warning":
            assert "recommendation" in item, item
    print("STATUS: success")
    print("MODULE: test_module_evaluation_inventory")


if __name__ == "__main__":
    main()
