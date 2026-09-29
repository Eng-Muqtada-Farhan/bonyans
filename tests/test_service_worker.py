"""
اختبار عامل الخدمة — عزل الأسطح عند انقطاع الشبكة
═══════════════════════════════════════════════════════════════
الجولة أ، البند ٥. لا يمكن اختبار fetch handler لعامل خدمة عبر
TestClient (لا متصفّح ولا تنفيذ JS) — هذا الاختبار الوحيد في
المجموعة الذي يشغّل خادماً حقيقياً على منفذ TCP ومتصفّحاً فعلياً
(Playwright/Chromium) ليثبت السلوك كما يراه مستخدم حقيقي:
انقطاع الشبكة داخل /app لا يُعيد الموقع العام كبديل.
"""
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from sqlalchemy import text

import main

ROOT = Path(__file__).resolve().parent.parent

try:
    from playwright.sync_api import sync_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    _HAS_PLAYWRIGHT = False


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server():
    """
    خادم uvicorn حقيقي على منفذ محلّي — عامل الخدمة يحتاج HTTP
    فعلياً، لا استدعاء داخل العملية كـTestClient.

    فحص الجاهزية يطلب /manifest.json (ملفّ ثابت) لا /health —
    /health يفحص الاتصال بقاعدة البيانات فعلياً (main.py:
    health_check) ويردّ 503 إن تعذّر، فيُخفق فحص الجاهزية أبداً حين
    تكون القاعدة معطوبة حتى لو كان الخادم نفسه يعمل تماماً ولا
    يحتاجها أي اختبار هنا (test_66/67/97/98 صفحات ثابتة بحتة).
    منفذ TCP يستجيب لملفّ ثابت كافٍ لإثبات أن uvicorn جاهز.
    """
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT),
    )
    base = f"http://127.0.0.1:{port}"
    try:
        ok = False
        for _ in range(100):
            try:
                urllib.request.urlopen(base + "/manifest.json", timeout=0.5)
                ok = True
                break
            except Exception:
                time.sleep(0.2)
        if not ok:
            proc.terminate()
            pytest.fail("الخادم الحيّ لم يستجب — تعذّر اختبار عامل الخدمة")
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@pytest.fixture(scope="module")
def company_cookie_token(_db_guard):
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles WHERE role='company' ORDER BY created_at LIMIT 1"
        )).scalar()
        uid = db.execute(text(
            "SELECT user_id FROM profiles WHERE company_id=:c AND role='company' "
            "ORDER BY created_at LIMIT 1"
        ), {"c": cid}).scalar()
    assert cid and uid, "تحتاج بيانات البذر: python seed_dev.py"
    return main.create_token(main.ROLE_COMPANY, uid)


@pytest.mark.needs_db
@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_47_offline_inside_app_does_not_serve_public_site(live_server, company_cookie_token):
    """
    زيارة أولى تسجّل عامل الخدمة، ثم انقطاع شبكة، ثم تنقّل إلى
    صفحة /app لم تُزَر من قبل (فلا نسخة مخزَّنة لها تحديداً) —
    يجب أن تظهر صفحة بديلة محايدة، لا الصفحة الرئيسية العامة.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(base_url=live_server)
        context.add_cookies([{
            "name": "bn_sess", "value": company_cookie_token,
            "url": live_server, "httpOnly": True, "sameSite": "Lax",
        }])
        page = context.new_page()

        # التسجيل يقع من صفحات الموقع العام فقط (نطاقه '/' يحكم
        # كل شيء) — يطابق كيف يُسجَّل فعلياً في التطبيق الحقيقي.
        page.goto(f"{live_server}/index.html")
        page.wait_for_function(
            "navigator.serviceWorker.controller !== null", timeout=15000
        )
        page.goto(f"{live_server}/app/index.html")

        context.set_offline(True)
        resp = page.goto(f"{live_server}/app/settings.html")
        body = page.content()
        context.set_offline(False)
        browser.close()

    assert resp.status == 503, f"توقّعت 503 (صفحة بديلة)، وصل {resp.status}"
    assert "لا يوجد اتصال" in body, "الصفحة البديلة لم تظهر"
    assert "منصة المقاولات الذكية في العراق" not in body, \
        "الموقع العام أُعيد بديلاً داخل /app — عزل الأسطح منكسر عند انقطاع الشبكة"


# ══════════════════════════════════════════════════════════════
# الجولة ج — ما يحتاج متصفّحاً حقيقياً
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_65_offline_at_bare_surface_path_no_trailing_slash(live_server, company_cookie_token):
    """
    isSurfaceNav كانت تفحص '/app/' بشرطة لاحقة فقط — تنقّل إلى
    '/app' بلا شرطة كان يسقط إلى الفرع الساكن، وعند الانقطاع قد
    يُقدَّم index.html العام. نفس الثقب الذي أُغلق سابقاً، مواربٌ.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(base_url=live_server)
        context.add_cookies([{
            "name": "bn_sess", "value": company_cookie_token,
            "url": live_server, "httpOnly": True, "sameSite": "Lax",
        }])
        page = context.new_page()

        page.goto(f"{live_server}/index.html")
        page.wait_for_function(
            "navigator.serviceWorker.controller !== null", timeout=15000
        )
        page.goto(f"{live_server}/app/index.html")

        context.set_offline(True)
        resp = page.goto(f"{live_server}/app")
        body = page.content()
        context.set_offline(False)
        browser.close()

    assert resp.status == 503, f"توقّعت 503 (صفحة بديلة)، وصل {resp.status}"
    assert "لا يوجد اتصال" in body
    assert "منصة المقاولات الذكية في العراق" not in body, \
        "/app بلا شرطة لاحقة سقط إلى الموقع العام — الثغرة عادت"


