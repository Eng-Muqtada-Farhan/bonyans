"""
اختبار عامل الخدمة — عزل الأسطح عند انقطاع الشبكة
═══════════════════════════════════════════════════════════════
الجولة أ، البند ٥. لا يمكن اختبار fetch handler لعامل خدمة عبر
TestClient (لا متصفّح ولا تنفيذ JS) — هذا الاختبار الوحيد في
المجموعة الذي يشغّل خادماً حقيقياً على منفذ TCP ومتصفّحاً فعلياً
(Playwright/Chromium) ليثبت السلوك كما يراه مستخدم حقيقي:
انقطاع الشبكة داخل /app لا يُعيد الموقع العام كبديل.
"""
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
