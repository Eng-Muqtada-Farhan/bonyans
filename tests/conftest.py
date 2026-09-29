"""
اختبارات الدخان — بُنيان
═══════════════════════════════════════════════════════════════

بوابة إلزامية قبل كتابة أي كود يمحو بيانات مستخدم نهائياً
(المرحلة ج في ROADMAP.md). بلا شبكة أمان لا يُكتب كود لا رجعة فيه.

القاعدة تُلمَس عند الطلب لا إجبارياً — fixture db (أدناه) هو
البوابة الصريحة الوحيدة. اختبار لا يطلبه لا يلمس الشبكة إطلاقاً،
مهما كانت حالة TEST_DATABASE_URL (غائباً، معطوباً، أو فرع Neon
معلَّقاً). هذا مقصود: عطل شبكة في فرع الاختبار لا يجوز أن يُسقط
اختبارات أمامية بحتة (manifest، نصوص صفحات، منطق JS ثابت) لا علاقة
لها بأي قاعدة بيانات — وهذا بالضبط ما وقع قبل هذا التغيير.

⛔ db() يرفض العمل إن غاب TEST_DATABASE_URL أو طابق DATABASE_URL —
لا تفحص ENVIRONMENT: ذاك متغيّر محلّي بلا صلة بأيّ قاعدة تتصل بها
هذه العملية فعلياً. لكن الرفض الآن عند الطلب الفعلي لا عند جمع
الاختبارات — sys.exit() القديم كان يُسقط حتى الاختبارات الأمامية
البحتة لو غاب TEST_DATABASE_URL، وهذا عين ما يُصلحه هذا التغيير.

تعمل على فرع Neon مستقلّ باسم test (راجع README_LAUNCH.md لإنشائه)
لا على القاعدة التي يخدمها الموقع، فكل صف تنشئه تحمل اسمه بادئة
SMOKE_ ويُحذف في التفكيك — بما فيه صفوف rate_limits التي تخلّفها
اختبارات الحدّ.

الاختبارات التي تلمس قاعدة البيانات (مباشرة عبر main.SessionLocal،
أو عبر admin_token/company_token/user_token/company_cookie_token/db)
تحمل علامة @pytest.mark.needs_db — سجَّلة في pytest.ini. شغّل
`pytest -m "not needs_db"` لتشغيل المجموعة الأمامية البحتة بلا أي
اتصال شبكي على الإطلاق، حتى لو كان TEST_DATABASE_URL معطوباً تماماً.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

_PROD_DB_URL = os.getenv("DATABASE_URL", "")
_TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "")

# إحلال DATABASE_URL بفرع test فقط إن كان موجوداً فعلاً — main.py
# يبني محرّكه من DATABASE_URL عند استيراده، والمحرّك كسول (لا يتّصل
# قبل أول استعلام حقيقي)، فهذا الإحلال بلا تكلفة شبكية بحدّ ذاته
# سواء أشار الرابط الناتج إلى فرع صالح أو معطوب. لو تُرك
# TEST_DATABASE_URL فارغاً، يبقى DATABASE_URL الحقيقي من .env كما
# هو (لا يُفرَغ فيُكسِر استيراد main.py بـ RuntimeError) — أي
# اختبار لا يطلب db() لاحقاً لن يستعلم مطلقاً، وأي اختبار يطلبه
# سيُرفَض بوضوح داخل الـ fixture قبل أي استعلام فعلي.
if _TEST_DB_URL:
    os.environ["DATABASE_URL"] = _TEST_DB_URL

# حلقة التطهير الخلفية (main.lifespan) لا تعمل هنا — اختبارات
# التطهير تستدعي main.purge_deleted_accounts()/run_purge_job()
# مباشرةً بأزمنة مصطنعة، ولا تريد حلقة حقيقية تتنافس معها على
# القفل الاستشاري نفسه أو تكتب إلى job_runs في توقيت غير متوقَّع.
os.environ["DISABLE_PURGE_LOOP"] = "1"

# كلمة مرور إدارة للاختبار وحده — تُحقَن في البيئة قبل استيراد
# main حتى لا تلمس ADMIN_PASSWORD_HASH الحقيقية ولا تُطبع أبداً.
SMOKE_ADMIN_PASSWORD = "smoke-test-only-Aa1!"

import bcrypt  # noqa: E402

os.environ["ADMIN_PASSWORD_HASH"] = bcrypt.hashpw(
    SMOKE_ADMIN_PASSWORD.encode(), bcrypt.gensalt()
).decode()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import main  # noqa: E402

# البريد مُعطَّل قسراً في الاختبارات — بعد هذا السطر لا قبله، لأن
# main.py يستدعي load_dotenv() ثانيةً عند استيراده، وdotenv يملأ
# أي متغيّر غائب من .env (override=False لا يمنع ملء الغائب) —
# فحذفه قبل import main يُعاد تلقائياً. بلا هذا، اختبارات استعادة
# كلمة المرور وتغيير البريد ترسل بريداً فعلياً إلى عناوين
# seed.test المصطنعة، وهو نطاق محجوز للاختبار (RFC 2606) لا
# يستقبل شيئاً — فيرتدّ البريد ارتداداً صلباً على نطاق مُرسِل
# عمره أيام، ويضرّ سمعته. الاختبارات تفحص المنطق والأمان لا
# مزوّد الطرف الثالث.
os.environ.pop("RESEND_API_KEY", None)

SMOKE_PREFIX = "SMOKE_"


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as c:
        yield c


def _wipe_rate_limits():
    try:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'login:%'"))
            db.commit()
    except Exception:
        pass


@pytest.fixture(scope="session")
def _smoke_cleanup_registered():
    """
    تنظيف صفوف SMOKE_ عند نهاية الجلسة — مرّة واحدة، وفقط إن طلبه
    اختبار واحد على الأقل عبر db() (لم يعد autouse). جلسة لا يطلب
    فيها أي اختبار db() لا تُنفِّذ هذه الدالّة إطلاقاً، فلا تلمس
    الشبكة لاختبارات أمامية بحتة.
    """
    yield
    with main.SessionLocal() as db:
        db.execute(
            text("DELETE FROM companies WHERE name LIKE :p"), {"p": SMOKE_PREFIX + "%"}
        )
        db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'login:%'"))
        db.commit()


@pytest.fixture(scope="session")
def _db_guard(_smoke_cleanup_registered):
    """
    الحارس نفسه (رفض TEST_DATABASE_URL الغائب أو المطابق للإنتاج) —
    عند الطلب الفعلي فقط، لا عند جمع الاختبارات. جلسة واحدة فقط
    (لا تكلفة تكرار)؛ db() (لكل اختبار) وrموز الأدوار الثلاثة كلّها
    تعتمده، فيُفحَص مرّة ويُطبَّق على الجميع.
    """
    if not _TEST_DB_URL:
        pytest.fail(
            "⛔ TEST_DATABASE_URL غائب عن .env — هذا الاختبار يحتاج فرع "
            "Neon مستقلّ (راجع README_LAUNCH.md). اختبارات لا تطلب db() "
            "أو رموز الأدوار غير متأثّرة.",
            pytrace=False,
        )
    if _TEST_DB_URL == _PROD_DB_URL:
        pytest.fail(
            "⛔ TEST_DATABASE_URL يطابق DATABASE_URL حرفياً — ليس فرعاً "
            "مستقلاً بل القاعدة الحيّة نفسها تحت اسم آخر (راجع "
            "README_LAUNCH.md).",
            pytrace=False,
        )
    yield


@pytest.fixture
def db(_db_guard):
    """
    البوابة الصريحة الوحيدة لأي اختبار يلمس قاعدة البيانات مباشرة
    (main.SessionLocal في جسم الاختبار نفسه) — تُطلَب بالاسم. اختبار
    لا يطلبه (ولا يطلب admin_token/company_token/user_token/
    company_cookie_token، التي تعتمد _db_guard أيضاً) لا يُنفِّذ
    سطراً واحداً هنا ولا يلمس الشبكة، بصرف النظر عن حالة
    TEST_DATABASE_URL.
    """
    _wipe_rate_limits()
    yield
    _wipe_rate_limits()


# ── رموز الأدوار الثلاثة ──────────────────────────────────────────────────────
# جلسة كاملة (تسجّل الدخول مرّة واحدة) فتعتمد _db_guard لا db()
# القائم على كل اختبار (تعارض نطاق: fixture جلسة لا يجوز أن يعتمد
# fixture لكل اختبار). db() يبقى ضرورياً فقط لاختبار يستعلم القاعدة
# مباشرة في جسمه هو، لا لمن يكتفي برمز جاهز.

@pytest.fixture(scope="session")
def admin_token(client, _db_guard):
    r = client.post("/login", json={"username": main.ADMIN_USERNAME,
                                    "password": SMOKE_ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    _wipe_rate_limits()
    return r.json()["token"]


@pytest.fixture(scope="session")
def company_token(client, _db_guard):
    r = client.post("/company/login", json={"email": "company@seed.test",
                                            "password": "SeedTest!2026"})
    assert r.status_code == 200, "تحتاج بيانات البذر: python seed_dev.py"
    _wipe_rate_limits()
    return r.json()["token"]


@pytest.fixture(scope="session")
def user_token(client, _db_guard):
    r = client.post("/auth/login", json={"email": "client@seed.test",
                                         "password": "SeedTest!2026"})
    assert r.status_code == 200, "تحتاج بيانات البذر: python seed_dev.py"
    _wipe_rate_limits()
    return r.json()["token"]