@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_66_login_logo_meets_44px_touch_target(live_server):
    """
    login.html:115 كان رابط الشعار 53.5×20px — المخالفة الوحيدة
    في 29 صفحة. قياس فعلي بمتصفّح حقيقي، لا تقدير من CSS.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.goto(f"{live_server}/login.html")
        box = page.locator(".lg-logo").bounding_box()
        browser.close()

    assert box is not None, "لم يُعثر على .lg-logo"
    assert box["height"] >= 44, f"ارتفاع الشعار {box['height']}px دون 44px"
    assert box["width"] >= 44, f"عرض الشعار {box['width']}px دون 44px"


@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_67_service_worker_update_shows_explicit_banner(live_server):
    """
    stale-while-revalidate يعني أن نسخة جديدة تُنصَّب في الخلفية
    ولا تظهر للمستخدم العائد إلا بعد إعادة تحميل صامتة — لا إشعار.
    sw-update.js يُظهر شريطاً صريحاً حين تُنصَّب نسخة جديدة بجوار
    نسخة تعمل فعلاً. الاختبار يعدّل service-worker.js فعلياً على
    القرص (يُستعاد في finally مهما حدث) لإجبار نسخة "جديدة" حقيقية،
    لا وهمية.
    """
    sw_path = ROOT / "public" / "service-worker.js"
    original = sw_path.read_text(encoding="utf-8")
    m = re.search(r"const CACHE_NAME\s*=\s*'([^']+)'", original)
    assert m, "CACHE_NAME غائب عن service-worker.js"
    current_cache_name = m.group(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(f"{live_server}/index.html")
            page.wait_for_function(
                "navigator.serviceWorker.controller !== null", timeout=15000
            )

            # نسخة "جديدة" فعلية — تغيير حقيقي في محتوى الملف
            sw_path.write_text(
                original.replace(current_cache_name, current_cache_name + "-test-marker"),
                encoding="utf-8",
            )
            page.evaluate(
                "() => navigator.serviceWorker.getRegistration()"
                ".then(r => r && r.update())"
            )
            page.wait_for_selector("#bn-sw-update", timeout=15000)
            assert "نسخة جديدة" in page.locator("#bn-sw-update").inner_text()

            reload_btn = page.locator("#bnSwReload")
            assert reload_btn.bounding_box()["height"] >= 44
        finally:
            sw_path.write_text(original, encoding="utf-8")
            browser.close()


# ══════════════════════════════════════════════════════════════
# عطب دخول المدير — الجلسة تُنشأ ثم تُرفض عند التنقّل إلى /admin
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_80_admin_login_survives_navigation_to_dashboard(live_server):
    """
    عطب حيّ على bonyans.com: POST /login بكلمة صحيحة ينجح (200)،
    لكن التنقّل إلى /admin/ يعيد المستخدم إلى login.html العامة —
    لا يتعلّق بـcompanies.status (identity_from_claims يعيد للمدير
    فوراً قبل أي استعلام، مؤكَّد بفحص مباشر) ولا بالكعكة Secure
    (تصل وتُقرأ بلا مشكلة، مؤكَّد بفحص مباشر تحت ENVIRONMENT=production).

    السبب الحقيقي: admin-login.html كان يكتفي بالكعكة (لصفحات
    /admin وحدها، عبر حارس الأسطح) ولا يكتب bn_token في
    localStorage — لكن admin-core.js يصادق كل نداء API بترويسة
    Authorization من localStorage لا بالكعكة (نفس نمط login.html
    لدوري company/user). فتنجح الصفحة بالتنقّل ثم تفشل كل بياناتها
    فوراً بـ401 صامت، فيُعاد المستخدم إلى ../login.html?role=admin —
    رابط ميّت لأن "admin" ليس بين أدوار login.html العامة (قرار
    متعمَّد: باب الإدارة لا يُعلَن في صفحة عامة)، فيهبط على منتقي
    الأدوار العام ظنّاً منه أنه لم يدخل قط.

    هذا اختبار متصفّح حقيقي (Playwright) بالضرورة: العطب في تفاعل
    JS (admin-core.js وadmin-login.html) لا في منطق الخادم وحده —
    TestClient لا يُنفِّذ JavaScript فلا يراه.
    """
    from conftest import SMOKE_ADMIN_PASSWORD

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(f"{live_server}/admin-login.html")
            page.fill("#adUser", main.ADMIN_USERNAME)
            page.fill("#adPass", SMOKE_ADMIN_PASSWORD)
            page.click("#adSubmit")

            page.wait_for_url(re.compile(r"/admin/index\.html"), timeout=10000)
            # أهمّ لحظة: admin-core.js يستدعي API فور تحميل الصفحة —
            # إن فشلت الترويسة يُعاد التوجيه فوراً. الانتظار على
            # عنصر حقيقي من لوحة الإدارة يثبت أن البيانات وصلت لا أن
            # الصفحة عُرضت لحظة قبل أن تُهجَر.
            page.wait_for_selector("text=لوحة الإدارة", timeout=10000)
            page.wait_for_timeout(1500)  # فرصة كافية لأي تحويل متأخّر بعد فشل API

            assert "/admin/index.html" in page.url, (
                f"أُعيد التوجيه بعيداً عن لوحة الإدارة بعد الدخول — الوجهة: {page.url}"
            )
            assert "منتقي" not in page.content() and "اختر نوع حسابك" not in page.content(), \
                "هبط على منتقي أدوار login.html العام بدل لوحة الإدارة"
        finally:
            browser.close()


# ══════════════════════════════════════════════════════════════
# جولة التثبيت — PWA فقط
# ══════════════════════════════════════════════════════════════

@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_97_install_button_hidden_in_standalone_mode(live_server):
    """
    زرّ التثبيت لا يظهر حين يكون التطبيق مثبَّتاً فعلاً (وضع
    standalone) — يُحاكى بتعديل matchMedia قبل تحميل أي سكربت في
    الصفحة، فيرى nav-public.js نفسه "مثبَّتاً" كما لو فتح المستخدم
    التطبيق من أيقونته لا من متصفّح عادي.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        try:
            page.add_init_script("""
                const realMatchMedia = window.matchMedia;
                window.matchMedia = function (q) {
                    if (q.indexOf('display-mode: standalone') !== -1) {
                        return { matches: true, media: q, addListener(){}, removeListener(){} };
                    }
                    return realMatchMedia.call(window, q);
                };
            """)
            page.goto(f"{live_server}/index.html")
            page.wait_for_selector(".bnv", timeout=10000)
            btn = page.locator("[data-bnv-install]")
            # hidden يجب أن يبقى — لا beforeinstallprompt يصل أصلاً في
            # اختبار آلي، لكن المهمّ هنا أن standalone وحدها كافية لإخفائه
            assert btn.get_attribute("hidden") is not None, \
                "زرّ التثبيت ظاهر رغم وضع standalone المحاكى"
        finally:
            browser.close()


