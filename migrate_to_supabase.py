"""Copy every table from local database.db (SQLite) into Supabase (Postgres).

Run from the project folder:
    pip install psycopg2-binary
    $env:DATABASE_URL = "postgresql://..."   (PowerShell)
    python migrate_to_supabase.py

The script never stores the password; it only reads DATABASE_URL from the
environment. Tables that already contain rows in Supabase are skipped.
"""
import os
import sqlite3
import sys

import psycopg2

SQLITE_FILE = "database.db"

url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("DATABASE_URL environment variable is not set.")
if not os.path.exists(SQLITE_FILE):
    sys.exit(f"{SQLITE_FILE} not found. Run this from the project folder.")

sl = sqlite3.connect(SQLITE_FILE)
pg = psycopg2.connect(url)
cur = pg.cursor()


def pg_type(ctype: str) -> str:
    t = (ctype or "").upper()
    if "INT" in t:
        return "BIGINT"
    if any(x in t for x in ("REAL", "FLOA", "DOUB")):
        return "DOUBLE PRECISION"
    return "TEXT"


tables = [
    r[0]
    for r in sl.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
]

for t in tables:
    cols = sl.execute(f'PRAGMA table_info("{t}")').fetchall()
    defs, pk_serial = [], None
    for _, name, ctype, _notnull, _dflt, pk in cols:
        if pk and pg_type(ctype) == "BIGINT":
            defs.append(f'"{name}" BIGSERIAL PRIMARY KEY')
            pk_serial = name
        elif pk:
            defs.append(f'"{name}" TEXT PRIMARY KEY')
        else:
            defs.append(f'"{name}" {pg_type(ctype)}')

    cur.execute(f'CREATE TABLE IF NOT EXISTS "{t}" ({", ".join(defs)})')
    cur.execute(f'ALTER TABLE "{t}" ENABLE ROW LEVEL SECURITY')

    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    if cur.fetchone()[0] > 0:
        print(f"{t}: already has data in Supabase, skipped")
        continue

    names = [c[1] for c in cols]
    rows = sl.execute(f'SELECT {", ".join(chr(34) + n + chr(34) for n in names)} FROM "{t}"').fetchall()
    if rows:
        placeholders = ", ".join(["%s"] * len(names))
        col_list = ", ".join(f'"{n}"' for n in names)
        cur.executemany(f'INSERT INTO "{t}" ({col_list}) VALUES ({placeholders})', rows)
    if pk_serial:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('\"{t}\"', '{pk_serial}'), "
            f'COALESCE((SELECT MAX("{pk_serial}") FROM "{t}"), 1))'
        )
    print(f"{t}: {len(rows)} rows copied, columns = {names}")

pg.commit()
cur.close()
pg.close()
print("Done.")