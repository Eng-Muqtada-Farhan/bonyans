"""Phase 9 — Security & Production Readiness Migration"""
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text
import os, sys

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
passed = failed = 0

def step(name, sql):
    global passed, failed
    print(f"  >> {name} ...", end=" ", flush=True)
    try:
        with engine.begin() as c: c.execute(text(sql))
        print("OK"); passed += 1
    except Exception as e:
        print(f"ERROR: {e}"); failed += 1

print("\n" + "="*55)
print("PHASE 9 — SECURITY MIGRATION")
print("="*55)

step("CREATE security_audit_log", """
CREATE TABLE IF NOT EXISTS security_audit_log (
    id         SERIAL PRIMARY KEY,
    actor_type TEXT NOT NULL,
    actor_id   TEXT NOT NULL DEFAULT '',
    action     TEXT NOT NULL,
    ip_hash    TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    meta       TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX audit.action",     "CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_log(action)")
step("INDEX audit.created_at", "CREATE INDEX IF NOT EXISTS idx_audit_created ON security_audit_log(created_at DESC)")
step("INDEX audit.actor",      "CREATE INDEX IF NOT EXISTS idx_audit_actor ON security_audit_log(actor_type, actor_id)")

print("\n[Verify]")
with engine.connect() as c:
    cnt  = c.execute(text("SELECT COUNT(*) FROM security_audit_log")).scalar()
    cols = c.execute(text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name='security_audit_log' ORDER BY ordinal_position
    """)).scalars().all()
    print(f"  security_audit_log: {cnt} rows — {', '.join(cols)}")

print(f"\n{'='*55}\nMIGRATION COMPLETE: {passed} passed, {failed} failed\n{'='*55}")
if failed: sys.exit(1)
