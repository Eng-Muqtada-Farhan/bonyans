"""
Phase 5B — Global Architecture Migration
Creates: users, company_members, project_requests
Extends: companies with 10 new columns
Migrates: existing company_users data into new tables
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
print("PHASE 5B — DATABASE MIGRATION")
print("="*60)

# ── 1. USERS TABLE ────────────────────────────────────────────
print("\n[1] Creating users table...")
step("CREATE users", """
CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,
    email             TEXT UNIQUE NOT NULL,
    phone             TEXT,
    display_name      TEXT,
    avatar_url        TEXT,
    provider          TEXT NOT NULL DEFAULT 'email',
    provider_id       TEXT,
    password_hash     TEXT,
    is_email_verified BOOLEAN NOT NULL DEFAULT false,
    is_phone_verified BOOLEAN NOT NULL DEFAULT false,
    is_active         BOOLEAN NOT NULL DEFAULT true,
    created_at        TIMESTAMP NOT NULL DEFAULT now(),
    updated_at        TIMESTAMP NOT NULL DEFAULT now()
)
""")

step("INDEX users.email", """
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email)
""")

step("INDEX users.provider_id", """
CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider, provider_id)
WHERE provider_id IS NOT NULL
""")

# ── 2. MIGRATE company_users → users ─────────────────────────
print("\n[2] Migrating existing company_users → users...")
step("MIGRATE company_users → users", """
INSERT INTO users
    (id, email, provider, provider_id, password_hash, is_active, created_at, updated_at)
SELECT
    id, email, provider, provider_id, password_hash, is_active, created_at, updated_at
FROM company_users
ON CONFLICT (email) DO NOTHING
""")

step("SYNC users_id_seq", """
SELECT setval(
    pg_get_serial_sequence('users','id'),
    COALESCE((SELECT MAX(id) FROM users), 1),
    true
)
""")

# ── 3. COMPANY_MEMBERS TABLE ──────────────────────────────────
print("\n[3] Creating company_members table...")
step("CREATE company_members", """
CREATE TABLE IF NOT EXISTS company_members (
    id         SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'owner',
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (company_id, user_id)
)
""")

step("INDEX company_members.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_members_company_id
ON company_members(company_id)
""")

step("INDEX company_members.user_id", """
CREATE INDEX IF NOT EXISTS idx_company_members_user_id
ON company_members(user_id)
""")

step("MIGRATE company_users → company_members", """
INSERT INTO company_members (company_id, user_id, role, created_at)
SELECT cu.company_id, u.id, 'owner', cu.created_at
FROM company_users cu
JOIN users u ON u.email = cu.email
ON CONFLICT (company_id, user_id) DO NOTHING
""")

# ── 4. EXTEND companies TABLE ─────────────────────────────────
print("\n[4] Extending companies table...")
new_cols = [
    ("owner_user_id",           "INTEGER REFERENCES users(id)"),
    ("slug",                    "TEXT"),
    ("country",                 "TEXT NOT NULL DEFAULT 'IQ'"),
    ("cover_url",               "TEXT"),
    ("facebook_url",            "TEXT"),
    ("instagram_url",           "TEXT"),
    ("linkedin_url",            "TEXT"),
    ("subscription_plan",       "TEXT NOT NULL DEFAULT 'free'"),
    ("subscription_expires_at", "TIMESTAMP"),
    ("updated_at",              "TIMESTAMP NOT NULL DEFAULT now()"),
]

for col_name, col_def in new_cols:
    step(f"ADD companies.{col_name}", f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='companies' AND column_name='{col_name}'
    ) THEN
        ALTER TABLE companies ADD COLUMN {col_name} {col_def};
    END IF;
END
$$
""")

step("INDEX companies.slug", """
CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_slug
ON companies(slug) WHERE slug IS NOT NULL
""")

step("INDEX companies.owner_user_id", """
CREATE INDEX IF NOT EXISTS idx_companies_owner_user_id
ON companies(owner_user_id) WHERE owner_user_id IS NOT NULL
""")

step("INDEX companies.subscription_plan", """
CREATE INDEX IF NOT EXISTS idx_companies_subscription_plan
ON companies(subscription_plan)
""")

# ── 5. BACKFILL owner_user_id ─────────────────────────────────
print("\n[5] Backfilling owner_user_id from company_members...")
step("BACKFILL owner_user_id", """
UPDATE companies c
SET owner_user_id = cm.user_id
FROM company_members cm
WHERE cm.company_id = c.id
  AND cm.role = 'owner'
  AND c.owner_user_id IS NULL
""")

# ── 6. BACKFILL slug ──────────────────────────────────────────
print("\n[6] Generating slugs for existing companies...")
step("BACKFILL slug", """
UPDATE companies
SET slug = 'company-' || id::text
WHERE slug IS NULL OR slug = ''
""")

# ── 7. PROJECT_REQUESTS TABLE ─────────────────────────────────
print("\n[7] Creating project_requests table...")
step("CREATE project_requests", """
CREATE TABLE IF NOT EXISTS project_requests (
    id            SERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    phone         TEXT NOT NULL,
    email         TEXT,
    city          TEXT NOT NULL,
    project_type  TEXT NOT NULL,
    description   TEXT,
    budget        TEXT,
    status        TEXT NOT NULL DEFAULT 'open',
    company_id    INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    user_id       INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMP NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP NOT NULL DEFAULT now()
)
""")

step("INDEX project_requests.company_id", """
CREATE INDEX IF NOT EXISTS idx_project_requests_company_id
ON project_requests(company_id)
""")

step("INDEX project_requests.status", """
CREATE INDEX IF NOT EXISTS idx_project_requests_status
ON project_requests(status)
""")

step("INDEX project_requests.created_at", """
CREATE INDEX IF NOT EXISTS idx_project_requests_created_at
ON project_requests(created_at DESC)
""")

# ── 8. VERIFY ─────────────────────────────────────────────────
print("\n[8] Verification...")
with engine.connect() as c:
    tables = ["users", "company_members", "project_requests"]
    for t in tables:
        cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t}: {cnt} rows")

    new_company_cols = ["owner_user_id", "slug", "country", "subscription_plan"]
    for col in new_company_cols:
        exists = c.execute(text("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name='companies' AND column_name=:col
        """), {"col": col}).scalar()
        print(f"  companies.{col}: {'✓' if exists else '✗ MISSING'}")

print("\n" + "="*60)
print(f"MIGRATION COMPLETE: {passed} passed, {failed} failed")
print("="*60)
if failed > 0:
    raise SystemExit(1)
