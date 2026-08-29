"""
Phase 6 — Project Marketplace Migration
Creates: projects, project_bids tables + indexes
All operations are idempotent (safe to re-run).
"""
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
passed = 0
failed = 0

def step(name, sql, params=None):
    global passed, failed
    print(f"  → {name} ...", end=" ", flush=True)
    try:
        with engine.begin() as c:
            c.execute(text(sql), params or {})
        print("OK")
        passed += 1
    except Exception as e:
        print(f"ERROR: {e}")
        failed += 1

print("\n" + "="*60)
print("PHASE 6 — DATABASE MIGRATION")
print("="*60)

# ── 1. PROJECTS TABLE ─────────────────────────────────────────
print("\n[1] Creating projects table...")
step("CREATE projects", """
CREATE TABLE IF NOT EXISTS projects (
    id            SERIAL PRIMARY KEY,
    title         TEXT NOT NULL,
    category      TEXT NOT NULL,
    city          TEXT NOT NULL,
    country       TEXT NOT NULL DEFAULT 'IQ',
    budget_min    NUMERIC,
    budget_max    NUMERIC,
    description   TEXT,
    attachments   TEXT NOT NULL DEFAULT '[]',
    contact_name  TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    contact_email TEXT,
    status        TEXT NOT NULL DEFAULT 'pending',
    owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
)
""")

step("INDEX projects.status", """
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)
""")

step("INDEX projects.city", """
CREATE INDEX IF NOT EXISTS idx_projects_city ON projects(city)
""")

step("INDEX projects.category", """
CREATE INDEX IF NOT EXISTS idx_projects_category ON projects(category)
""")

step("INDEX projects.owner_user_id", """
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_user_id)
WHERE owner_user_id IS NOT NULL
""")

step("INDEX projects.created_at", """
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC)
""")

# ── 2. PROJECT_BIDS TABLE ─────────────────────────────────────
print("\n[2] Creating project_bids table...")
step("CREATE project_bids", """
CREATE TABLE IF NOT EXISTS project_bids (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    price         NUMERIC NOT NULL,
    duration_days INTEGER,
    message       TEXT,
    status        TEXT NOT NULL DEFAULT 'submitted',
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (project_id, company_id)
)
""")

step("INDEX project_bids.project_id", """
CREATE INDEX IF NOT EXISTS idx_bids_project_id ON project_bids(project_id)
""")

step("INDEX project_bids.company_id", """
CREATE INDEX IF NOT EXISTS idx_bids_company_id ON project_bids(company_id)
""")

step("INDEX project_bids.status", """
CREATE INDEX IF NOT EXISTS idx_bids_status ON project_bids(status)
""")

# ── 3. VERIFY ─────────────────────────────────────────────────
print("\n[3] Verification...")
with engine.connect() as c:
    for t in ["projects", "project_bids"]:
        cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        cols = c.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name=:t ORDER BY ordinal_position
        """), {"t": t}).scalars().all()
        print(f"  {t}: {cnt} rows — cols: {', '.join(cols)}")

print("\n" + "="*60)
print(f"MIGRATION COMPLETE: {passed} passed, {failed} failed")
print("="*60)
if failed > 0:
    raise SystemExit(1)
