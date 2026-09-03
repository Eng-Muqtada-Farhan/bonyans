"""
اختبارات الدخان — بُنيان
═══════════════════════════════════════════════════════════════

بوابة إلزامية قبل كتابة أي كود يمحو بيانات مستخدم نهائياً
(المرحلة ج في ROADMAP.md). بلا شبكة أمان لا يُكتب كود لا رجعة فيه.

⛔ ترفض العمل عندما ENVIRONMENT=production.

تعمل على قاعدة التطوير نفسها لأن المخطط فيها هو المرجع، فكل صف
تنشئه تحمل اسمه بادئة SMOKE_ ويُحذف في التفكيك — بما فيه صفوف
rate_limits التي تخلّفها اختبارات الحدّ.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

if os.getenv("ENVIRONMENT", "development") == "production":
    sys.exit("⛔ رُفض: اختبارات الدخان للتطوير المحلي فقط، و ENVIRONMENT=production.")

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


@pytest.fixture(autouse=True)
def _clean_rate_limits():
    """
    عدّاد الحدّ في قاعدة البيانات مشترك بين الاختبارات، وTestClient
    يستعمل عنوان IP واحداً. بلا تنظيف يُحجب أول اختبار دخول ما بعد
    الخامس، فتفشل اختبارات لا علاقة لها بالحدّ.
    """
    _wipe_rate_limits()
    yield
    _wipe_rate_limits()


def _wipe_rate_limits():
    try:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'login:%'"))
            db.commit()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _cleanup_smoke_rows():
    yield
    with main.SessionLocal() as db:
        db.execute(
            text("DELETE FROM companies WHERE name LIKE :p"), {"p": SMOKE_PREFIX + "%"}
        )
        db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'login:%'"))
        db.commit()


# ── رموز الأدوار الثلاثة ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def admin_token(client):
    r = client.post("/login", json={"username": main.ADMIN_USERNAME,
                                    "password": SMOKE_ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    _wipe_rate_limits()
    return r.json()["token"]


@pytest.fixture(scope="session")
def company_token(client):
    r = client.post("/company/login", json={"email": "company@seed.test",
                                            "password": "SeedTest!2026"})
    assert r.status_code == 200, "تحتاج بيانات البذر: python seed_dev.py"
    _wipe_rate_limits()
    return r.json()["token"]


@pytest.fixture(scope="session")
def user_token(client):
    r = client.post("/auth/login", json={"email": "client@seed.test",
                                         "password": "SeedTest!2026"})
    assert r.status_code == 200, "تحتاج بيانات البذر: python seed_dev.py"
    _wipe_rate_limits()
    return r.json()["token"]
