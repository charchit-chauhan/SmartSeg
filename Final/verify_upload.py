import traceback
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text


def main():
    pwd = "AgCcmzSFAvWAJhdqZaMTSDhNYylBWhwU"
    user = "root"
    host = "centerbeam.proxy.rlwy.net"
    port = 32321
    database = "railway"

    connection_string = f"mysql+pymysql://{user}:{quote_plus(pwd)}@{host}:{port}/{database}"

    try:
        engine = create_engine(connection_string, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION() AS v")).scalar()
            count = conn.execute(text("SELECT COUNT(*) AS cnt FROM shopping_trends")).scalar()
            sample = conn.execute(text("SELECT * FROM shopping_trends LIMIT 3")).mappings().all()

        print("Connected successfully.")
        print("Server version:", version)
        print("Row count:", count)
        print("Sample rows:")
        for row in sample:
            print(row)
        return 0
    except Exception:
        print("Verification failed:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
