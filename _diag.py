from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text; import os
engine = create_engine(os.getenv('DATABASE_URL'), pool_pre_ping=True)
with engine.connect() as c:
    # All companies — id, name, status
    rows = c.execute(text('SELECT id, name, status FROM companies ORDER BY id')).fetchall()
    print('=== ALL COMPANIES ===')
    for r in rows:
        print(f'  id={r[0]:3d}  status={r[2]:10s}  name={r[1]}')

    # Specifically id=8
    row = c.execute(text('SELECT id, name, status, verified FROM companies WHERE id=8')).fetchone()
    print('\n=== id=8 ===')
    print(f'  {row}')
