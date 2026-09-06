"""حذف project_requests بلا رجعة — نظام سابق حلّ محلّه سوق /projects

صفر صفّ في تاريخ الإنتاج كله (جدول لم يُستخدم قطّ)، ولا نداء أو
رابط واحد إليه من أي صفحة عامة في public/ — POST /project-requests
وGET /admin/project-requests كانا يعملان بلا أي مستهلك حقيقي.
سوق المشاريع الحالي (جدول projects · project_bids) حلّ محلّه
تماماً قبل أن يُنظَّف خلفه.

طلب عرض سعر موجَّه لشركة بعينها ما زال مؤجَّلاً (FAST-TRACK.md،
SCOPE.md) — يُبنى نظيفاً على معمار profiles/RBAC حين يحين دوره،
لا بترميم هذا الهيكل الميت.

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-07
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS project_requests;")


def downgrade() -> None:
    op.execute("""
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
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
