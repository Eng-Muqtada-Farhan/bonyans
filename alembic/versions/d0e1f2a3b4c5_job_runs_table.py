"""job_runs — سجلّ تشغيل المهام الدورية

purge_deleted_accounts() كانت معرَّفة ولا يستدعيها شيء — لا مُجدوِل
ولا حدث بدء تشغيل، فوعد «تُحذف خلال ٣٠ يوماً» (الخصوصية §٥) لا
يتحقّق أبداً في الإنتاج. صار main.py يشغّلها عبر حلقة asyncio تُعاد
كل بضع ساعات، لكن حلقة كهذه بلا سجلّ تبقى ادّعاءً آخر لا يُتحقَّق
منه. هذا الجدول هو ذلك السجلّ: صفّ واحد لكل محاولة تشغيل، ناجحة
كانت أو فاشلة، فآخر تشغيل قابل للقراءة بدل الثقة العمياء بأن
الحلقة تعمل.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS job_runs (
            id            SERIAL PRIMARY KEY,
            job_name      TEXT        NOT NULL,
            ran_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
            status        TEXT        NOT NULL,   -- 'ok' | 'error' | 'skipped_locked'
            purged_count  INTEGER     NOT NULL DEFAULT 0,
            error         TEXT
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_runs_name_time "
        "ON job_runs (job_name, ran_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_job_runs_name_time;")
    op.execute("DROP TABLE IF EXISTS job_runs;")
