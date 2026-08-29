"""align_timestamp_types

مواءمة أعمدة الوقت مع TIMESTAMPTZ.

قاعدة الإنتاج بُنيت بسكربتات _migrate_phase*.py التي استخدمت TIMESTAMP
بلا منطقة زمنية، بينما الترحيل الأولي ينشئها TIMESTAMPTZ. هذا الترحيل
يوائم الاثنين فتصبح قاعدة قائمة مطابقة تماماً لقاعدة مبنية من الصفر.

على قاعدة جديدة الأعمدة أصلاً TIMESTAMPTZ فالترحيل بلا أثر (idempotent).

Revision ID: a1b2c3d4e5f6
Revises: 313fab49d281
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "313fab49d281"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (جدول، عمود) — كلها إلى TIMESTAMPTZ
_TS_COLUMNS = [
    ("chat_messages", "created_at"),
    ("companies", "subscription_expires_at"),
    ("companies", "updated_at"),
    ("company_members", "created_at"),
    ("company_subscriptions", "created_at"),
    ("company_subscriptions", "expires_at"),
    ("company_subscriptions", "start_date"),
    ("conversations", "created_at"),
    ("notifications", "created_at"),
    ("project_bids", "created_at"),
    ("project_bids", "updated_at"),
    ("project_requests", "created_at"),
    ("project_requests", "updated_at"),
    ("projects", "created_at"),
    ("projects", "updated_at"),
    ("review_replies", "created_at"),
    ("reviews", "created_at"),
    ("security_audit_log", "created_at"),
    ("subscription_plans", "created_at"),
    ("subscription_requests", "created_at"),
    ("subscription_requests", "processed_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
]


def upgrade() -> None:
    for table, column in _TS_COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" '
            f'ALTER COLUMN "{column}" TYPE TIMESTAMPTZ '
            f'USING "{column}"::TIMESTAMPTZ;'
        )

    # companies.created_at كان TEXT في السكربتات القديمة — يحتاج تحويلاً صريحاً.
    op.execute(
        'ALTER TABLE "companies" '
        'ALTER COLUMN "created_at" TYPE TIMESTAMPTZ '
        'USING NULLIF("created_at"::TEXT, \'\')::TIMESTAMPTZ;'
    )

    # يجعل ON CONFLICT (name_ar) في زرع التصنيفات فعّالاً، ويمنع التكرار.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS categories_name_ar_key "
        "ON categories (name_ar);"
    )

    # عمود مفقود في القواعد المبنية بالسكربتات القديمة.
    op.execute('ALTER TABLE "companies" ADD COLUMN IF NOT EXISTS image_url TEXT;')


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS categories_name_ar_key;")
    for table, column in _TS_COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" '
            f'ALTER COLUMN "{column}" TYPE TIMESTAMP '
            f'USING "{column}"::TIMESTAMP;'
        )
    op.execute(
        'ALTER TABLE "companies" ALTER COLUMN "created_at" TYPE TEXT '
        'USING "created_at"::TEXT;'
    )