@pytest.mark.skipif(not _HAS_PLAYWRIGHT, reason="Playwright غير مثبَّت")
def test_98_install_page_detects_platform_from_user_agent(live_server):
    """
    install.html تُبرِز تعليمات iOS حين يكون وكيل المستخدم سفاري
    آيفون، وتعليمات أندرويد خلافه — كلا القسمين موجودان في HTML
    الساكن دوماً (يعملان بلا جافاسكربت)؛ الفحص هنا على الشارة
    "هذا جهازك" التي يضيفها JS تحسيناً لا شرطاً.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ١ · آيفون سفاري
        ios_ua = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
        ctx = browser.new_context(user_agent=ios_ua)
        page = ctx.new_page()
        page.goto(f"{live_server}/install.html")
        page.wait_for_timeout(300)
        assert "is-detected" in (page.locator("#platIOS").get_attribute("class") or ""), \
            "لم يُبرِز قسم iOS مع وكيل مستخدم سفاري/آيفون"
        assert "is-detected" not in (page.locator("#platAndroid").get_attribute("class") or "")
        # القسمان مقروءان في HTML الساكن بلا شرط جافاسكربت
        assert "إضافة إلى الشاشة الرئيسية" in page.content()
        assert "تثبيت التطبيق" in page.content()
        ctx.close()

        # ٢ · أندرويد Chrome
        android_ua = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
        ctx2 = browser.new_context(user_agent=android_ua)
        page2 = ctx2.new_page()
        page2.goto(f"{live_server}/install.html")
        page2.wait_for_timeout(300)
        assert "is-detected" in (page2.locator("#platAndroid").get_attribute("class") or ""), \
            "لم يُبرِز قسم أندرويد مع وكيل مستخدم غير iOS"
        assert "is-detected" not in (page2.locator("#platIOS").get_attribute("class") or "")
        ctx2.close()

        browser.close()
