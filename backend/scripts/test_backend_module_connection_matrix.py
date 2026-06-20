from __future__ import annotations

from scripts.backend_module_intelligence_audit_lib import connection_matrix, write_reports


def main() -> None:
    write_reports()
    matrix = connection_matrix()
    assert matrix
    assert any(item["api_route_connected"] for item in matrix)
    assert any(item["frontend_visible"] for item in matrix)
    assert any(item["affects_next_decision"] for item in matrix)
    assert all("runtime_status" in item for item in matrix)
    print("backend module connection matrix test success")
    print("matrix_rows:", len(matrix))


if __name__ == "__main__":
    main()
