"""رمز تفعيل من ٦ خانات بجانب الرابط — لا بدله

الرابط وحده لا يكفي: التطبيق (Capacitor لاحقاً) لا يستطيع فتح
رابط بريد بسهولة، والرمز يُكتب داخل الواجهة مباشرة. مدّتان
مختلفتان عمداً:

  الرابط  — ٢٤ ساعة (VERIFY_TTL القائمة). يتحمّل مستخدماً يسجّل من
            الجوّال وينقر الرابط من بريد سطح المكتب بعد ساعات.
  الرمز   — ١٥ دقيقة. يُكتب في نفس الجلسة التي سجّل فيها المستخدم
            وهو ما زال ينظر إلى بريده الوارد — نافذة أقصر تُقلِّل
            أثر رمز مسروق (سكرين شوت، جهاز مشترك) بلا فائدة
            تُذكَر من إطالتها لمستخدم يستعمله فوراً أصلاً.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-09-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE email_tokens
            ADD COLUMN IF NOT EXISTS code_hash       TEXT,
            ADD COLUMN IF NOT EXISTS code_expires_at  TIMESTAMPTZ;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE email_tokens
            DROP COLUMN IF EXISTS code_hash,
            DROP COLUMN IF EXISTS code_expires_at;
    """)
