"""Diagnose a cloud MySQL connection. Prints a clear verdict (auth / SSL / network).

Usage (parts):
    python tools/test_cloud_connection.py --host H --port P --user U --database D --ssl --password "..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine, text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=3306)
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", default="")
    ap.add_argument("--database", required=True)
    ap.add_argument("--ssl", action="store_true")
    a = ap.parse_args()

    pw_len = len(a.password)
    print(f"Host : {a.host}:{a.port}")
    print(f"User : {a.user}")
    print(f"DB   : {a.database}")
    print(f"SSL  : {a.ssl}")
    print(f"Password length received: {pw_len} chars "
          f"(Aiven defaults are ~24+; if this looks short, it was truncated on copy)")
    print()

    ssl = "&ssl_disabled=false" if a.ssl else ""
    url = (f"mysql+mysqlconnector://{quote_plus(a.user)}:{quote_plus(a.password)}"
           f"@{quote_plus(a.host)}:{a.port}/{quote_plus(a.database)}?charset=utf8mb4{ssl}")
    try:
        eng = create_engine(url, pool_pre_ping=True, connect_args={"connection_timeout": 12})
        with eng.connect() as c:
            v = c.execute(text("SELECT VERSION()")).scalar()
            n = c.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=:d"),
                          {"d": a.database}).scalar()
        print(f"SUCCESS - connected. MySQL version {v}; {n} tables in '{a.database}'.")
        print("Your credentials are correct. Use the SAME password in Streamlit secrets.")
    except Exception as exc:
        msg = str(getattr(exc, "orig", exc))
        print("FAILED -", msg[:300])
        low = msg.lower()
        print()
        if "1045" in msg or "access denied" in low:
            print("DIAGNOSIS: Access denied = wrong username or password.")
            print(" - Re-copy the password from Aiven using its COPY button (don't hand-select).")
            print(" - Check for a leading/trailing space.")
            print(" - Easiest fix: in Aiven, RESET the service password to a simple one (letters+digits), then retry.")
        elif "ssl" in low or "tls" in low:
            print("DIAGNOSIS: SSL/TLS issue. Keep --ssl (Aiven requires it).")
        elif "timed out" in low or "can't connect" in low or "2003" in msg:
            print("DIAGNOSIS: Network/host/port issue. Verify host + port 14527 and that the service is Running.")
        else:
            print("DIAGNOSIS: Unrecognized error - paste the line above for help.")


if __name__ == "__main__":
    main()
