from datetime import datetime, timezone

def now_iso() -> str:
    """UTC ISO timestamp"""
    return datetime.now(timezone.utc).isoformat()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)