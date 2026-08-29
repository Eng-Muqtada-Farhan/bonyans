"""
Phase 8 — Communication & Reputation Migration
Creates: conversations, messages, notifications, reviews, review_replies, activity_log
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
    print(f"  >> {name} ...", end=" ", flush=True)
    try:
        with engine.begin() as c:
            c.execute(text(sql), params or {})
        print("OK")
        passed += 1
    except Exception as e:
        print(f"ERROR: {e}")
        failed += 1

print("\n" + "="*60)
print("PHASE 8 — DATABASE MIGRATION: COMMUNICATION & REPUTATION")
print("="*60)

# ── 1. CONVERSATIONS ──────────────────────────────────────────
print("\n[1] Creating conversations table...")
step("CREATE conversations", """
CREATE TABLE IF NOT EXISTS conversations (
    id             SERIAL PRIMARY KEY,
    project_id     INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    client_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_id     INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    created_at     TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX conversations.client_user_id", """
CREATE INDEX IF NOT EXISTS idx_conv_client ON conversations(client_user_id)
""")
step("INDEX conversations.company_id", """
CREATE INDEX IF NOT EXISTS idx_conv_company ON conversations(company_id)
""")
step("INDEX conversations.project_id", """
CREATE INDEX IF NOT EXISTS idx_conv_project ON conversations(project_id)
WHERE project_id IS NOT NULL
""")

# ── 2. MESSAGES ───────────────────────────────────────────────
print("\n[2] Creating messages table...")
step("CREATE messages", """
CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type     TEXT NOT NULL,
    sender_id       INTEGER NOT NULL,
    message         TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX messages.conversation_id", """
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id)
""")
step("INDEX messages.is_read", """
CREATE INDEX IF NOT EXISTS idx_msg_read ON messages(is_read) WHERE is_read = false
""")

# ── 3. NOTIFICATIONS ──────────────────────────────────────────
print("\n[3] Creating notifications table...")
step("CREATE notifications", """
CREATE TABLE IF NOT EXISTS notifications (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER REFERENCES users(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    title      TEXT NOT NULL,
    message    TEXT NOT NULL,
    is_read    BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX notifications.user_id", """
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id)
WHERE user_id IS NOT NULL
""")
step("INDEX notifications.company_id", """
CREATE INDEX IF NOT EXISTS idx_notif_company ON notifications(company_id)
WHERE company_id IS NOT NULL
""")
step("INDEX notifications.is_read", """
CREATE INDEX IF NOT EXISTS idx_notif_unread ON notifications(is_read) WHERE is_read = false
""")

# ── 4. REVIEWS ────────────────────────────────────────────────
print("\n[4] Creating reviews table...")
step("CREATE reviews", """
CREATE TABLE IF NOT EXISTS reviews (
    id          SERIAL PRIMARY KEY,
    company_id  INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    client_name TEXT NOT NULL,
    project_id  INTEGER REFERENCES projects(id) ON DELETE SET NULL,
    rating      INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("UNIQUE reviews per project", """
CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_project
ON reviews(project_id) WHERE project_id IS NOT NULL
""")
step("INDEX reviews.company_id", """
CREATE INDEX IF NOT EXISTS idx_reviews_company ON reviews(company_id)
""")
step("INDEX reviews.status", """
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status)
""")

# ── 5. REVIEW REPLIES ─────────────────────────────────────────
print("\n[5] Creating review_replies table...")
step("CREATE review_replies", """
CREATE TABLE IF NOT EXISTS review_replies (
    id         SERIAL PRIMARY KEY,
    review_id  INTEGER NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    reply      TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX review_replies.review_id", """
CREATE INDEX IF NOT EXISTS idx_reply_review ON review_replies(review_id)
""")

# ── 6. ACTIVITY LOG ───────────────────────────────────────────
print("\n[6] Creating activity_log table...")
step("CREATE activity_log", """
CREATE TABLE IF NOT EXISTS activity_log (
    id         SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     TEXT NOT NULL,
    metadata   TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT now()
)
""")
step("INDEX activity_log.company_id", """
CREATE INDEX IF NOT EXISTS idx_activity_company ON activity_log(company_id)
WHERE company_id IS NOT NULL
""")
step("INDEX activity_log.user_id", """
CREATE INDEX IF NOT EXISTS idx_activity_user ON activity_log(user_id)
WHERE user_id IS NOT NULL
""")
step("INDEX activity_log.created_at", """
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC)
""")

# ── 7. VERIFY ─────────────────────────────────────────────────
print("\n[7] Verification...")
tables = ["conversations","messages","notifications","reviews","review_replies","activity_log"]
with engine.connect() as c:
    for t in tables:
        cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        cols = c.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name=:t ORDER BY ordinal_position
        """), {"t": t}).scalars().all()
        print(f"  {t}: {cnt} rows — {', '.join(cols)}")

print("\n" + "="*60)
print(f"MIGRATION COMPLETE: {passed} passed, {failed} failed")
print("="*60)
if failed > 0:
    raise SystemExit(1)

