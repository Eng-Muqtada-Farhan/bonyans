"""سلسلة البريد: استعادة كلمة المرور · التفعيل · تغيير البريد

جدولان لا ثلاثة:

  password_resets — يُثبت أنك تملك كلمة مرور هذا الحساب
  email_tokens    — يُثبت أنك تملك عنوان البريد هذا
                    (purpose: verify | change)

الفصل دلالي لا شكلي: الأول يفتح تغيير كلمة المرور، والثاني يُثبت
ملكية عنوان. دمجهما يعني رمزاً واحداً يصلح للأمرين — وهو ما لا
نريده أبداً.

الحسابات القائمة تُعتبر مُفعَّلة (قرار صاحب المشروع ١ أيلول
٢٠٢٦): أُنشئت قبل وجود التحقّق فلا يمكنها التفعيل بأثر رجعي،
وقفلها يقفل حساب صاحب المشروع نفسه. التحقّق يسري على التسجيلات
الجديدة وحدها.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-01
"""
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # الرمز لا يُخزَّن نصّاً: من قرأ الجدول لا يستطيع انتحال أحد.
    op.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  TEXT    NOT NULL UNIQUE,
            expires_at  TIMESTAMPTZ NOT NULL,
            used_at     TIMESTAMPTZ,
            ip_hash     TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS password_resets_user_idx ON password_resets(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS password_resets_exp_idx ON password_resets(expires_at);")

    op.execute("""
        CREATE TABLE IF NOT EXISTS email_tokens (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            purpose     TEXT    NOT NULL CHECK (purpose IN ('verify', 'change')),
            token_hash  TEXT    NOT NULL UNIQUE,
            new_email   TEXT,
            expires_at  TIMESTAMPTZ NOT NULL,
            used_at     TIMESTAMPTZ,
            ip_hash     TEXT,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            -- تغيير بلا عنوان جديد لا معنى له
            CONSTRAINT email_tokens_change_shape CHECK (
                purpose <> 'change' OR new_email IS NOT NULL
            )
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS email_tokens_user_idx ON email_tokens(user_id, purpose);")
    op.execute("CREATE INDEX IF NOT EXISTS email_tokens_exp_idx ON email_tokens(expires_at);")

    # الحسابات القائمة مُفعَّلة — التحقّق للتسجيلات الجديدة وحدها
    op.execute("UPDATE users SET is_email_verified = true WHERE is_email_verified = false;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_tokens;")
    op.execute("DROP TABLE IF EXISTS password_resets;")
    # لا نُعيد is_email_verified إلى false: لا سبيل لمعرفة من كان
    # مُفعَّلاً قبل الترحيل، وإرجاع الجميع يقفل حسابات صالحة.
