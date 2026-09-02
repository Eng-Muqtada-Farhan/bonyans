"""شروط المتجرين: الموافقة القانونية · حذف الحساب · الإبلاغ والحجب

ثلاثة شروط نشر في متجرَي التطبيقات:
  · موافقة موثَّقة على الشروط والخصوصية (وقتها ونسخة الوثيقة)
  · حذف الحساب من داخل التطبيق (Apple ٥٫١٫١)
  · الإبلاغ والحجب على المحتوى الذي ينشره المستخدمون (Apple ١٫٢)

سياسة الحذف من LEGAL-DRAFT.md §٥ و§٦:
  · بيانات الحساب تُحذف خلال ٣٠ يوماً
  · سجلّ التدقيق يبقى مجهَّلاً ١٢ شهراً
  · التقييمات تُجهَّل ولا تُحذف — حذفها يشوّه سمعة قُدِّرت بها شركة
  · الرسائل تبقى في نسخة المستلم كما في أي محادثة

فلذلك الحذف على مرحلتين: تجهيل فوري (يفقد الحساب هويته ونفاذه
لحظة الطلب) ثم محو نهائي بعد ٣٠ يوماً. الحذف الفوري الكامل
يخالف السياسة المكتوبة ويُفقد الطرف الآخر سجلّه.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-02
"""
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ١ · الموافقة القانونية ──────────────────────────────────────
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS terms_version     TEXT;
    """)
    # الحسابات القائمة سجّلت قبل وجود المربّع — لا نخترع لها موافقة.
    # تبقى NULL، ويُطلب منها القبول عند أول دخول بعد النشر.

    # ── ٢ · حذف الحساب ──────────────────────────────────────────────
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deletion_requested_at TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS anonymized_at         TIMESTAMPTZ;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS users_deletion_idx
        ON users(deletion_requested_at) WHERE deletion_requested_at IS NOT NULL;
    """)

    # ── ٣ · البلاغات ────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id            SERIAL PRIMARY KEY,
            reporter_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
            target_type   TEXT NOT NULL CHECK (
                              target_type IN ('company', 'project', 'review', 'message')),
            target_id     INTEGER NOT NULL,
            reason        TEXT NOT NULL,
            details       TEXT,
            status        TEXT NOT NULL DEFAULT 'open'
                              CHECK (status IN ('open', 'actioned', 'dismissed')),
            resolved_at   TIMESTAMPTZ,
            resolved_note TEXT,
            ip_hash       TEXT,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS reports_status_idx ON reports(status, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS reports_target_idx ON reports(target_type, target_id);")
    # بلاغ واحد لكل مستخدم على الهدف نفسه — التكرار ضجيج لا إشارة
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS reports_once_uq
        ON reports (reporter_id, target_type, target_id)
        WHERE reporter_id IS NOT NULL;
    """)

    # ── ٤ · الحجب ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            id          SERIAL PRIMARY KEY,
            blocker_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            blocked_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT blocks_not_self CHECK (blocker_id <> blocked_id)
        );
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS blocks_pair_uq
        ON blocks (blocker_id, blocked_id);
    """)
    op.execute("CREATE INDEX IF NOT EXISTS blocks_blocked_idx ON blocks(blocked_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS blocks;")
    op.execute("DROP TABLE IF EXISTS reports;")
    op.execute("DROP INDEX IF EXISTS users_deletion_idx;")
    op.execute("""
        ALTER TABLE users
            DROP COLUMN IF EXISTS anonymized_at,
            DROP COLUMN IF EXISTS deletion_requested_at,
            DROP COLUMN IF EXISTS terms_version,
            DROP COLUMN IF EXISTS terms_accepted_at;
    """)
