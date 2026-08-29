"""rate_limits_table

جدول تحديد المعدّل — المهمة 1.4

كان العدّاد قاموساً في ذاكرة العملية، فينهار مع عدة عمّال
(gunicorn -w 4 يعني أربع عمليات، كل واحدة بعدّادها، فيصير
حدّ «5 محاولات» فعلياً 20)، ويُصفَّر عند كل إعادة تشغيل.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-29
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            key          TEXT PRIMARY KEY,
            hits         INTEGER     NOT NULL DEFAULT 0,
            window_start TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limits_window "
        "ON rate_limits (window_start);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_rate_limits_window;")
    op.execute("DROP TABLE IF EXISTS rate_limits;")
