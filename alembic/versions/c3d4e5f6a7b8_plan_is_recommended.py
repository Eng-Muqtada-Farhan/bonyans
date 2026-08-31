"""plan_is_recommended

عمود توصية المنصّة على الباقات.

كانت الواجهة تعرض شارة «الأكثر اختياراً» — وهي ادّعاء عن سلوك
مشتركين لا وجود لهم (company_subscriptions فيه صفر صف). القاعدة
في DESIGN.md §٥·٥ تمنع ذلك.

البديل عمود صريح يضبطه المدير، والشارة تقول «توصيتنا»: رأي منسوب
إلى المنصّة لا إحصاء مختلَق. يُستبدَل بإحصاء حقيقي حين يوجد
مشتركون فعليون.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE subscription_plans "
        "ADD COLUMN IF NOT EXISTS is_recommended BOOLEAN NOT NULL DEFAULT FALSE;"
    )
    # توصية ابتدائية: الباقة المميّزة. يغيّرها المدير متى شاء.
    op.execute("UPDATE subscription_plans SET is_recommended = FALSE;")
    op.execute("UPDATE subscription_plans SET is_recommended = TRUE WHERE code = 'featured';")


def downgrade() -> None:
    op.execute("ALTER TABLE subscription_plans DROP COLUMN IF EXISTS is_recommended;")
