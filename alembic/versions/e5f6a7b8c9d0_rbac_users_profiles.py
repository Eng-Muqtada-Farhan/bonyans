"""توحيد المصادقة: users + profiles

ثلاثة أنظمة مصادقة تصير واحداً.

قبل:
  company_users   — حساب شركة (بريد + كلمة مرور) منفصل تماماً
  users           — حساب صاحب مشروع (بريد + كلمة مرور)
  company_members — ربط user بشركة، بدور owner/member

الثمن: استعادة كلمة المرور كانت ستُبنى ثلاث مرات، وتفعيل البريد
ثلاث مرات، وكل ثغرة تُصلَح ثلاث مرات — وتُنسى مرة.

بعد:
  users    — الهوية وبيانات الاعتماد. صفّ واحد لكل إنسان.
  profiles — الأدوار. صفّ لكل ربط (مستخدم، دور)، ومعه company_id
             حين يكون الدور 'company'.

نقل البيانات:
  · كل صفّ في company_users يصير مستخدماً في users (أو يُربط
    بمستخدم قائم إن تطابق البريد — لا نُنشئ ازدواجاً) + ملفّاً
    بدور 'company'
  · كل صفّ في company_members يصير ملفّاً بدور 'company' مع
    company_role من عموده role
  · كل مستخدم بلا ربط شركة يأخذ ملفّاً بدور 'client'

الجدولان القديمان يبقيان بلا حذف في هذا الترحيل: الحذف بعد أن
يُثبت النظام الجديد نفسه في التشغيل. downgrade يعيد القراءة إليهما.

المدير يبقى خارج الجدول: كلمة مروره في .env، ونسخها إلى صفّ في
قاعدة البيانات تُنشئ مصدرين للحقيقة — وهو الداء نفسه الذي يعالجه
هذا الترحيل.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-01
"""
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role         TEXT    NOT NULL CHECK (role IN ('client', 'company')),
            company_id   INTEGER REFERENCES companies(id) ON DELETE CASCADE,
            company_role TEXT,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            -- دور 'company' بلا شركة لا معنى له، و'client' بشركة تناقض
            CONSTRAINT profiles_company_shape CHECK (
                (role = 'company' AND company_id IS NOT NULL) OR
                (role = 'client'  AND company_id IS NULL)
            )
        );
    """)
    # مستخدم واحد لا يحمل الدور نفسه على الشركة نفسها مرتين
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS profiles_user_role_company_uq
        ON profiles (user_id, role, COALESCE(company_id, 0));
    """)
    op.execute("CREATE INDEX IF NOT EXISTS profiles_user_idx ON profiles(user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS profiles_company_idx ON profiles(company_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uq ON users(lower(email));")

    # ١ · حسابات الشركات ← users (بلا ازدواج لو تطابق البريد)
    op.execute("""
        INSERT INTO users (email, display_name, provider, provider_id, password_hash,
                           is_email_verified, is_phone_verified, is_active,
                           created_at, updated_at)
        SELECT lower(cu.email),
               COALESCE(c.name, lower(cu.email)),
               COALESCE(cu.provider, 'local'),
               cu.provider_id,
               cu.password_hash,
               false, false, cu.is_active,
               cu.created_at, cu.updated_at
        FROM company_users cu
        LEFT JOIN companies c ON c.id = cu.company_id
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE lower(u.email) = lower(cu.email)
        );
    """)

    # ٢ · ملفّات الشركات من company_users
    op.execute("""
        INSERT INTO profiles (user_id, role, company_id, company_role, created_at)
        SELECT u.id, 'company', cu.company_id, 'owner', cu.created_at
        FROM company_users cu
        JOIN users u ON lower(u.email) = lower(cu.email)
        ON CONFLICT DO NOTHING;
    """)

    # ٣ · ملفّات الشركات من company_members (عضويات موجودة)
    op.execute("""
        INSERT INTO profiles (user_id, role, company_id, company_role, created_at)
        SELECT cm.user_id, 'company', cm.company_id,
               COALESCE(cm.role, 'member'), cm.created_at
        FROM company_members cm
        JOIN users u ON u.id = cm.user_id
        ON CONFLICT DO NOTHING;
    """)

    # ٤ · من لا ربط شركة له فهو صاحب مشروع
    op.execute("""
        INSERT INTO profiles (user_id, role, company_id, company_role, created_at)
        SELECT u.id, 'client', NULL, NULL, u.created_at
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM profiles p WHERE p.user_id = u.id AND p.role = 'company'
        )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    # الجدولان القديمان لم يُحذفا، فالرجوع يقتصر على إسقاط الجديد.
    op.execute("DROP INDEX IF EXISTS profiles_user_role_company_uq;")
    op.execute("DROP INDEX IF EXISTS profiles_user_idx;")
    op.execute("DROP INDEX IF EXISTS profiles_company_idx;")
    op.execute("DROP INDEX IF EXISTS users_email_lower_uq;")
    op.execute("DROP TABLE IF EXISTS profiles;")
