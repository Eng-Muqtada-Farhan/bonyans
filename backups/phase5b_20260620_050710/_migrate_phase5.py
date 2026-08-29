"""
Phase 5 — Safe Database Migration
Creates 4 new tables and adds verification_status to companies.
All operations are idempotent (safe to run multiple times).
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)

STEPS = []

def step(label, sql):
    STEPS.append((label, sql))

# ── 1. Add verification_status to companies (safe — IF NOT EXISTS via DO block) ──
step("ADD companies.verification_status", """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='companies'
          AND column_name='verification_status'
    ) THEN
        ALTER TABLE companies
        ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'pending';
    END IF;
END$$;
""")

# ── 2. company_users ──────────────────────────────────────────────────────────
step("CREATE company_users", """
CREATE TABLE IF NOT EXISTS company_users (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    provider      TEXT    NOT NULL DEFAULT 'email',
    provider_id   TEXT,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")

step("INDEX company_users.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_users_company_id
ON company_users(company_id);
""")

step("INDEX company_users.email", """
CREATE UNIQUE INDEX IF NOT EXISTS idx_company_users_email
ON company_users(email);
""")

# ── 3. company_projects ───────────────────────────────────────────────────────
step("CREATE company_projects", """
CREATE TABLE IF NOT EXISTS company_projects (
    id               SERIAL PRIMARY KEY,
    company_id       INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    title            TEXT    NOT NULL,
    description      TEXT,
    location         TEXT,
    completion_date  TEXT,
    image_url        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")

step("INDEX company_projects.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_projects_company_id
ON company_projects(company_id);
""")

# ── 4. company_gallery ────────────────────────────────────────────────────────
step("CREATE company_gallery", """
CREATE TABLE IF NOT EXISTS company_gallery (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    image_url   TEXT    NOT NULL,
    title       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")

step("INDEX company_gallery.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_gallery_company_id
ON company_gallery(company_id);
""")

# ── 5. company_views ──────────────────────────────────────────────────────────
step("CREATE company_views", """
CREATE TABLE IF NOT EXISTS company_views (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    ip_hash     TEXT,
    user_agent  TEXT,
    viewed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""")

step("INDEX company_views.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_views_company_id
ON company_views(company_id);
""")

step("INDEX company_views.viewed_at", """
CREATE INDEX IF NOT EXISTS idx_company_views_viewed_at
ON company_views(viewed_at);
""")

# ── Run ───────────────────────────────────────────────────────────────────────
print("Starting Phase 5 migration...\n")
passed = 0
failed = 0

with engine.begin() as conn:
    for label, sql in STEPS:
        try:
            conn.execute(text(sql))
            print(f"  [OK]  {label}")
            passed += 1
        except Exception as e:
            print(f"  [ERR] {label}: {e}")
            failed += 1
            raise  # abort on first error — engine.begin() will rollback

print(f"\nMigration complete: {passed} steps passed, {failed} failed.")

# ── Verify schema ─────────────────────────────────────────────────────────────
print("\n--- Schema verification ---")
with engine.connect() as conn:
    tables = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )).fetchall()
    for t in tables:
        cols = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema='public' AND table_name=:t "
            "ORDER BY ordinal_position"
        ), {"t": t[0]}).fetchall()
        col_names = [c[0] for c in cols]
        print(f"  {t[0]:30s} → {col_names}")
