import os
import re
import traceback
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


def get_railway_password():
    # Prefer explicit environment variable
    env = os.getenv("RAILWAY_PASSWORD")
    if env:
        return env

    # Fallback: read upload.py and extract the literal (safe read, no import)
    p = os.path.join(os.path.dirname(__file__), "upload.py")
    try:
        with open(p, "r", encoding="utf-8") as f:
            s = f.read()
        m = re.search(r"RAILWAY_PASSWORD\s*=\s*[\'\"]([^\'\"]+)[\'\"]", s)
        if m:
            return m.group(1)
    except Exception:
        pass

    return None


def test_connection():
    pwd = get_railway_password()
    if not pwd:
        print("No Railway password found. Set RAILWAY_PASSWORD environment variable or put it in upload.py.")
        return 2

    user = "root"
    host = "centerbeam.proxy.rlwy.net"
    port = 32321
    database = "railway"

    password = quote_plus(pwd)
    connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

    print(f"Attempting to connect to {user}@{host}:{port}/{database} (password hidden)")

    try:
        engine = create_engine(connection_string, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            # Try a simple query
            r = conn.execute(text("SELECT VERSION() as v"))
            row = r.mappings().first()
            print("Connected successfully. Server version:", row["v"] if row else "(no result)")
        return 0
    except Exception as e:
        print("Connection failed:")
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = test_connection()
    raise SystemExit(exit_code)
