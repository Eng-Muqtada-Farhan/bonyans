"""حذف companies.subscription_plan — عمود ميت

المصدر الوحيد للباقة هو company_subscriptions المرتبط بـ
subscription_plans، وهو ما يقرؤه get_company_plan لكل قرار
(حدّ فرص المشاريع، أولوية البحث، الظهور المميز).

العمود المحذوف كان يُكتب في ثلاثة مواضع ولا يُقرأ في أي قرار،
فصار نسخةً ثانيةً تفترق عن الحقيقة بصمت: صفٌّ مكتوب فيه
'partner' بينما لا اشتراك فعّالاً له، والخادم يعامله كـ starter.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_companies_subscription_plan;")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS subscription_plan;")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE companies "
        "ADD COLUMN IF NOT EXISTS subscription_plan TEXT NOT NULL DEFAULT 'free';"
    )
    # يُعاد ملؤه من المصدر الحقيقي لا بقيمة مخترعة
    op.execute("""
        UPDATE companies c
        SET subscription_plan = sp.code
        FROM company_subscriptions cs
        JOIN subscription_plans sp ON sp.id = cs.plan_id
        WHERE cs.company_id = c.id
          AND cs.status = 'active'
          AND (cs.expires_at IS NULL OR cs.expires_at > now());
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_companies_subscription_plan "
        "ON companies(subscription_plan);"
    )
