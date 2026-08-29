"""
Phase 7 — Subscriptions & Monetization Migration
Creates: subscription_plans, subscription_requests, company_subscriptions
Seeds: 4 official plans (starter, active, featured, partner)
All operations are idempotent.
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
print("PHASE 7 — DATABASE MIGRATION: SUBSCRIPTIONS")
print("="*60)

# ── 1. SUBSCRIPTION PLANS TABLE ───────────────────────────────
print("\n[1] Creating subscription_plans table...")
step("CREATE subscription_plans", """
CREATE TABLE IF NOT EXISTS subscription_plans (
    id                SERIAL PRIMARY KEY,
    code              TEXT UNIQUE NOT NULL,
    name              TEXT NOT NULL,
    monthly_price     NUMERIC NOT NULL DEFAULT 0,
    yearly_price      NUMERIC NOT NULL DEFAULT 0,
    max_images        INTEGER NOT NULL DEFAULT 3,
    max_project_leads INTEGER NOT NULL DEFAULT 1,
    search_priority   INTEGER NOT NULL DEFAULT 0,
    is_verified       BOOLEAN NOT NULL DEFAULT false,
    is_featured       BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMP NOT NULL DEFAULT now()
)
""")

step("INDEX subscription_plans.code", """
CREATE UNIQUE INDEX IF NOT EXISTS idx_sub_plans_code ON subscription_plans(code)
""")

# ── 2. SEED PLANS ─────────────────────────────────────────────
print("\n[2] Seeding official plans...")

plans = [
    ("starter", "STARTER",  0,   0,   3,   1,  0, False, False),
    ("active",  "ACTIVE",   10,  100, 15,  5,  1, False, False),
    ("featured","FEATURED",  20,  200, 50,  20, 2, True,  True),
    ("partner", "PARTNER",   40,  400, -1,  -1, 3, True,  True),
]

for code, name, mp, yp, mi, ml, sp, iv, iF in plans:
    step(f"SEED {code}", """
INSERT INTO subscription_plans
    (code, name, monthly_price, yearly_price, max_images,
     max_project_leads, search_priority, is_verified, is_featured)
VALUES
    (:code, :name, :mp, :yp, :mi, :ml, :sp, :iv, :if)
ON CONFLICT (code) DO UPDATE SET
    name=EXCLUDED.name,
    monthly_price=EXCLUDED.monthly_price,
    yearly_price=EXCLUDED.yearly_price,
    max_images=EXCLUDED.max_images,
    max_project_leads=EXCLUDED.max_project_leads,
    search_priority=EXCLUDED.search_priority,
    is_verified=EXCLUDED.is_verified,
    is_featured=EXCLUDED.is_featured
""", {"code":code,"name":name,"mp":mp,"yp":yp,"mi":mi,"ml":ml,"sp":sp,"iv":iv,"if":iF})

# ── 3. SUBSCRIPTION REQUESTS TABLE ────────────────────────────
print("\n[3] Creating subscription_requests table...")
step("CREATE subscription_requests", """
CREATE TABLE IF NOT EXISTS subscription_requests (
    id           SERIAL PRIMARY KEY,
    company_id   INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    plan_id      INTEGER NOT NULL REFERENCES subscription_plans(id),
    status       TEXT NOT NULL DEFAULT 'pending',
    notes        TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT now(),
    processed_at TIMESTAMP,
    processed_by TEXT
)
""")

step("INDEX sub_requests.company_id", """
CREATE INDEX IF NOT EXISTS idx_sub_req_company_id ON subscription_requests(company_id)
""")

step("INDEX sub_requests.status", """
CREATE INDEX IF NOT EXISTS idx_sub_req_status ON subscription_requests(status)
""")

# ── 4. COMPANY SUBSCRIPTIONS TABLE ────────────────────────────
print("\n[4] Creating company_subscriptions table...")
step("CREATE company_subscriptions", """
CREATE TABLE IF NOT EXISTS company_subscriptions (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    plan_id     INTEGER NOT NULL REFERENCES subscription_plans(id),
    status      TEXT NOT NULL DEFAULT 'active',
    is_founder  BOOLEAN NOT NULL DEFAULT false,
    start_date  TIMESTAMP NOT NULL DEFAULT now(),
    expires_at  TIMESTAMP,
    auto_renew  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMP NOT NULL DEFAULT now()
)
""")

step("INDEX company_subs.company_id", """
CREATE INDEX IF NOT EXISTS idx_company_subs_company_id ON company_subscriptions(company_id)
""")

step("INDEX company_subs.status", """
CREATE INDEX IF NOT EXISTS idx_company_subs_status ON company_subscriptions(status)
""")

step("INDEX company_subs.expires_at", """
CREATE INDEX IF NOT EXISTS idx_company_subs_expires ON company_subscriptions(expires_at)
WHERE expires_at IS NOT NULL
""")

# ── 5. VERIFY ─────────────────────────────────────────────────
print("\n[5] Verification...")
with engine.connect() as c:
    for t in ["subscription_plans","subscription_requests","company_subscriptions"]:
        cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"  {t}: {cnt} rows")

    plans_rows = c.execute(text(
        "SELECT code, name, monthly_price, max_images, max_project_leads FROM subscription_plans ORDER BY search_priority"
    )).fetchall()
    print("\n  Plans seeded:")
    for p in plans_rows:
        lim_img = str(p[3]) if p[3] != -1 else "∞"
        lim_ld  = str(p[4]) if p[4] != -1 else "∞"
        print(f"    {p[0]:10} ${p[2]:4}/mo  images:{lim_img}  leads:{lim_ld}")

print("\n" + "="*60)
print(f"MIGRATION COMPLETE: {passed} passed, {failed} failed")
print("="*60)
if failed > 0:
    raise SystemExit(1)
