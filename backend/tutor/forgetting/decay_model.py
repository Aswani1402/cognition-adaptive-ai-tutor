import math
from datetime import datetime, timezone
from typing import Optional, Union

DEFAULT_LAMBDA = 0.03  # per day


def _to_dt_utc(ts: Optional[Union[str, float, int, datetime]]) -> Optional[datetime]:
    """
    Accepts:
      - datetime
      - unix seconds (int/float or numeric string)
      - ISO string timestamps (e.g., '2026-02-18T12:34:56', '...Z')
    Returns timezone-aware datetime in UTC, or None if unparsable.
    """
    if ts is None:
        return None

    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    # unix seconds?
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)

    s = str(ts).strip()
    if not s:
        return None

    # unix seconds string?
    try:
        return datetime.fromtimestamp(float(s), tz=timezone.utc)
    except Exception:
        pass

    # ISO string
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def decay_score(last_practiced_at: Optional[Union[str, float, int, datetime]],
               lam: float = DEFAULT_LAMBDA,
               now: Optional[datetime] = None) -> float:
    """
    Returns forgetting risk score in [0,1]:
      d = 1 - exp(-lam * delta_days)
    """
    now_dt = now if now else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    last_dt = _to_dt_utc(last_practiced_at)
    if last_dt is None:
        return 0.0  # safe fallback (no decay if unknown)

    delta_days = (now_dt - last_dt).total_seconds() / 86400.0
    if delta_days < 0:
        delta_days = 0.0

    d = 1.0 - math.exp(-float(lam) * float(delta_days))
    return float(max(0.0, min(1.0, d)))


def decayed_mastery(mastery: float,
                    last_practiced_at: Optional[Union[str, float, int, datetime]],
                    lam: float = DEFAULT_LAMBDA,
                    now: Optional[datetime] = None) -> float:
    """
    Converts mastery (0..1) into time-decayed mastery (0..1):
      m_decayed = mastery * exp(-lam * delta_days)
    """
    mastery = float(mastery) if mastery is not None else 0.0
    mastery = max(0.0, min(1.0, mastery))

    now_dt = now if now else datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)

    last_dt = _to_dt_utc(last_practiced_at)
    if last_dt is None:
        return mastery  # safe fallback: no time info => no decay applied

    delta_days = (now_dt - last_dt).total_seconds() / 86400.0
    if delta_days < 0:
        delta_days = 0.0

    m = mastery * math.exp(-float(lam) * float(delta_days))
    return float(max(0.0, min(1.0, m)))