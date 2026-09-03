"""توثيق companies.owner_user_id · حماية رسائل الطرف الباقي عند حذف حساب

١ · companies.owner_user_id يحمل قيد FK على الإنتاج فعلاً (أُضيف
    يدوياً خارج Alembic في وقت ما — لا وجود له في أي ترحيل سابق)،
    بلا ON DELETE. بيئة جديدة تُبنى من هذه السلسلة تفتقده تماماً:
    DELETE FROM users ينجح عليها ويفشل بصمت على الإنتاج إن كان
    المستخدم يملك شركة (حتى شركة مُصفَّرة الحالة deleted، فسجلّها
    نفسه لا يُحذف — main.py: delete_account لا يحذف صفّ الشركة).
    فوعد "تُحذف خلال ٣٠ يوماً" (LEGAL-DRAFT §٥) لا يتحقّق لأي
    حساب كان صاحب شركة — يفشل purge_deleted_accounts صامتاً.
    صار SET NULL: تُفصَل الملكية بلا كسر مرجعي، والشركة تبقى بحالتها
    المحذوفة كما ضبطها الطلب.

٢ · conversations.client_user_id كانت ON DELETE CASCADE — حذف
    العميل نهائياً كان يمحو محادثاته بالتتالي، ثم CASCADE ثانية
    (messages_conversation_id_fkey) يمحو رسائل المحادثة كلها —
    بما فيها ردود الشركة. يخالف حرفياً "رسائلك تبقى في نسخة
    المستلم" (الخصوصية §٦). صار SET NULL: المحادثة ورسائلها
    تبقى سليمة، وهويّة العميل وحدها تُفصَل — الشركة تراها بعدها
    منسوبة إلى «حساب محذوف»، تماماً كتجهيل التقييمات بالاسم.

Revision ID: c9d0e1f2a3b4
Revises: a7b8c9d0e1f2
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "c9d0e1f2a3b4"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── companies.owner_user_id ──────────────────────────────────
    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_owner_user_id_fkey;")
    op.execute("""
        ALTER TABLE companies
        ADD CONSTRAINT companies_owner_user_id_fkey
        FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE SET NULL;
    """)

    # ── conversations.client_user_id ─────────────────────────────
    op.execute("ALTER TABLE conversations ALTER COLUMN client_user_id DROP NOT NULL;")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_client_user_id_fkey;")
    op.execute("""
        ALTER TABLE conversations
        ADD CONSTRAINT conversations_client_user_id_fkey
        FOREIGN KEY (client_user_id) REFERENCES users(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    # لا يُعاد NOT NULL — صفوف قد تحمل NULL فعلاً من استعمال حقيقي
    # بعد هذا الترحيل، وإجباره يفشل أو يخترع قيمة. القيد وحده يعود.
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_client_user_id_fkey;")
    op.execute("""
        ALTER TABLE conversations
        ADD CONSTRAINT conversations_client_user_id_fkey
        FOREIGN KEY (client_user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)

    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_owner_user_id_fkey;")
    op.execute("""
        ALTER TABLE companies
        ADD CONSTRAINT companies_owner_user_id_fkey
        FOREIGN KEY (owner_user_id) REFERENCES users(id);
    """)
