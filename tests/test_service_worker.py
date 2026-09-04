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
                urllib.request.urlopen(base + "/health", timeout=0.5)
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
def company_cookie_token():
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
