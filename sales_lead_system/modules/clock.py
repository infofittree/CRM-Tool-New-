"""Business-timezone clock.

Streamlit Cloud servers run in UTC, but the sales team works in India (IST).
Computing "today" in UTC makes follow-ups scheduled for the local date appear
in the wrong day bucket near midnight. Every "today"/"now" used for follow-up
scheduling and dashboard buckets must come from here so the calendar day matches
the team's actual day.

Timezone is configurable via CRM_TIMEZONE (env var or Streamlit secret);
defaults to Asia/Kolkata (IST).
"""

from __future__ import annotations

import os
from datetime import date, datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

_DEFAULT_TZ = "Asia/Kolkata"


def _tz_name() -> str:
    # Check env var first, then try Streamlit secrets.
    tz = os.getenv("CRM_TIMEZONE")
    if tz:
        return tz
    try:
        import sys
        if "streamlit" in sys.modules:
            import streamlit as st
            if "CRM_TIMEZONE" in st.secrets:
                return str(st.secrets["CRM_TIMEZONE"])
    except Exception:
        pass
    return _DEFAULT_TZ


def _tz():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(_tz_name())
    except Exception:
        try:
            return ZoneInfo(_DEFAULT_TZ)
        except Exception:
            return None


def now() -> datetime:
    """Current time in the business timezone (naive-safe for comparisons)."""
    tz = _tz()
    return datetime.now(tz) if tz else datetime.now()


def today() -> date:
    """Today's date in the business timezone — use this instead of date.today()."""
    return now().date()
