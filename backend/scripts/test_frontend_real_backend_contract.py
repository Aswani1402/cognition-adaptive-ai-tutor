from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend_ui" / "KP-UI"


def main() -> None:
    env = (FRONTEND / ".env.local").read_text(encoding="utf-16")
    api = (FRONTEND / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    topbar = (FRONTEND / "src" / "components" / "layout" / "Topbar.tsx").read_text(encoding="utf-8")
    assert "VITE_API_BASE_URL=http://127.0.0.1:8010" in env, env
    assert "/openapi.json" in api, "health check must use openapi"
    assert "Backend URL missing" in api and "Backend URL missing" in topbar
    assert "Live backend" in topbar
    assert "throw backendUnavailable" in api
    print({"env": "ok", "api_contract": "live backend, no authenticated mock fallback"})


if __name__ == "__main__":
    main()
