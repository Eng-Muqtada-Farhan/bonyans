"""إخفاء إداري للمشاريع — حالة منفصلة لا يملكها صاحب المشروع

closed/cancelled حالتان يملكهما صاحب المشروع مفهومياً (سيغلق/يلغي
مشروعه بنفسه حين يُبنى ذلك المسار). لو استُعملت closed للإخفاء
الإداري، يستطيع صاحب مشروع نظرياً إعادة نشره ببساطة فيُبطل قرار
المدير — فالإخفاء الإداري يحتاج قيمة status لا يصل إليها المالك
من أي مسار يملكه، ولا حتى PUT /admin/projects/{id}/status العامّة
(محجوبة عمداً عن admin_hidden، انظر main.py). عمودان جديدان يحفظان
السبب ووقته للعرض في لوحة الإدارة ولرسالة البريد.

Revision ID: b7c8d9e0f1a2
Revises: e1f2a3b4c5d6
Create Date: 2026-09-06
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE projects
            ADD COLUMN IF NOT EXISTS admin_hidden_reason TEXT,
            ADD COLUMN IF NOT EXISTS admin_hidden_at      TIMESTAMPTZ;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE projects
            DROP COLUMN IF EXISTS admin_hidden_reason,
            DROP COLUMN IF EXISTS admin_hidden_at;
    """)
