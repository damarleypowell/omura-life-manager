"""
One-time migration: copy ALL data from the Neon (serverless Postgres) database
into a local SQLite file, so the app can run fully locally with real data and
none of Neon's cold-start flakiness.

Run:  python -m backend.migrate_neon_to_sqlite

Source: DATABASE_URL from backend/.env (Neon).
Dest:   ./omura_local.db (SQLite) — recreated fresh each run.
Copies in FK-dependency order via the ORM (so enum columns convert correctly).
"""

import os
import time

import dotenv

_ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
dotenv.load_dotenv(_ENV)

NEON_URL = os.environ["DATABASE_URL"]
# Dest + retry count overridable so we can import into a side file while the
# live app keeps running on omura_local.db, then swap it in.
SQLITE_PATH = os.path.abspath(os.environ.get("MIGRATE_DEST", "omura_local.db"))
SQLITE_URL = f"sqlite:///{SQLITE_PATH}"
_ATTEMPTS = int(os.environ.get("MIGRATE_ATTEMPTS", "10"))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker      # noqa: E402

from backend.app.database.session import Base  # noqa: E402
from backend.app.database import models        # noqa: F401,E402  (registers mappers)


def _wait_for_neon(engine, attempts: int = 10) -> None:
    for i in range(attempts):
        try:
            with engine.connect() as c:
                c.execute(text("SELECT 1"))
            print(f"Neon reachable (attempt {i + 1}).")
            return
        except Exception as exc:
            wait = 3 + i * 2
            print(f"Neon cold-start retry {i + 1}/{attempts} in {wait}s: {str(exc)[:90]}")
            time.sleep(wait)
    raise RuntimeError("Could not reach Neon after retries — try again in a moment.")


def main():
    # Fresh local DB
    if os.path.exists(SQLITE_PATH):
        os.remove(SQLITE_PATH)
        print(f"Removed existing {SQLITE_PATH}")

    src_engine = create_engine(NEON_URL, pool_pre_ping=True)
    dst_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

    _wait_for_neon(src_engine, attempts=_ATTEMPTS)

    # Build the local schema
    Base.metadata.create_all(bind=dst_engine)

    Src = sessionmaker(bind=src_engine)
    Dst = sessionmaker(bind=dst_engine)
    src, dst = Src(), Dst()

    model_by_table = {m.class_.__tablename__: m.class_ for m in Base.registry.mappers}

    report = {}
    try:
        # sorted_tables respects FK dependencies (parents before children)
        for table in Base.metadata.sorted_tables:
            Model = model_by_table.get(table.name)
            if Model is None:
                continue
            try:
                rows = src.query(Model).all()
            except Exception as exc:
                print(f"  ! skip {table.name}: read failed ({str(exc)[:80]})")
                src.rollback()
                continue
            for obj in rows:
                data = {c.name: getattr(obj, c.name) for c in table.columns}
                dst.add(Model(**data))
            dst.commit()
            report[table.name] = len(rows)
            print(f"  copied {len(rows):>5}  {table.name}")
    finally:
        src.close()
        dst.close()

    total = sum(report.values())
    print(f"\nDone — {total} rows copied into {SQLITE_PATH}")
    print("Run the app locally with:  python -m uvicorn backend.run_local:app --host 127.0.0.1 --port 8003")


if __name__ == "__main__":
    main()
