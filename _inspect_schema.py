import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'), pool_pre_ping=True)

with engine.connect() as c:
    tables = c.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )).fetchall()

    print("=== TABLES ===")
    for t in tables:
        print(" -", t[0])

    for t in tables:
        tname = t[0]
        cols = c.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t "
            "ORDER BY ordinal_position"
        ), {"t": tname}).fetchall()
        print(f"\n=== {tname} ===")
        for col in cols:
            print(f"  {col[0]:25s} {col[1]:20s} nullable={col[2]}  default={col[3]}")
