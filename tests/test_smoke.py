"""
عشرون اختبار دخان — بُنيان

تغطّي: الدخول بالأدوار الثلاثة · رمز مزوّر ومنتهٍ · حرّاس الأسطح
(٩ حالات) · /companies و /projects بالفلاتر والترقيم · دورة حياة
الشركة (إنشاء · اعتماد · رفض) · حدّ المعدّل.
"""
import re
import time
from pathlib import Path

import pytest
from jose import jwt as _jose_jwt
from sqlalchemy import text

import main
from conftest import SMOKE_ADMIN_PASSWORD, SMOKE_PREFIX, _wipe_rate_limits

PAGE = {"sec-fetch-dest": "document"}


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


# ══════════════════════════════════════════════════════════════
# ١–٣ · الدخول بالأدوار الثلاثة
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_01_admin_login(client, admin_token):
    """المدير يدخل ويأخذ رمزاً وكعكة جلسة بعمر ٢٤ ساعة."""
    _wipe_rate_limits()
    r = client.post("/login", json={"username": main.ADMIN_USERNAME,
                                    "password": SMOKE_ADMIN_PASSWORD})
    assert r.status_code == 200
    assert r.json()["token"]
    cookie = r.headers.get("set-cookie", "")
    assert main.SESSION_COOKIE in cookie
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    assert f"Max-Age={int(main.ADMIN_TTL.total_seconds())}" in cookie


@pytest.mark.needs_db
def test_02_company_login(client, company_token):
    """حساب الشركة يدخل ويأخذ رمزاً موحّد الشكل بدور company."""
    payload = _jose_jwt.decode(company_token, main.JWT_SECRET, algorithms=[main.ALGORITHM])
    assert payload["role"] == main.ROLE_COMPANY
    assert payload["uid"]
    # الشركة تُقرأ من profiles لا من الرمز — رمز عمره أسبوع لا يحمل صلاحية
    assert "company_id" not in payload


@pytest.mark.needs_db
def test_03_user_login(client, user_token):
    """صاحب المشروع يدخل ويأخذ الرمز نفسه بدور user."""
    payload = _jose_jwt.decode(user_token, main.JWT_SECRET, algorithms=[main.ALGORITHM])
    assert payload["role"] == main.ROLE_USER
    assert payload["uid"]


@pytest.mark.needs_db
def test_04_wrong_password_is_401(client):
    """كلمة مرور خاطئة ترجع ٤٠١ لا ٢٠٠ ولا ٥٠٠."""
    _wipe_rate_limits()
    r = client.post("/login", json={"username": main.ADMIN_USERNAME,
                                    "password": "definitely-not-the-password"})
    assert r.status_code == 401


# ══════════════════════════════════════════════════════════════
# ٥–٦ · رمز مزوّر · رمز منتهٍ
# ══════════════════════════════════════════════════════════════

def test_05_forged_token_rejected(client):
    """رمز موقَّع بمفتاح آخر يُرفض — التوقيع لا الشكل هو الحَكَم."""
    forged = _jose_jwt.encode(
        {"sub": "user:5", "role": "user", "uid": 5, "exp": int(time.time()) + 3600},
        "not-the-real-secret", algorithm=main.ALGORITHM)
    r = client.get("/my/projects", headers=bearer(forged))
    assert r.status_code == 401


def test_06_expired_token_rejected(client):
    """رمز صحيح التوقيع لكنه منتهٍ يُرفض."""
    expired = _jose_jwt.encode(
        {"sub": "user:5", "role": "user", "uid": 5, "exp": int(time.time()) - 60},
        main.JWT_SECRET, algorithm=main.ALGORITHM)
    r = client.get("/my/projects", headers=bearer(expired))
    assert r.status_code == 401


# ══════════════════════════════════════════════════════════════
# ٧–١٥ · الحرّاس: ثلاثة أدوار × ثلاثة أسطح
# ══════════════════════════════════════════════════════════════

SURFACES = {"/app/index.html": "company",
            "/me/index.html": "user",
            "/admin/index.html": "admin"}


def _visit(client, surface, token):
    """
    زيارة صفحة بجلسة محدَّدة — أو بلا جلسة.

    TestClient يحتفظ بالكعكات بين الطلبات، فبلا مسحٍ صريح تتسرّب
    جلسة اختبارٍ سابق إلى اختبار «بلا جلسة» فيمرّ وهو كاذب.
    """
    client.cookies.clear()
    if token:
        client.cookies.set(main.SESSION_COOKIE, token)
    try:
        return client.get(surface, headers=PAGE, follow_redirects=False)
    finally:
        client.cookies.clear()


@pytest.mark.parametrize("surface,need", list(SURFACES.items()))
@pytest.mark.needs_db
def test_07_09_own_surface_allowed(client, surface, need,
                                   admin_token, company_token, user_token):
    """كل دور يدخل سطحه — ٢٠٠ لا تحويل."""
    tok = {"admin": admin_token, "company": company_token, "user": user_token}[need]
    r = _visit(client, surface, tok)
    assert r.status_code == 200, f"{need} مُنع من سطحه {surface}"


@pytest.mark.parametrize("surface", list(SURFACES))
def test_10_12_no_session_redirects_to_login(client, surface):
    """
    بلا جلسة: تحويل إلى صفحة الدخول لا ٢٠٠ ولا ٥٠٠. /admin وحده
    يحوَّل إلى admin-login.html — باب منفصل بلا رابط إليه من أي
    صفحة عامة، لا إلى login.html العام (جولة الملاحظات ١، بند ٤).
    """
    r = _visit(client, surface, None)
    assert r.status_code == 302
    expected = "/admin-login.html" if surface.startswith("/admin/") else "/login.html"
    assert r.headers["location"].startswith(expected), r.headers["location"]


@pytest.mark.parametrize("surface,need", [("/app/index.html", "company"),
                                          ("/me/index.html", "user"),
                                          ("/admin/index.html", "admin")])
@pytest.mark.needs_db
def test_13_15_wrong_role_goes_to_own_home(client, surface, need,
                                           admin_token, company_token, user_token):
    """دور دخل سطحاً ليس له يُعاد إلى سطحه هو، لا إلى الرئيسية."""
    others = {"admin": admin_token, "company": company_token, "user": user_token}
    del others[need]
    for role, tok in others.items():
        r = _visit(client, surface, tok)
        assert r.status_code == 302, f"{role} لم يُحوَّل عن {surface}"
        assert r.headers["location"] == main._ROLE_HOME[role]


@pytest.mark.needs_db
def test_16_guard_does_not_break_admin_api(client, admin_token):
    """
    الحارس يحرس الصفحات لا الواجهات البرمجية.
    بلا هذا الفصل ترجع مسارات /admin/* تحويلاً ٣٠٢ بدل ٤٠١/٢٠٠.
    """
    r = client.get("/admin/companies", headers=bearer(admin_token))
    assert r.status_code == 200
    assert client.get("/admin/companies").status_code == 401


# ══════════════════════════════════════════════════════════════
# ١٧–١٨ · القوائم: الفلاتر والترقيم
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_17_companies_filters_and_pagination(client):
    """/companies يرقّم ويفلتر، والفلتران يتقاطعان، وtotal يتبع الشرط."""
    r = client.get("/companies", params={"page": 1, "per_page": 3})
    assert r.status_code == 200
    d = r.json()
    assert set(d) >= {"items", "page", "per_page", "total", "pages"}
    assert len(d["items"]) <= 3
    assert d["page"] == 1 and d["per_page"] == 3

    city = client.get("/companies", params={"city": "بغداد", "per_page": 100}).json()
    assert city["total"] <= d["total"]
    assert all(c["city"] == "بغداد" for c in city["items"])

    both = client.get("/companies", params={"city": "بغداد", "spec": "مقاولات عامة",
                                            "per_page": 100}).json()
    assert both["total"] <= city["total"]
    assert all(c["city"] == "بغداد" and c["spec"] == "مقاولات عامة"
               for c in both["items"])

    # الصفحة الثانية لا تكرّر الأولى
    p1 = client.get("/companies", params={"page": 1, "per_page": 2}).json()["items"]
    p2 = client.get("/companies", params={"page": 2, "per_page": 2}).json()["items"]
    assert not ({c["id"] for c in p1} & {c["id"] for c in p2})


@pytest.mark.needs_db
def test_18_projects_filters_and_defaults(client):
    """/projects يعرض المنشورة افتراضاً، ويفلتر بالمدينة والتخصص."""
    d = client.get("/projects", params={"per_page": 100}).json()
    assert all(p["status"] == "published" for p in d["items"])
    assert all(isinstance(p["bids_count"], int) for p in d["items"])

    contracted = client.get("/projects", params={"status": "contracted",
                                                 "per_page": 100}).json()
    assert all(p["status"] == "contracted" for p in contracted["items"])

    if d["items"]:
        p = d["items"][0]
        one = client.get("/projects", params={"city": p["city"],
                                              "category": p["category"],
                                              "per_page": 100}).json()
        assert one["total"] >= 1
        assert all(x["city"] == p["city"] and x["category"] == p["category"]
                   for x in one["items"])


@pytest.mark.needs_db
def test_18b_guest_never_sees_project_contact(client, company_token):
    """
    زائر لا يجد حقول التواصل إطلاقاً — لا فارغةً بل غائبة.

    إخفاؤها في الواجهة وحدها مسرح أمني: نداء واحد يكشفها.
    الشركة التي لم يُقبل عرضها لا تراها كذلك.
    """
    listing = client.get("/projects", params={"per_page": 100}).json()
    assert listing["items"], "تحتاج بيانات البذر: python seed_dev.py"

    # القائمة العامّة لا تحمل حقول تواصل أصلاً
    for p in listing["items"]:
        for f in ("contact_name", "contact_phone", "contact_email"):
            assert f not in p, f"القائمة العامّة تسرّب {f}"

    pid = listing["items"][0]["id"]

    guest = client.get(f"/projects/{pid}").json()
    for f in ("contact_name", "contact_phone", "contact_email"):
        assert f not in guest, f"زائر يرى {f}"
    assert "title" in guest and "budget_min" in guest   # البقية سليمة

    company = client.get(f"/projects/{pid}", headers=bearer(company_token)).json()
    for f in ("contact_name", "contact_phone", "contact_email"):
        assert f not in company, f"شركة لم يُقبل عرضها ترى {f}"


@pytest.mark.needs_db
def test_18c_owner_and_admin_see_project_contact(client, user_token, admin_token):
    """صاحب المشروع والمدير يريان بيانات التواصل."""
    mine = client.get("/my/projects", headers=bearer(user_token)).json()
    assert mine, "تحتاج بيانات البذر: python seed_dev.py"
    pid = mine[0]["id"]

    for label, tok in (("المالك", user_token), ("المدير", admin_token)):
        d = client.get(f"/projects/{pid}", headers=bearer(tok)).json()
        assert "contact_phone" in d, f"{label} لا يرى بيانات التواصل"
        assert "contact_name" in d and "contact_email" in d


# ══════════════════════════════════════════════════════════════
# ١٩ · دورة حياة الشركة: إنشاء · اعتماد · رفض
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_19_company_lifecycle(client, admin_token, user_token):
    """إنشاء يتطلّب إدارة، ويبدأ pending، ثم approved ثم rejected."""
    body = {"name": SMOKE_PREFIX + "شركة دخان", "city": "بغداد",
            "phone": "07000000099", "spec": "مقاولات عامة",
            "desc": "صف اختبار دخان — يُحذف تلقائياً."}

    # بلا رمز ٤٠١، وبرمز صالح لدور آخر ٤٠٣ — التمييز مقصود
    assert client.post("/companies", json=body).status_code == 401
    assert client.post("/companies", json=body,
                       headers=bearer(user_token)).status_code == 403

    r = client.post("/companies", json=body, headers=bearer(admin_token))
    assert r.status_code == 200, r.text
    cid = r.json()["id"]

    with main.SessionLocal() as db:
        row = db.execute(text("SELECT status, verified FROM companies WHERE id=:i"),
                         {"i": cid}).fetchone()
    assert row[0] == "pending"

    # شركة قيد المراجعة لا تظهر في الدليل العام
    listed = client.get("/companies", params={"per_page": 100}).json()["items"]
    assert cid not in {c["id"] for c in listed}

    a = client.put(f"/companies/{cid}/approve", headers=bearer(admin_token))
    assert a.status_code == 200 and a.json()["status"] == "approved"
    assert a.json()["verified"] is True
    listed = client.get("/companies", params={"per_page": 100}).json()["items"]
    assert cid in {c["id"] for c in listed}

    j = client.put(f"/companies/{cid}/reject", headers=bearer(admin_token))
    assert j.status_code == 200 and j.json()["status"] == "rejected"
    assert j.json()["verified"] is False

    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM companies WHERE id=:i"), {"i": cid})
        db.commit()


# ══════════════════════════════════════════════════════════════
# ٢٠ · حدّ المعدّل — خمس محاولات ثم ٤٢٩
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_20_rate_limit_blocks_sixth_login(client):
    """
    خمس محاولات مسموحة ثم ٤٢٩ — ولا يُخلط الحجب بعطل قاعدة البيانات
    الذي يرفع ٥٠٣.
    """
    _wipe_rate_limits()
    codes = [client.post("/login", json={"username": main.ADMIN_USERNAME,
                                         "password": "wrong"}).status_code
             for _ in range(6)]
    assert codes[:5] == [401] * 5, codes
    assert codes[5] == 429, codes
    _wipe_rate_limits()


# ══════════════════════════════════════════════════════════════
# ٢١–٢٦ · توحيد المصادقة (RBAC)
# ══════════════════════════════════════════════════════════════

def test_21_legacy_token_shape_rejected(client):
    """
    رمز بالشكل القديم (type بدل role) يُرفض.

    قبوله يعني إبقاء شكلين للمطالبات إلى الأبد — وهو الازدواج
    الذي أُزيل. الإبطال قرار مُعلَن لا سهو.
    """
    for legacy in (
        {"sub": "company:63", "type": "company", "company_id": 63},
        {"sub": "user:5", "type": "user", "user_id": 5},
    ):
        legacy["exp"] = int(time.time()) + 3600
        tok = _jose_jwt.encode(legacy, main.JWT_SECRET, algorithm=main.ALGORITHM)
        assert client.get("/company/me", headers=bearer(tok)).status_code == 401


@pytest.mark.needs_db
def test_22_profiles_cover_every_user(client, db):
    """كل مستخدم نشط له ملفّ دور — لا حساب بلا دور بعد الترحيل."""
    with main.SessionLocal() as db:
        orphans = db.execute(text("""
            SELECT count(*) FROM users u
            WHERE u.is_active = true
              AND NOT EXISTS (SELECT 1 FROM profiles p WHERE p.user_id = u.id)
        """)).scalar()
    assert orphans == 0


@pytest.mark.needs_db
def test_23_profile_shape_constraint(client, db):
    """قيد الشكل يمنع ملفّاً متناقضاً: شركة بلا company_id، أو عميل بشركة."""
    import sqlalchemy.exc
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users LIMIT 1")).scalar()
        for role, cid in (("company", None), ("client", 1)):
            try:
                db.execute(text(
                    "INSERT INTO profiles (user_id, role, company_id) VALUES (:u,:r,:c)"
                ), {"u": uid, "r": role, "c": cid})
                db.commit()
                assert False, f"قُبل ملفّ متناقض: {role}/{cid}"
            except Exception:
                db.rollback()


@pytest.mark.needs_db
def test_24_require_role_separates_401_from_403(client, user_token):
    """
    بلا رمز ٤٠١، وبرمز صالح لدور آخر ٤٠٣.

    التمييز عملي: الأول يعيد الدخول، والثاني لا يفيده التكرار.
    """
    assert client.get("/company/me").status_code == 401
    assert client.get("/company/me", headers=bearer(user_token)).status_code == 403


@pytest.mark.needs_db
def test_25_company_login_reads_profiles(client, company_token):
    """
    دخول الشركة صار من users + profiles لا من company_users.
    الرمز يحمل uid، والشركة تُشتقّ من الملفّ.
    """
    payload = _jose_jwt.decode(company_token, main.JWT_SECRET, algorithms=[main.ALGORITHM])
    ident = main.identity_from_claims(payload)
    assert ident is not None
    assert ident.role == main.ROLE_COMPANY
    assert ident.cid
    with main.SessionLocal() as db:
        cid = db.execute(text("""
            SELECT company_id FROM profiles WHERE user_id=:u AND role='company'
        """), {"u": ident.uid}).scalar()
    assert cid == ident.cid


@pytest.mark.needs_db
def test_26_deactivated_user_token_stops_working(client, db):
    """
    تعطيل الحساب يُبطل رمزه فوراً — الصلاحية تُقرأ من قاعدة
    البيانات عند كل طلب لا من داخل الرمز.
    """
    r = client.post("/auth/login", json={"email": "client@seed.test",
                                         "password": "SeedTest!2026"})
    assert r.status_code == 200
    tok = r.json()["token"]
    _wipe_rate_limits()
    assert client.get("/my/projects", headers=bearer(tok)).status_code == 200

    with main.SessionLocal() as db:
        db.execute(text("UPDATE users SET is_active=false WHERE email='client@seed.test'"))
        db.commit()
    try:
        assert client.get("/my/projects", headers=bearer(tok)).status_code == 401
    finally:
        with main.SessionLocal() as db:
            db.execute(text("UPDATE users SET is_active=true WHERE email='client@seed.test'"))
            db.commit()


# ══════════════════════════════════════════════════════════════
# ٢٧–٣٤ · سلسلة البريد
#
# البريد مُعطَّل قسراً هنا — conftest.py يحذف RESEND_API_KEY من
# البيئة بعد load_dotenv، بصرف النظر عمّا في .env الفعلي. وهذا
# مقصود: نختبر المنطق والأمان لا مزوّد الطرف الثالث. mailer.send
# يُرجع False فتُختبَر أيضاً استجابة النظام لفشل الإرسال.
# ══════════════════════════════════════════════════════════════

import hashlib as _hl
import secrets as _sec

SEED_EMAIL = "client@seed.test"
SEED_PASS  = "SeedTest!2026"


def _mk_reset(email, minutes=30):
    """رمز استعادة مزروع — الخام لا يُخزَّن فنولّده هنا."""
    raw = _sec.token_urlsafe(32)
    h = _hl.sha256(raw.encode()).hexdigest()
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                         {"e": email}).scalar()
        db.execute(text(
            "INSERT INTO password_resets (user_id, token_hash, expires_at) "
            "VALUES (:u, :h, now() + make_interval(mins => :m))"
        ), {"u": uid, "h": h, "m": minutes})
        db.commit()
    return raw, uid


def _wipe_mail_limits():
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'forgot:%' "
                        "OR key LIKE 'reset:%' OR key LIKE 'verify:%' "
                        "OR key LIKE 'chgmail:%'"))
        db.commit()


@pytest.mark.needs_db
def test_27_forgot_password_reply_never_varies(client):
    """الردّ نفسه سواء وُجد البريد أم لا — اختلافه يكشف المسجَّلين."""
    _wipe_mail_limits()
    real = client.post("/auth/forgot-password", json={"email": SEED_EMAIL})
    fake = client.post("/auth/forgot-password",
                       json={"email": "definitely-not-registered@nowhere.test"})
    assert real.status_code == fake.status_code == 200
    assert real.json() == fake.json()
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_28_forgot_password_rate_limited_same_reply(client, db):
    """الحدّ يُطبَّق، والردّ لا يتغيّر حتى عند الحجب."""
    _wipe_mail_limits()
    replies = [client.post("/auth/forgot-password", json={"email": SEED_EMAIL})
               for _ in range(5)]
    assert all(r.status_code == 200 for r in replies)
    assert len({r.text for r in replies}) == 1, "الردّ تغيّر عند الحجب فكشف الحساب"
    with main.SessionLocal() as db:
        n = db.execute(text(
            "SELECT count(*) FROM rate_limits WHERE key LIKE 'forgot:email:%'")).scalar()
    assert n >= 1
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_29_reset_token_single_use_and_hashed(client, db):
    """الرمز يُستعمل مرة واحدة ولا يُخزَّن نصّاً."""
    _wipe_mail_limits()
    raw, uid = _mk_reset(SEED_EMAIL)
    with main.SessionLocal() as db:
        stored = db.execute(text(
            "SELECT token_hash FROM password_resets WHERE user_id=:u "
            "ORDER BY id DESC LIMIT 1"), {"u": uid}).scalar()
    assert raw not in stored, "الرمز الخام مخزَّن — من قرأ الجدول ينتحل"

    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 200
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 400
    _wipe_rate_limits()
    assert client.post("/auth/login",
                       json={"email": SEED_EMAIL, "password": SEED_PASS}).status_code == 200
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_30_expired_reset_token_rejected(client):
    """رمز منتهٍ يُرفض."""
    _wipe_mail_limits()
    raw, _ = _mk_reset(SEED_EMAIL, minutes=-1)
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 400
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_31_reset_rejects_short_password(client):
    """كلمة قصيرة تُرفض ولا تستهلك الرمز."""
    _wipe_mail_limits()
    raw, _ = _mk_reset(SEED_EMAIL)
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": "short"}).status_code == 400
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 200
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_32_change_password_requires_current(client, user_token):
    """رمز جلسة مسروق وحده لا يكفي لتغيير كلمة المرور."""
    bad = client.post("/auth/change-password", headers=bearer(user_token),
                      json={"current_password": "wrong-one",
                            "new_password": "NewPass!2026"})
    assert bad.status_code == 401
    ok = client.post("/auth/change-password", headers=bearer(user_token),
                     json={"current_password": SEED_PASS, "new_password": SEED_PASS})
    assert ok.status_code == 200, ok.text


@pytest.mark.needs_db
def test_33_change_email_needs_password_and_defers(client, user_token):
    """يتطلّب كلمة المرور، ولا يغيّر البريد قبل التأكيد."""
    _wipe_mail_limits()
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                         {"e": SEED_EMAIL}).scalar()
        before = db.execute(text("SELECT email FROM users WHERE id=:i"),
                            {"i": uid}).scalar()

    assert client.post("/auth/change-email", headers=bearer(user_token),
                       json={"new_email": "new@seed.test",
                             "password": "wrong"}).status_code == 401

    # الإرسال يفشل (لا مفتاح بريد) فيُعاد 502 — ولا يُدّعى نجاح
    r = client.post("/auth/change-email", headers=bearer(user_token),
                    json={"new_email": "new@seed.test", "password": SEED_PASS})
    assert r.status_code in (200, 502), r.text

    with main.SessionLocal() as db:
        after = db.execute(text("SELECT email FROM users WHERE id=:i"),
                           {"i": uid}).scalar()
        db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
        db.commit()
    assert after == before, "تغيّر البريد قبل التأكيد"
    _wipe_mail_limits()


@pytest.mark.needs_db
def test_34_verify_and_change_tokens_do_not_cross(client, db):
    """الغرض شرط قبول لا وسم: رمز تفعيل لا يؤكّد تغيير بريد."""
    raw = _sec.token_urlsafe(32)
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                         {"e": SEED_EMAIL}).scalar()
        db.execute(text(
            "INSERT INTO email_tokens (user_id, purpose, token_hash, expires_at) "
            "VALUES (:u, 'verify', :h, now() + interval '1 hour')"
        ), {"u": uid, "h": _hl.sha256(raw.encode()).hexdigest()})
        db.commit()
    try:
        assert client.post("/auth/confirm-email-change",
                           json={"token": raw}).status_code == 400
        assert client.post("/auth/verify-email",
                           json={"token": raw}).status_code == 200
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
            db.execute(text("UPDATE users SET is_email_verified=true WHERE id=:u"), {"u": uid})
            db.commit()


# ══════════════════════════════════════════════════════════════
# ٣٥–٤٦ · شروط المتجرين: الموافقة · الحذف · الإبلاغ والحجب
#
# الحذف أخطر كود في المشروع: يمحو بيانات نهائياً. كل مسار فيه
# مُختبَر — الرفض بلا كلمة مرور، والرفض بلا العبارة، وما يبقى
# بعد الحذف بالتحديد لا بالعموم.
# ══════════════════════════════════════════════════════════════

CONFIRM = "حذف حسابي"


def _mk_user(email, password="TempPass!2026", name="مستخدم اختبار حذف"):
    """حساب مؤقّت للحذف — لا نلمس حسابات البذر في اختبار مدمّر."""
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE lower(email)=:e"), {"e": email.lower()})
        db.commit()
        uid = db.execute(text("""
            INSERT INTO users (email, display_name, password_hash, provider, is_active,
                               is_email_verified, terms_accepted_at, terms_version)
            VALUES (:e, :n, :p, 'email', true, true, now(), :v)
            RETURNING id
        """), {"e": email.lower(), "n": name,
               "p": main.pwd_context.hash(password), "v": main.LEGAL_VERSION}).scalar()
        db.execute(text("INSERT INTO profiles (user_id, role) VALUES (:u,'client')"),
                   {"u": uid})
        db.commit()
    return uid


def _drop_user(uid):
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
        db.commit()


def _login(client, email, password="TempPass!2026"):
    _wipe_rate_limits()
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ── الموافقة القانونية ──────────────────────────────────────────

@pytest.mark.needs_db
def test_35_register_requires_terms(client, db):
    """لا تسجيل بلا موافقة — الحارس على الخادم لا على المربّع."""
    email = "terms-test@nowhere.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE lower(email)=:e"), {"e": email})
        db.commit()
    bad = client.post("/auth/register", json={
        "email": email, "password": "GoodPass!2026", "display_name": "بلا موافقة"})
    assert bad.status_code == 400
    with main.SessionLocal() as db:
        n = db.execute(text("SELECT count(*) FROM users WHERE lower(email)=:e"),
                       {"e": email}).scalar()
    assert n == 0, "أُنشئ حساب بلا موافقة"


@pytest.mark.needs_db
def test_36_register_records_consent(client, db):
    """الموافقة تُخزَّن بوقتها وبنسخة الوثيقة."""
    email = "terms-ok@nowhere.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE lower(email)=:e"), {"e": email})
        db.commit()
    r = client.post("/auth/register", json={
        "email": email, "password": "GoodPass!2026",
        "display_name": "موافق", "accept_terms": True})
    assert r.status_code == 200, r.text
    try:
        with main.SessionLocal() as db:
            row = db.execute(text(
                "SELECT terms_accepted_at, terms_version FROM users WHERE lower(email)=:e"
            ), {"e": email}).mappings().fetchone()
        assert row["terms_accepted_at"] is not None
        assert row["terms_version"] == main.LEGAL_VERSION
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM users WHERE lower(email)=:e"), {"e": email})
            db.commit()


def test_37_legal_pages_public(client):
    """الصفحتان تعملان بلا تسجيل دخول — شرط المتجرين."""
    for path in ("/privacy.html", "/terms.html"):
        r = client.get(path, headers=PAGE)
        assert r.status_code == 200, path
        assert "بُنيان" in r.text


# ── حذف الحساب ──────────────────────────────────────────────────

@pytest.mark.needs_db
def test_38_delete_requires_password(client, db):
    """كلمة مرور خاطئة لا تحذف شيئاً."""
    uid = _mk_user("del-pw@nowhere.test")
    try:
        tok = _login(client, "del-pw@nowhere.test")
        r = client.request("DELETE", "/account", headers=bearer(tok),
                           json={"password": "wrong", "confirm": CONFIRM})
        assert r.status_code == 401
        with main.SessionLocal() as db:
            active = db.execute(text("SELECT is_active FROM users WHERE id=:u"),
                                {"u": uid}).scalar()
        assert active is True, "عُطِّل الحساب رغم فشل كلمة المرور"
    finally:
        _drop_user(uid)


@pytest.mark.needs_db
def test_39_delete_requires_typed_confirmation(client, db):
    """العبارة المكتوبة شرط — نقرة وحدها لا تمحو حساباً."""
    uid = _mk_user("del-confirm@nowhere.test")
    try:
        tok = _login(client, "del-confirm@nowhere.test")
        for bad in ("", "نعم", "delete", "حذف"):
            r = client.request("DELETE", "/account", headers=bearer(tok),
                               json={"password": "TempPass!2026", "confirm": bad})
            assert r.status_code == 400, bad
        with main.SessionLocal() as db:
            active = db.execute(text("SELECT is_active FROM users WHERE id=:u"),
                                {"u": uid}).scalar()
        assert active is True
    finally:
        _drop_user(uid)


@pytest.mark.needs_db
def test_40_delete_anonymizes_and_locks_out(client, db):
    """
    الحذف يُفقد الحساب هويته ونفاذه فوراً، ويسجّل موعد المحو.
    """
    uid = _mk_user("del-ok@nowhere.test")
    try:
        tok = _login(client, "del-ok@nowhere.test")
        r = client.request("DELETE", "/account", headers=bearer(tok),
                           json={"password": "TempPass!2026", "confirm": CONFIRM})
        assert r.status_code == 200, r.text
        assert "purge_after" in r.json()

        with main.SessionLocal() as db:
            u = db.execute(text(
                "SELECT email, password_hash, display_name, is_active, "
                "deletion_requested_at, anonymized_at FROM users WHERE id=:u"
            ), {"u": uid}).mappings().fetchone()
        assert u["is_active"] is False
        assert u["password_hash"] is None, "بقيت تجزئة كلمة المرور"
        assert "del-ok@nowhere.test" not in (u["email"] or ""), "بقي البريد الأصلي"
        assert u["display_name"] == main.ANON_LABEL
        assert u["deletion_requested_at"] is not None
        assert u["anonymized_at"] is not None

        # الرمز القديم لم يعد ينفذ — الصلاحية من قاعدة البيانات
        assert client.get("/auth/me", headers=bearer(tok)).status_code == 401
        # ولا دخول بالبريد القديم
        _wipe_rate_limits()
        assert client.post("/auth/login", json={
            "email": "del-ok@nowhere.test", "password": "TempPass!2026"
        }).status_code == 401
    finally:
        _drop_user(uid)


@pytest.mark.needs_db
def test_41_delete_keeps_reviews_anonymized(client, db):
    """
    التقييمات تُجهَّل ولا تُحذف — حذفها يشوّه سمعة قُدِّرت بها
    شركة (LEGAL-DRAFT §٦).
    """
    name = "مقيّم اختبار الحذف"
    uid = _mk_user("del-review@nowhere.test", name=name)
    with main.SessionLocal() as db:
        cid = db.execute(text("SELECT id FROM companies LIMIT 1")).scalar()
        rid = db.execute(text("""
            INSERT INTO reviews (company_id, client_name, rating, comment, status)
            VALUES (:c, :n, 4, 'تقييم اختبار الحذف', 'approved') RETURNING id
        """), {"c": cid, "n": name}).scalar()
        db.commit()
    try:
        tok = _login(client, "del-review@nowhere.test")
        assert client.request("DELETE", "/account", headers=bearer(tok),
                              json={"password": "TempPass!2026",
                                    "confirm": CONFIRM}).status_code == 200
        with main.SessionLocal() as db:
            row = db.execute(text(
                "SELECT client_name, comment FROM reviews WHERE id=:r"), {"r": rid}
            ).mappings().fetchone()
        assert row is not None, "حُذف التقييم — والسياسة تقول يُجهَّل"
        assert row["client_name"] == main.ANON_LABEL, "لم يُجهَّل اسم المقيّم"
        assert row["comment"] == "تقييم اختبار الحذف", "ضاع نصّ التقييم"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM reviews WHERE id=:r"), {"r": rid})
            db.commit()
        _drop_user(uid)


@pytest.mark.needs_db
def test_42_delete_anonymizes_projects_not_bids(client, db):
    """
    مشروع صاحب الحساب يُجهَّل ولا يُحذف: عروض الشركات عليه جزء
    من سجلّها هي، ومحوه يمحو تاريخاً ليس ملكاً للمنسحب وحده.
    """
    uid = _mk_user("del-proj@nowhere.test")
    with main.SessionLocal() as db:
        pid = db.execute(text("""
            INSERT INTO projects (title, category, city, country, contact_name,
                                  contact_phone, contact_email, status, owner_user_id)
            VALUES ('مشروع اختبار الحذف','مقاولات عامة','بغداد','IQ',
                    'صاحب','07000000123','x@y.test','published',:u)
            RETURNING id
        """), {"u": uid}).scalar()
        cid = db.execute(text("SELECT id FROM companies LIMIT 1")).scalar()
        bid = db.execute(text("""
            INSERT INTO project_bids (project_id, company_id, price, status)
            VALUES (:p, :c, 5000, 'submitted') RETURNING id
        """), {"p": pid, "c": cid}).scalar()
        db.commit()
    try:
        tok = _login(client, "del-proj@nowhere.test")
        assert client.request("DELETE", "/account", headers=bearer(tok),
                              json={"password": "TempPass!2026",
                                    "confirm": CONFIRM}).status_code == 200
        with main.SessionLocal() as db:
            p = db.execute(text(
                "SELECT contact_name, contact_phone, contact_email, owner_user_id, status "
                "FROM projects WHERE id=:p"), {"p": pid}).mappings().fetchone()
            b = db.execute(text("SELECT id FROM project_bids WHERE id=:b"),
                           {"b": bid}).first()
        assert p is not None, "حُذف المشروع"
        assert p["contact_phone"] == "" and p["contact_email"] == ""
        assert p["contact_name"] == main.ANON_LABEL
        assert p["owner_user_id"] is None
        assert p["status"] == "closed", "بقي مفتوحاً للعروض بلا صاحب"
        assert b is not None, "ضاع عرض الشركة مع حذف حساب صاحب المشروع"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM project_bids WHERE id=:b"), {"b": bid})
            db.execute(text("DELETE FROM projects WHERE id=:p"), {"p": pid})
            db.commit()
        _drop_user(uid)


@pytest.mark.needs_db
def test_43_purge_only_after_grace(client, db):
    """المحو النهائي لا يقع قبل انقضاء الثلاثين يوماً."""
    uid = _mk_user("del-grace@nowhere.test")
    try:
        with main.SessionLocal() as db:
            db.execute(text(
                "UPDATE users SET deletion_requested_at = now() WHERE id=:u"), {"u": uid})
            db.commit()
        main.purge_deleted_accounts()
        with main.SessionLocal() as db:
            still = db.execute(text("SELECT 1 FROM users WHERE id=:u"), {"u": uid}).first()
        assert still is not None, "مُحي الحساب قبل انقضاء المهلة"

        with main.SessionLocal() as db:
            db.execute(text("UPDATE users SET deletion_requested_at = now() - "
                            "interval '31 days' WHERE id=:u"), {"u": uid})
            db.commit()
        main.purge_deleted_accounts()
        with main.SessionLocal() as db:
            gone = db.execute(text("SELECT 1 FROM users WHERE id=:u"), {"u": uid}).first()
        assert gone is None, "لم يُمحَ بعد انقضاء المهلة"
    finally:
        _drop_user(uid)


# ── الإبلاغ والحجب ──────────────────────────────────────────────

@pytest.mark.needs_db
def test_44_report_requires_auth_and_valid_input(client, user_token):
    """بلاغ بلا حساب مرفوض، وبنوع أو سبب مجهول مرفوض."""
    assert client.post("/report", json={
        "target_type": "company", "target_id": 1, "reason": "spam"}).status_code == 401
    assert client.post("/report", headers=bearer(user_token), json={
        "target_type": "planet", "target_id": 1, "reason": "spam"}).status_code == 400
    assert client.post("/report", headers=bearer(user_token), json={
        "target_type": "company", "target_id": 1, "reason": "because"}).status_code == 400


@pytest.mark.needs_db
def test_45_report_is_recorded_once_and_visible_to_admin(client, user_token, admin_token):
    """البلاغ يُسجَّل، ويتكرّر بلا ضجيج، ويظهر للإدارة بعمره."""
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM reports WHERE details = 'بلاغ اختبار'"))
        db.execute(text("DELETE FROM rate_limits WHERE key LIKE 'report:%'"))
        db.commit()
        cid = db.execute(text("SELECT id FROM companies LIMIT 1")).scalar()

    body = {"target_type": "company", "target_id": cid,
            "reason": "fake_info", "details": "بلاغ اختبار"}
    first = client.post("/report", headers=bearer(user_token), json=body)
    assert first.status_code == 200, first.text
    again = client.post("/report", headers=bearer(user_token), json=body)
    assert again.status_code == 200, "التكرار كشف نفسه بردّ مختلف"

    with main.SessionLocal() as db:
        n = db.execute(text(
            "SELECT count(*) FROM reports WHERE target_type='company' AND target_id=:c"
        ), {"c": cid}).scalar()
    assert n == 1, "سُجّل البلاغ مرّتين"

    listed = client.get("/admin/reports", headers=bearer(admin_token))
    assert listed.status_code == 200
    row = [r for r in listed.json() if r["target_id"] == cid]
    assert row, "لم يظهر البلاغ للإدارة"
    assert "age_hours" in row[0], "عمر البلاغ غائب — التزام ٢٤ ساعة غير مرئي"
    assert row[0]["reason_label"] == "بيانات كاذبة"

    rid = row[0]["id"]
    done = client.put(f"/admin/reports/{rid}", headers=bearer(admin_token),
                      json={"status": "actioned", "note": "اختبار"})
    assert done.status_code == 200
    with main.SessionLocal() as db:
        st = db.execute(text("SELECT status FROM reports WHERE id=:i"), {"i": rid}).scalar()
        db.execute(text("DELETE FROM reports WHERE id=:i"), {"i": rid})
        db.commit()
    assert st == "actioned"


@pytest.mark.needs_db
def test_46_block_prevents_messaging_both_ways(client, user_token):
    """الحجب يمنع المراسلة، ورفعه يعيدها."""
    with main.SessionLocal() as db:
        me = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'")).scalar()
        cid = db.execute(text("""
            SELECT company_id FROM profiles WHERE role='company' ORDER BY created_at LIMIT 1
        """)).scalar()
        owner = db.execute(text("""
            SELECT user_id FROM profiles WHERE company_id=:c AND role='company'
            ORDER BY created_at LIMIT 1
        """), {"c": cid}).scalar()
        db.execute(text("DELETE FROM blocks WHERE blocker_id=:a OR blocked_id=:a"), {"a": me})
        db.commit()

    assert client.post(f"/block/{me}", headers=bearer(user_token)).status_code == 400  # نفسه

    blocked = client.post(f"/block/{owner}", headers=bearer(user_token))
    assert blocked.status_code == 200, blocked.text

    listed = client.get("/blocks", headers=bearer(user_token))
    assert listed.status_code == 200
    assert any(b["user_id"] == owner for b in listed.json())

    denied = client.post("/conversations", headers=bearer(user_token),
                         json={"company_id": cid, "message": "مرحباً"})
    assert denied.status_code == 403, "المراسلة نجحت رغم الحجب"

    assert client.request("DELETE", f"/block/{owner}",
                          headers=bearer(user_token)).status_code == 200
    with main.SessionLocal() as db:
        left = db.execute(text("SELECT count(*) FROM blocks WHERE blocker_id=:a"),
                          {"a": me}).scalar()
    assert left == 0


# ══════════════════════════════════════════════════════════════
# الجولة أ — ثغرات حيّة وعزل الأسطح
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_47_website_map_link_reject_javascript_scheme(client, admin_token, company_token):
    """
    website وmap_link يُرفضان إن لم يبدآ بـhttp:// أو https:// —
    قائمة سماح لا قائمة منع. هذا هو مسار XSS المخزّنة عبر
    javascript: الذي كان يصل إلى كل زائر على صفحة الشركة العامة.
    """
    # POST /companies (إنشاء إداري)
    body = {"name": SMOKE_PREFIX + "شركة رابط خبيث", "city": "بغداد",
            "phone": "07000000098", "spec": "مقاولات عامة", "desc": "اختبار",
            "website": "javascript:alert(document.cookie)"}
    r = client.post("/companies", json=body, headers=bearer(admin_token))
    assert r.status_code == 422, "قبل رابط javascript: في الإنشاء الإداري"

    body2 = {**body, "website": "", "map_link": "javascript:alert(1)"}
    r2 = client.post("/companies", json=body2, headers=bearer(admin_token))
    assert r2.status_code == 422, "قبل رابط javascript: في map_link عند الإنشاء"

    # نداء سليم يُقبل ويُنظَّف فوراً — يثبت أن القائمة سماح لا حجب عام
    ok = client.post("/companies", json={**body, "website": "https://example.com"},
                     headers=bearer(admin_token))
    assert ok.status_code == 200, "رابط https:// سليم رُفض خطأً"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM companies WHERE id=:i"), {"i": ok.json()["id"]})
        db.commit()

    # PUT /company/me (تعديل الشركة نفسها بعد الاعتماد)
    before = client.get("/company/me", headers=bearer(company_token)).json()
    bad = client.put("/company/me", headers=bearer(company_token),
                     json={"website": "javascript:alert(document.cookie)"})
    assert bad.status_code == 422, "قبل رابط javascript: في PUT /company/me"

    bad2 = client.put("/company/me", headers=bearer(company_token),
                      json={"map_link": "javaScript:alert(1)"})
    assert bad2.status_code == 422, "قبل رابط javascript: بحروف كبيرة في map_link"

    good = client.put("/company/me", headers=bearer(company_token),
                      json={"website": "https://example.com"})
    assert good.status_code == 200, "رابط https:// سليم رُفض خطأً في /company/me"

    # استعادة القيمة الأصلية — لا نترك أثراً في حساب البذرة
    client.put("/company/me", headers=bearer(company_token),
              json={"website": before.get("website") or ""})


@pytest.mark.needs_db
def test_48_free_text_fields_have_max_length(client, admin_token):
    """
    حقل نصّي حرّ بلا حدّ أقصى يعني صفّاً بحجم ميغابايت — كل نموذج
    Pydantic في main.py يحمل الآن max_length معقولاً.
    """
    body = {"name": SMOKE_PREFIX + "شركة", "city": "بغداد",
            "phone": "07000000097", "spec": "مقاولات عامة",
            "desc": "س" * 5001}  # الحدّ ٥٠٠٠
    r = client.post("/companies", json=body, headers=bearer(admin_token))
    assert r.status_code == 422, "وصف أطول من الحدّ الأقصى قُبل"

    body2 = {**body, "desc": "اختبار", "phone": "0" * 31}  # الحدّ ٣٠
    r2 = client.post("/companies", json=body2, headers=bearer(admin_token))
    assert r2.status_code == 422, "هاتف أطول من الحدّ الأقصى قُبل"


@pytest.mark.needs_db
def test_49_page_upper_bound_prevents_offset_overflow(client):
    """
    page بلا حدّ أعلى كان يُنتج OFFSET يتجاوز bigint فيُسقط الطلب
    بخطأ 500 غير معالَج (main.py: /companies و /projects).
    """
    r = client.get("/companies", params={"page": 99999999999999999999, "per_page": 20})
    assert r.status_code == 200, f"page ضخم أسقط /companies: {r.status_code}"
    assert r.json()["items"] == []

    r2 = client.get("/projects", params={"page": 99999999999999999999, "per_page": 20})
    assert r2.status_code == 200, f"page ضخم أسقط /projects: {r2.status_code}"
    assert r2.json()["items"] == []


@pytest.mark.needs_db
def test_50_wa_stats_requires_matching_company_or_admin(client, admin_token, company_token):
    """
    wa-stats كانت تتحقّق فقط من وجود ترويسة Authorization — أي طلب
    بترويسة عشوائية يقرأ إحصاءات أي شركة. صار يستعمل الحارس نفسه
    المستعمل في /company/{id}/views المجاور: resolve_identity +
    مقارنة company_id.
    """
    me = client.get("/company/me", headers=bearer(company_token)).json()
    cid = me["id"]

    forged = client.get(f"/company/{cid}/wa-stats",
                        headers={"Authorization": "Bearer garbage-not-a-jwt"})
    assert forged.status_code == 401, "ترويسة عشوائية أعادت غير 401"

    no_auth = client.get(f"/company/{cid}/wa-stats")
    assert no_auth.status_code == 401

    own = client.get(f"/company/{cid}/wa-stats", headers=bearer(company_token))
    assert own.status_code == 200, "الشركة رُفضت عن إحصاءاتها هي"

    with main.SessionLocal() as db:
        other_cid = db.execute(
            text("SELECT id FROM companies WHERE id != :c ORDER BY id LIMIT 1"),
            {"c": cid}
        ).scalar()
    assert other_cid, "تحتاج بيانات البذر: شركة ثانية على الأقل"
    other = client.get(f"/company/{other_cid}/wa-stats", headers=bearer(company_token))
    assert other.status_code == 403, "شركة رأت إحصاءات شركة غيرها"

    admin_view = client.get(f"/company/{cid}/wa-stats", headers=bearer(admin_token))
    assert admin_view.status_code == 200, "المدير رُفض عن إحصاءات شركة"


@pytest.mark.needs_db
def test_51_500_responses_do_not_leak_exception_text(client, company_token, monkeypatch):
    """
    main.py:434 و1181 و2846 كانت تُعيد str(e) الخام في جسم استجابة
    500 — قد يسرّب تفاصيل استعلام أو رسالة اتصال بقاعدة البيانات.
    صار يُسجَّل في السجلّ، وتُعاد رسالة عامة للعميل.
    """
    secret = "SECRET_DB_CONNECTION_STRING_MUST_NOT_LEAK_TO_CLIENT"

    def _boom(*a, **k):
        raise RuntimeError(secret)

    monkeypatch.setattr(main.imagekit.files, "upload", _boom)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    r = client.post(
        "/upload",
        headers=bearer(company_token),
        files={"file": ("test.png", png_bytes, "image/png")},
    )
    assert r.status_code == 500
    assert secret not in r.text, "نصّ الاستثناء الخام تسرّب إلى العميل"
    assert "فشل رفع الصورة" in r.text

    # الموضعان الآخران (main.py: company_upload وsubmit_bid) بنفس
    # النمط — فحص ساكن يمنع ارتداد أيّ منهما دون تشغيل مسار حيّ لكل واحد.
    import inspect
    src = inspect.getsource(main)
    assert 'detail=f"Upload failed' not in src
    assert 'detail=f"Image upload failed' not in src
    assert 'detail=str(e)' not in src


# ══════════════════════════════════════════════════════════════
# الجولة ب — الوعود الأربعة المكتوبة التي لا ينفّذها الكود
# ══════════════════════════════════════════════════════════════

def test_52_health_endpoint_does_not_leak_exception_text(client, monkeypatch):
    """main.py:3916 كانت تُعيد str(e) من فشل اتصال القاعدة."""
    secret = "SECRET_DB_HOST_MUST_NOT_LEAK"
    monkeypatch.setattr(main, "SessionLocal",
                        lambda: (_ for _ in ()).throw(RuntimeError(secret)))
    r = client.get("/health")
    assert r.status_code == 503
    assert secret not in r.text


@pytest.mark.needs_db
def test_53_report_rejects_nonexistent_target(client, user_token):
    """POST /report كان يقبل ويخزّن target_id وهمياً بلا تحقّق."""
    fake_id = 999999999
    r = client.post("/report", headers=bearer(user_token),
                    json={"target_type": "company", "target_id": fake_id, "reason": "other"})
    assert r.status_code == 404, "بلاغ عن هدف غير موجود قُبل"
    with main.SessionLocal() as db:
        n = db.execute(text(
            "SELECT count(*) FROM reports WHERE target_type='company' AND target_id=:i"
        ), {"i": fake_id}).scalar()
    assert n == 0, "خُزِّن بلاغ عن هدف وهمي رغم الرفض"


@pytest.mark.needs_db
def test_54_purge_old_audit_logs_respects_retention(client, admin_token):
    """صفوف security_audit_log الأقدم من ١٢ شهراً تُحذف، والأحدث تبقى."""
    with main.SessionLocal() as db:
        old_id = db.execute(text("""
            INSERT INTO security_audit_log(actor_type, actor_id, action, ip_hash, meta, created_at)
            VALUES ('user', 'SMOKE_old', 'smoke_probe', 'x', '{}', now() - interval '400 days')
            RETURNING id
        """)).scalar()
        new_id = db.execute(text("""
            INSERT INTO security_audit_log(actor_type, actor_id, action, ip_hash, meta, created_at)
            VALUES ('user', 'SMOKE_new', 'smoke_probe', 'x', '{}', now())
            RETURNING id
        """)).scalar()
        db.commit()
    try:
        removed = main.purge_old_audit_logs()
        assert removed >= 1
        with main.SessionLocal() as db:
            still_old = db.execute(text("SELECT 1 FROM security_audit_log WHERE id=:i"),
                                   {"i": old_id}).first()
            still_new = db.execute(text("SELECT 1 FROM security_audit_log WHERE id=:i"),
                                   {"i": new_id}).first()
        assert still_old is None, "صفّ أقدم من ١٢ شهراً لم يُحذف"
        assert still_new is not None, "صفّ حديث حُذف خطأً"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM security_audit_log WHERE id IN (:a, :b)"),
                      {"a": old_id, "b": new_id})
            db.commit()


@pytest.mark.needs_db
def test_55_run_purge_job_logs_and_locks(client, db):
    """
    run_purge_job يسجّل في job_runs، ولا يُنفَّذ مرتين إن كان قفله
    الاستشاري مأخوذاً من عملية أخرى — يُثبت بإمساك القفل يدوياً في
    اتصال منفصل ثم استدعاء run_purge_job وانتظار status='skipped_locked'.
    """
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM job_runs"))
        db.commit()

    holder = main.engine.connect()
    try:
        got = holder.execute(text("SELECT pg_try_advisory_lock(:k)"),
                             {"k": main._PURGE_LOCK_KEY}).scalar()
        assert got, "تعذّر أخذ القفل يدوياً للاختبار"

        main.run_purge_job()

        with main.SessionLocal() as db:
            rows = db.execute(text(
                "SELECT job_name, status FROM job_runs ORDER BY id"
            )).fetchall()
        assert rows, "لا سجلّ في job_runs بعد التشغيل"
        assert all(r[1] == "skipped_locked" for r in rows), \
            f"تنفيذ وقع رغم القفل المأخوذ: {rows}"
    finally:
        holder.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": main._PURGE_LOCK_KEY})
        holder.commit()
        holder.close()

    # بلا منازع على القفل، التشغيل يمرّ فعلياً ويُسجَّل 'ok' لكلا المهمّتين
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM job_runs"))
        db.commit()
    main.run_purge_job()
    with main.SessionLocal() as db:
        rows = db.execute(text("SELECT job_name, status FROM job_runs ORDER BY id")).fetchall()
    names_ok = {r[0] for r in rows if r[1] == "ok"}
    assert names_ok == {"purge_deleted_accounts", "purge_old_audit_logs"}, rows


@pytest.mark.needs_db
def test_56_owner_and_client_fk_are_set_null(client, db):
    """
    توثيق الانحراف (ترحيل c9d0e1f2a3b4): كلا القيدين ON DELETE
    SET NULL الآن، لا CASCADE ولا NO ACTION.
    """
    with main.SessionLocal() as db:
        rows = db.execute(text("""
            SELECT conname, confdeltype FROM pg_constraint
            WHERE conname IN ('companies_owner_user_id_fkey',
                              'conversations_client_user_id_fkey')
        """)).fetchall()
    by_name = {r[0]: r[1] for r in rows}
    assert by_name.get("companies_owner_user_id_fkey") == "n", by_name
    assert by_name.get("conversations_client_user_id_fkey") == "n", by_name


@pytest.mark.needs_db
def test_57_purge_after_grace_preserves_other_party_messages(client, admin_token):
    """
    أهمّ اختبار في الجولة. صاحب مشروع يُحذف حسابه نهائياً بعد
    مهلة ٣٠ يوماً — رسائل الشركة معه في المحادثة يجب أن تبقى
    موجودة ومقروءة، لا أن تُمحى بالتتالي (كان DELETE FROM users
    يُشعل CASCADE على conversations ثم chat_messages).
    """
    uid = _mk_user("purge-msg-test@nowhere.test")
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles WHERE role='company' ORDER BY created_at LIMIT 1"
        )).scalar()
    assert cid, "تحتاج بيانات البذر: python seed_dev.py"

    with main.SessionLocal() as db:
        conv_id = db.execute(text("""
            INSERT INTO conversations(client_user_id, company_id) VALUES (:u, :c)
            RETURNING id
        """), {"u": uid, "c": cid}).scalar()
        db.execute(text("""
            INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
            VALUES (:conv, 'client', :u, 'SMOKE: رسالة العميل قبل الحذف')
        """), {"conv": conv_id, "u": uid})
        db.execute(text("""
            INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
            VALUES (:conv, 'company', :c, 'SMOKE: ردّ الشركة — يجب أن يبقى')
        """), {"conv": conv_id, "c": cid})
        db.commit()

    try:
        with main.SessionLocal() as db:
            db.execute(text(
                "UPDATE users SET deletion_requested_at = now() - interval '31 days' WHERE id=:u"
            ), {"u": uid})
            db.commit()

        main.purge_deleted_accounts()

        with main.SessionLocal() as db:
            user_gone = db.execute(text("SELECT 1 FROM users WHERE id=:u"), {"u": uid}).first()
            conv = db.execute(text(
                "SELECT client_user_id FROM conversations WHERE id=:c"
            ), {"c": conv_id}).mappings().first()
            msg_count = db.execute(text(
                "SELECT count(*) FROM chat_messages WHERE conversation_id=:c"
            ), {"c": conv_id}).scalar()

        assert user_gone is None, "المستخدم لم يُحذف — purge لم ينجح"
        assert conv is not None, "المحادثة مُحيت — رسائل الطرف الباقي ضاعت معها"
        assert conv["client_user_id"] is None, \
            "client_user_id لم يُفصَل — القيد ما زال CASCADE لا SET NULL"
        assert msg_count == 2, f"توقّعت بقاء رسالتين، وُجد {msg_count}"

        # الشركة تراها منسوبة إلى «حساب محذوف» لا معطوبة
        with main.SessionLocal() as db:
            listed = db.execute(text("""
                SELECT COALESCE(u.display_name, :anon) AS client_name
                FROM conversations c LEFT JOIN users u ON u.id=c.client_user_id
                WHERE c.id=:c
            """), {"c": conv_id, "anon": main.ANON_LABEL}).scalar()
        assert listed == main.ANON_LABEL
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM chat_messages WHERE conversation_id=:c"), {"c": conv_id})
            db.execute(text("DELETE FROM conversations WHERE id=:c"), {"c": conv_id})
            # purge_deleted_accounts يحذف المستخدم عادة؛ هذا احتياط
            # فقط إن فشل الاختبار قبل بلوغه فبقي الصفّ معلَّقاً.
            db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
            db.commit()


# ══════════════════════════════════════════════════════════════
# الجولة ج — ما يمنع القبول في المتجرين
# ══════════════════════════════════════════════════════════════

def _wcag_ratio(hex1, hex2):
    def lin(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    def lum(h):
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

    l1, l2 = lum(hex1), lum(hex2)
    l1, l2 = max(l1, l2), min(l1, l2)
    return (l1 + 0.05) / (l2 + 0.05)


def _read_tokens():
    return (Path(__file__).resolve().parent.parent / "public" / "tokens.css").read_text(encoding="utf-8")


def test_58_ink3_contrast_passes_wcag_aa_in_all_modes(client):
    """
    --bn-ink-3 يُستعمل فوق --bn-bg و--bn-surface في الوضعين — أي
    نسبة دون 4.5:1 (نص عادي) مخالفة WCAG AA. تحديداً على رابطَي
    الخصوصية والشروط الإلزاميين للمتجرين (tokens.css:341).
    حساب رقمي لا لقطة شاشة — يفشل لو رجع اللون للقيمة الأصلية.
    """
    css = _read_tokens()

    def token(name, block=None):
        pat = css if block is None else block
        m = re.search(name + r"\s*:\s*(#[0-9A-Fa-f]{6})", pat)
        assert m, f"{name} غير موجود"
        return m.group(1)

    light_bg, light_surf, light_ink3 = (
        token(r"--bn-bg"), token(r"--bn-surface"), token(r"--bn-ink-3")
    )
    m = re.search(r"prefers-color-scheme:\s*dark\s*\)\s*\{.*?\{(.*?)\}\s*\}", css, re.S)
    assert m, "كتلة الوضع الليلي (النظام) غير موجودة"
    dark_sys = m.group(1)
    dark_bg, dark_surf, dark_ink3 = (
        token(r"--bn-bg", dark_sys), token(r"--bn-surface", dark_sys), token(r"--bn-ink-3", dark_sys)
    )
    m2 = re.search(r'data-theme="dark"\s*\]\s*\{(.*?)\}', css, re.S)
    assert m2, "كتلة الوضع الليلي (الصريح) غير موجودة"
    explicit_dark = m2.group(1)
    edark_ink3 = token(r"--bn-ink-3", explicit_dark)

    cases = [
        ("فاتح / bg", light_bg, light_ink3),
        ("فاتح / surface", light_surf, light_ink3),
        ("داكن نظام / bg", dark_bg, dark_ink3),
        ("داكن نظام / surface", dark_surf, dark_ink3),
        ("داكن صريح / bg", dark_bg, edark_ink3),
        ("داكن صريح / surface", dark_surf, edark_ink3),
    ]
    failures = []
    for label, bg, fg in cases:
        r = _wcag_ratio(bg, fg)
        if r < 4.5:
            failures.append(f"{label}: {bg} مقابل {fg} = {r:.2f}:1 (دون 4.5:1)")
    assert not failures, "\n".join(failures)


def test_59_service_worker_matches_surface_without_trailing_slash(client):
    """
    isSurfaceNav كانت تفحص '/app/' بشرطة لاحقة فقط — تنقّل إلى
    '/app' بلا شرطة يسقط إلى الفرع الساكن. فحص ساكن على مصدر
    الملف يثبت أن الفحص الجديد يقبل كلا الشكلين لكل الأسطح الثلاثة.
    """
    src = (Path(__file__).resolve().parent.parent / "public" / "service-worker.js").read_text(encoding="utf-8")
    m = re.search(r"SURFACE_RE\s*=\s*(/.*?/)[;\s]", src)
    assert m, "SURFACE_RE غير موجود"
    pattern = re.compile(m.group(1)[1:-1])
    for surface in ("app", "admin", "me"):
        assert pattern.match(f"/{surface}"), f"/{surface} بلا شرطة لا يُطابَق"
        assert pattern.match(f"/{surface}/index.html"), f"/{surface}/ بشرطة لا يُطابَق"
    assert not pattern.match("/application.html"), "طابق مساراً عاماً بالخطأ (بادئة مشتركة)"


def test_60_sitemap_and_robots_use_current_domain(client):
    """sitemap.xml وrobots.txt كانا يحملان النطاق القديم bunyan.iq."""
    root = Path(__file__).resolve().parent.parent / "public"
    sitemap = (root / "sitemap.xml").read_text(encoding="utf-8")
    robots = (root / "robots.txt").read_text(encoding="utf-8")
    assert "bunyan.iq" not in sitemap
    assert "bunyan.iq" not in robots
    assert "bonyans.com" in sitemap
    assert "bonyans.com" in robots


@pytest.mark.needs_db
def test_61_rejected_company_session_is_invalidated_immediately(client, admin_token):
    """
    زرّ «رفض» الإداري كان لا يقطع وصول شركة جلستها قائمة بالفعل —
    identity_from_claims كانت تفحص users.is_active وحده لا
    companies.status. الآن ترفض الرمز فوراً بعد الرفض، لا عند
    انتهائه الطبيعي (حتى ٧ أيام).
    """
    body = {"name": SMOKE_PREFIX + "شركة رفض جلسة", "city": "بغداد",
            "phone": "07000000096", "spec": "مقاولات عامة", "desc": "اختبار"}
    r = client.post("/companies", json=body, headers=bearer(admin_token))
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    with main.SessionLocal() as db:
        uid = db.execute(text(
            "SELECT id FROM users WHERE email=:e"
        ), {"e": f"smoke-{cid}@nowhere.test"}).scalar()
        if not uid:
            uid = db.execute(text("""
                INSERT INTO users (email, display_name, password_hash, provider,
                                   is_active, is_email_verified, terms_accepted_at, terms_version)
                VALUES (:e, 'مالك اختبار', :p, 'email', true, true, now(), :v)
                RETURNING id
            """), {"e": f"smoke-{cid}@nowhere.test", "p": main.pwd_context.hash("x"),
                   "v": main.LEGAL_VERSION}).scalar()
        db.execute(text("""
            INSERT INTO profiles (user_id, role, company_id, company_role)
            VALUES (:u, 'company', :c, 'owner')
        """), {"u": uid, "c": cid})
        db.commit()

    try:
        token = main.create_token(main.ROLE_COMPANY, uid)
        before = client.get("/company/me", headers=bearer(token))
        assert before.status_code == 200, "الرمز يجب أن يعمل قبل الرفض"

        rej = client.put(f"/companies/{cid}/reject", headers=bearer(admin_token))
        assert rej.status_code == 200

        after = client.get("/company/me", headers=bearer(token))
        assert after.status_code == 401, \
            "نفس الرمز ما زال يعمل بعد الرفض — الجلسة لم تُبطَل"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM profiles WHERE user_id=:u"), {"u": uid})
            db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
            db.execute(text("DELETE FROM companies WHERE id=:c"), {"c": cid})
            db.commit()


@pytest.mark.needs_db
def test_62_messages_are_paginated_newest_first(client, user_token):
    """
    /conversations/{id}/messages كانت تعيد تاريخ المحادثة كاملاً
    بلا حدّ. صار ترقيماً حقيقياً: {items, has_more, oldest_id}،
    والصفحة الأولى أحدث limit رسالة لا أقدمها.
    """
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles WHERE role='company' ORDER BY created_at LIMIT 1"
        )).scalar()
        uid = db.execute(text(
            "SELECT id FROM users WHERE lower(email)='client@seed.test'"
        )).scalar()
    assert cid and uid, "تحتاج بيانات البذر"

    with main.SessionLocal() as db:
        conv_id = db.execute(text(
            "INSERT INTO conversations(client_user_id, company_id) VALUES (:u,:c) RETURNING id"
        ), {"u": uid, "c": cid}).scalar()
        ids = []
        for i in range(7):
            mid = db.execute(text("""
                INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
                VALUES (:conv,'client',:u,:m) RETURNING id
            """), {"conv": conv_id, "u": uid, "m": f"SMOKE msg {i}"}).scalar()
            ids.append(mid)
        db.commit()

    try:
        p1 = client.get(f"/conversations/{conv_id}/messages", params={"limit": 3},
                        headers=bearer(user_token))
        assert p1.status_code == 200
        d1 = p1.json()
        assert d1["has_more"] is True
        assert [m["id"] for m in d1["items"]] == ids[-3:], "الصفحة الأولى ليست أحدث ٣"

        p2 = client.get(f"/conversations/{conv_id}/messages",
                        params={"limit": 3, "before_id": d1["oldest_id"]},
                        headers=bearer(user_token))
        d2 = p2.json()
        assert [m["id"] for m in d2["items"]] == ids[1:4], "صفحة أقدم لا تطابق"
        assert d2["has_more"] is True

        p3 = client.get(f"/conversations/{conv_id}/messages",
                        params={"limit": 3, "before_id": d2["oldest_id"]},
                        headers=bearer(user_token))
        d3 = p3.json()
        assert [m["id"] for m in d3["items"]] == ids[:1]
        assert d3["has_more"] is False
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM chat_messages WHERE conversation_id=:c"), {"c": conv_id})
            db.execute(text("DELETE FROM conversations WHERE id=:c"), {"c": conv_id})
            db.commit()


@pytest.mark.needs_db
def test_63_report_target_existence_still_enforced(client, user_token):
    """
    فحص مساعد بعد إعادة صياغة submit_report في هذه الجولة — يبقى
    404 لهدف غير موجود (مصدره test_53، يُعاد هنا كخطّ دفاع ثانٍ
    ضد ارتداد أثناء تعديلات لاحقة على نفس المسار).
    """
    r = client.post("/report", headers=bearer(user_token),
                    json={"target_type": "message", "target_id": 999999999, "reason": "other"})
    assert r.status_code == 404


@pytest.mark.needs_db
def test_64_admin_users_truncation_is_reported_not_silent(client, admin_token):
    """
    /admin/users كانت تُرجع مصفوفة مبتورة بصمت عند ٢٠٠. الشكل
    صار {items, total, truncated} — truncated=False طالما total
    الفعلي (مؤكَّد باستعلام مباشر) لا يتجاوز طول items.
    """
    r = client.get("/admin/users", headers=bearer(admin_token))
    assert r.status_code == 200
    d = r.json()
    assert set(d.keys()) >= {"items", "total", "truncated"}
    with main.SessionLocal() as db:
        real_total = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
    assert d["total"] == real_total
    assert d["truncated"] == (real_total > len(d["items"]))
    assert len(d["items"]) <= 200


def test_65_icons_are_real_png_not_svg_in_disguise(client):
    """
    icon-192.png وicon-512.png كانا ملفّ icon.svg نفسه بامتداد
    .png (بصمة واحدة، توقيع '<svg' لا PNG). يفحص كل ملفّ أيقونة
    فعلياً: توقيع PNG الثنائي، وأبعاده الحقيقية عبر Pillow، لا
    امتداد الاسم وحده.
    """
    pytest.importorskip("PIL")
    from PIL import Image

    icons_dir = Path(__file__).resolve().parent.parent / "public" / "icons"
    expected = {
        "icon-192.png": 192, "icon-512.png": 512, "icon-1024.png": 1024,
        "icon-maskable-192.png": 192, "icon-maskable-512.png": 512,
    }
    png_magic = b"\x89PNG\r\n\x1a\n"
    for name, size in expected.items():
        path = icons_dir / name
        assert path.exists(), f"{name} غير موجود"
        head = path.read_bytes()[:8]
        assert head == png_magic, f"{name} ليس PNG فعلياً — يبدأ بـ{head!r}"
        with Image.open(path) as im:
            assert im.size == (size, size), f"{name} بأبعاد {im.size} لا {size}x{size}"

    # المانيفست يفرّق any عن maskable — دمجهما في ملفّ واحد يُظهر
    # حشواً زائداً على أندرويد أو قصّاً على "any".
    import json
    manifest = json.loads((icons_dir.parent / "manifest.json").read_text(encoding="utf-8"))
    purposes = {i["src"]: i["purpose"] for i in manifest["icons"]}
    assert purposes.get("icons/icon-192.png") == "any"
    assert purposes.get("icons/icon-maskable-192.png") == "maskable"


def test_66_maskable_icon_content_stays_inside_safe_zone(client):
    """
    الأيقونة القابلة للقصّ يجب أن تُخزَّن محتواها داخل منطقة أمان
    ٨٠٪ الوسطى — أنظمة أندرويد تقصّ الزوايا بأشكال مختلفة، وأي
    محتوى خارج هذه المنطقة قد يُقصّ.
    """
    pytest.importorskip("PIL")
    from PIL import Image

    root = Path(__file__).resolve().parent.parent
    path = root / "public" / "icons" / "icon-maskable-512.png"

    # الخلفية الحقيقية هي BG في make_icons.py — لا لون ثابت مفترَض هنا.
    # كانت هذه القيمة (13, 17, 23) خلفية icon.svg، ملفّ قديم منفصل لا
    # علاقة له بالمولِّد الحالي (جولة الأيقونات: هندسة داخلية مُتحقَّق
    # منها من الشعار الرسمي، BG أسود صراحةً) — فشلت مقارنةً بمرجع خاطئ
    # لا لأن الأيقونة معطوبة. جذر المشروع مُضاف أصلاً إلى sys.path في
    # conftest.py فـ import make_icons يعمل بلا أي تعديل هنا.
    import make_icons
    bg_expected = make_icons.BG

    with Image.open(path) as im:
        w, h = im.size
        for corner in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
            assert im.getpixel(corner) == bg_expected, \
                f"زاوية {corner} ليست الخلفية الصِرفة — محتوى تسرّب خارج منطقة الأمان"


# ══════════════════════════════════════════════════════════════
# الجولة د — النشر
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_67_prelaunch_lock_blocks_everything_except_health(client, monkeypatch):
    """
    قفل ما قبل الإطلاق (main.py: prelaunch_lock) — الموقع يجب ألّا
    يكون علنياً قبل جاهزيته. HTTP Basic Auth يحجب كل مسار ما عدا
    /health (فحوص Railway الصحية يجب أن تمرّ حتى خلف القفل).
    """
    monkeypatch.setattr(main, "_PRELAUNCH_LOCK", True)
    monkeypatch.setenv("PRELAUNCH_USER", "smoke")
    monkeypatch.setenv("PRELAUNCH_PASS", "smoke-pass-123")

    assert client.get("/health").status_code == 200, "/health يجب أن يمرّ حتى خلف القفل"

    no_auth = client.get("/index.html")
    assert no_auth.status_code == 401
    assert "WWW-Authenticate" in no_auth.headers

    bad = client.get("/index.html", auth=("wrong", "wrong"))
    assert bad.status_code == 401

    ok = client.get("/index.html", auth=("smoke", "smoke-pass-123"))
    assert ok.status_code == 200

    api = client.get("/companies")
    assert api.status_code == 401, "القفل يجب أن يغطّي نقاط الـAPI أيضاً لا الصفحات وحدها"


def test_68_prelaunch_lock_fails_closed_without_credentials_configured(client, monkeypatch):
    """
    تفعيل القفل بلا PRELAUNCH_USER/PRELAUNCH_PASS مضبوطين يجب أن
    يمنع لا أن يسمح — قفل يظنّه المشغِّل يعمل بينما هو معطَّل بصمت
    أسوأ من عدم وجوده أصلاً.
    """
    monkeypatch.setattr(main, "_PRELAUNCH_LOCK", True)
    monkeypatch.delenv("PRELAUNCH_USER", raising=False)
    monkeypatch.delenv("PRELAUNCH_PASS", raising=False)
    r = client.get("/index.html")
    assert r.status_code == 503, "بلا بيانات اعتماد يجب أن يُمنع الوصول لا أن يُسمح به"


@pytest.mark.needs_db
def test_69_internal_purge_trigger_requires_token(client, monkeypatch):
    """
    /internal/run-purge-job — مُشغِّل احتياطي خارجي (مُجدوِل خارج
    Railway) لحلقة التطهير. 404 لا 401/403 عمداً: لا يكشف وجود
    المسار لفاحص عشوائي بلا الرمز الصحيح.
    """
    monkeypatch.setenv("INTERNAL_JOB_TOKEN", "smoke-token-xyz")

    assert client.post("/internal/run-purge-job").status_code == 404
    assert client.post("/internal/run-purge-job",
                       headers={"X-Internal-Token": "wrong"}).status_code == 404

    r = client.post("/internal/run-purge-job",
                    headers={"X-Internal-Token": "smoke-token-xyz"})
    assert r.status_code == 200
    assert r.json()["triggered"] is True
    assert "recent" in r.json()


def test_70_every_env_var_main_reads_is_in_env_example(client):
    """
    انحراف حقيقي وقع فعلاً: main.py قرأ PRELAUNCH_LOCK/USER/PASS
    وINTERNAL_JOB_TOKEN قبل أن تصل أسماؤها كأسطر فعلية (لا تعليقات)
    في .env.example — قائمة النسخ إلى Railway بُنيت من ملفّ ناقص،
    فنشرت الموقع بلا القفل الذي صُمِّم خصيصاً لمنع ذلك. هذا الاختبار
    يقرأ os.getenv الفعلية من main.py وmailer.py، ويقارنها بأسطر
    KEY= الفعّالة (لا التعليقات) في .env.example.
    """
    root = Path(__file__).resolve().parent.parent
    main_src = (root / "main.py").read_text(encoding="utf-8")
    mailer_src = (root / "mailer.py").read_text(encoding="utf-8")

    read_vars = set(re.findall(r'os\.getenv\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', main_src))
    read_vars |= set(re.findall(r'_env\(\s*["\']([A-Z_][A-Z0-9_]*)["\']', mailer_src))

    # اختبارات محلية وحدها — tests/conftest.py يضبطها، لا .env
    read_vars.discard("DISABLE_PURGE_LOOP")

    example = (root / ".env.example").read_text(encoding="utf-8")
    documented = set(re.findall(r'(?m)^([A-Z_][A-Z0-9_]*)=', example))

    missing = read_vars - documented
    assert not missing, (
        f"main.py/mailer.py يقرآن {missing} ولا وجود لها كأسطر فعّالة "
        f"(لا تعليقات) في .env.example — أضِفها قبل أن تُنسَخ القائمة "
        f"إلى Railway ناقصة."
    )


def test_71_procfile_has_no_ineffective_release_line(client):
    """
    Procfile كان يحمل `release: alembic upgrade head` — جُرِّب
    فعلياً على Railway (Nixpacks) فوصل uvicorn إلى import main
    مباشرة بلا ترحيل يسبقه: Nixpacks لا يقرأ عملية release كما
    تفعل Heroku. سطر يبدو أنه يعمل بلا أثر فعلي أخطر من غيابه —
    الترحيل الآن حصراً عبر Pre-Deploy Command في لوحة Railway،
    موثَّق في README_LAUNCH.md.
    """
    root = Path(__file__).resolve().parent.parent
    procfile = (root / "Procfile").read_text(encoding="utf-8")
    assert "release:" not in procfile, \
        "release: في Procfile بلا أثر على Railway/Nixpacks — احذفه"
    assert re.search(r"(?m)^web:\s*uvicorn main:app", procfile), \
        "عملية web غائبة أو بصيغة غير متوقَّعة"

    readme = (root / "README_LAUNCH.md").read_text(encoding="utf-8")
    assert "Pre-Deploy Command" in readme, \
        "README_LAUNCH.md يجب أن يوثّق أن الترحيل يُضبط من Pre-Deploy Command"


def test_72_startup_errors_do_not_name_env_file(client):
    """
    main.py:39,48,60 كانت تقول "is not set in .env" — على Railway
    لا يوجد هذا الملفّ إطلاقاً، فالرسالة تُضلِّل من يشخِّص عطلاً في
    سجلّات الإنتاج نحو مكان لا وجود له. يجب أن تشير إلى "environment"
    لا إلى ملفّ محلّي بعينه.
    """
    root = Path(__file__).resolve().parent.parent
    main_src = (root / "main.py").read_text(encoding="utf-8")
    leaks = re.findall(r'raise RuntimeError\("[^"]*is not set in \.env[^"]*"\)', main_src)
    assert not leaks, f"رسائل تشير إلى .env لا إلى البيئة: {leaks}"


# ══════════════════════════════════════════════════════════════
# جولة الملاحظات ١ — أربع ملاحظات من الفحص على bonyans.com الحيّ
# ══════════════════════════════════════════════════════════════

def test_73_register_form_offers_all_18_governorates_on_empty_db(client):
    """
    كانت قائمة المحافظات في نموذج تسجيل الشركة تُشتقّ من
    `companies.city` — على قاعدة بلا شركات، هذه القائمة فارغة،
    فأول شركة لا تستطيع التسجيل أبداً، ولا سبيل لملء القاعدة.
    الحلّ: مصدران — التسجيل يأخذ قائمة العراق الثابتة من الكود
    (bn-filters.js)، والفلاتر وحدها تبقى مشتقّة. النموذج انتقل
    إلى register.html المستقلّة (جولة الملاحظات ٢) فهذا الاختبار
    يقرأ تلك الصفحة نصّياً: يثبت أن fillCities لا تشتقّ من بيانات
    شركات، وأن القائمة الثابتة فيها ١٨ محافظة فعلاً.
    """
    root = Path(__file__).resolve().parent.parent
    filters_src = (root / "public" / "bn-filters.js").read_text(encoding="utf-8")
    reg_src = (root / "public" / "register.html").read_text(encoding="utf-8")

    m = re.search(r"IRAQ_CITIES\s*=\s*\[(.*?)\]", filters_src, re.S)
    assert m, "IRAQ_CITIES غائبة عن bn-filters.js"
    cities = re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1))
    cities = [a or b for a, b in cities]
    assert len(cities) == 18, f"يجب أن تحمل القائمة ١٨ محافظة، وُجد {len(cities)}"

    assert "IRAQ_CITIES" in reg_src, \
        "register.html لا يستعمل القائمة الثابتة لتعبئة نموذج التسجيل"
    fill_fn = re.search(r"function fillCities\(\)\s*\{.*?\n  \}", reg_src, re.S)
    assert fill_fn, "fillCities غائبة عن register.html"
    assert "companies.map" not in fill_fn.group(0) and "c.city" not in fill_fn.group(0), \
        "نموذج التسجيل ما زال يشتقّ المدن من الشركات القائمة — يفشل على قاعدة فارغة"
    assert "IRAQ_CITIES" in fill_fn.group(0), \
        "نموذج التسجيل يجب أن يعبّئ من القائمة الثابتة"

    # index.html لم يعد يحمل نافذة تسجيل — الوعد الآخر لهذه الجولة
    # (إلغاء النوافذ المنبثقة) يفشل بصمت لو بقيت بقايا منها.
    index_src = (root / "public" / "index.html").read_text(encoding="utf-8")
    assert "regOverlay" not in index_src and "openRegModal" not in index_src, \
        "index.html ما زال يحمل بقايا نافذة التسجيل المنبثقة"


@pytest.mark.needs_db
def test_74_company_registration_creates_verify_row(client, db):
    """
    الوعد: تسجيل شركة يُصدر تفعيلاً بلهجة 'company' — لا يكتفي بصفّ
    /auth/register (الذي يُصدر بلهجة 'user' منذ قبل هذه الجولة أصلاً،
    فوجود صفّ وحده لا يثبت الفجوة المُصلَحة). الاختبار يحفظ صفّ
    التفعيل بعد auth/register، ثم يتحقّق أن POST /company/create
    يُبطله (used_at لم يعد NULL) ويُصدر صفّاً جديداً مكانه —
    دليل إعادة الإصدار بلهجة الشركة، لا مجرّد وجود صفّ قديم.
    """
    email = f"{SMOKE_PREFIX.lower()}reg1@seed.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        db.commit()

    r = client.post("/auth/register", json={
        "email": email, "password": "RegTest!2026", "accept_terms": True,
    })
    assert r.status_code == 200, r.text
    user_token = r.json()["token"]

    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar()
        row_after_register = db.execute(text(
            "SELECT id FROM email_tokens WHERE user_id=:u AND purpose='verify' "
            "AND used_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ), {"u": uid}).fetchone()
        assert row_after_register, "auth/register لم يُنشئ صفّ تفعيل — خارج نطاق هذه الجولة أصلاً"
        register_row_id = row_after_register[0]

    r = client.post("/company/create", headers=bearer(user_token), json={
        "name": SMOKE_PREFIX + "شركة الاختبار",
        "city": "بغداد", "phone": "07700000000", "spec": "مقاولات عامة",
    })
    assert r.status_code == 200, r.text

    with main.SessionLocal() as db:
        register_row_used_at = db.execute(text(
            "SELECT used_at FROM email_tokens WHERE id=:i"
        ), {"i": register_row_id}).scalar()
        assert register_row_used_at is not None, (
            "company/create لم يُبطل صفّ التفعيل الصادر بلهجة 'user' — "
            "لا إعادة إصدار بلهجة 'company' وقعت"
        )
        new_row = db.execute(text(
            "SELECT id FROM email_tokens WHERE user_id=:u AND purpose='verify' "
            "AND used_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ), {"u": uid}).fetchone()
        assert new_row and new_row[0] != register_row_id, \
            "company/create لم يُصدر صفّ تفعيل جديداً بلهجة 'company'"

        db.execute(text("DELETE FROM companies WHERE owner_user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM profiles WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
        db.commit()


@pytest.mark.needs_db
def test_75_unverified_email_blocks_project_and_bid_not_login(client, db):
    """
    غير المُفعَّل يُرفض عند طرح مشروع وعند تقديم عرض (403) — لا عند
    الدخول نفسه. يسجّل مستخدماً جديداً (غير مُفعَّل افتراضاً)، يحاول
    POST /projects، ثم يحوّله لشركة (تبقى غير مُفعَّلة) ويحاول
    POST /projects/{id}/bid.
    """
    email = f"{SMOKE_PREFIX.lower()}reg2@seed.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        db.commit()

    r = client.post("/auth/register", json={
        "email": email, "password": "RegTest!2026", "accept_terms": True,
    })
    assert r.status_code == 200, r.text
    user_token = r.json()["token"]

    with main.SessionLocal() as db:
        verified = db.execute(text("SELECT is_email_verified FROM users WHERE email=:e"),
                              {"e": email}).scalar()
    assert not verified, "حساب جديد يجب أن يبدأ غير مُفعَّل"

    r = client.post("/projects", headers=bearer(user_token), json={
        "title": "SMOKE مشروع", "category": "بناء", "city": "بغداد",
        "contact_name": "ت", "contact_phone": "07700000000",
    })
    assert r.status_code == 403, r.text

    r = client.post("/company/create", headers=bearer(user_token), json={
        "name": SMOKE_PREFIX + "شركة أخرى",
        "city": "بغداد", "phone": "07700000000", "spec": "مقاولات عامة",
    })
    assert r.status_code == 200, r.text
    company_token = r.json()["token"]

    r = client.post("/projects/1/bid", headers=bearer(company_token),
                    json={"price": 1000.0})
    assert r.status_code == 403, r.text

    # الدخول نفسه لا يُمنع — لم نمنعه هنا، فقط تحقّقنا من ٤٠١ لا ٤٠٣
    # على /auth/login سيكون اختباراً منفصلاً عن نطاق هذا البند.

    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar()
        db.execute(text("DELETE FROM companies WHERE owner_user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM profiles WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
        db.commit()


@pytest.mark.needs_db
def test_76_verify_code_locks_after_5_wrong_attempts(client, user_token):
    """
    ٥ محاولات خاطئة تُبطل الرمز (لا الرابط) — عبر جدول rate_limits
    القائم. يُصدر رمزاً حقيقياً، يخطئ خمس مرات، يتحقّق أن المحاولة
    السادسة (حتى بالرمز الصحيح) تُرفض بـ429، وأن code_hash صار NULL.
    """
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                         {"e": "client@seed.test"}).scalar()
        db.execute(text("DELETE FROM rate_limits WHERE key=:k"),
                  {"k": f"verifycode:uid:{uid}"})
        db.commit()

    raw_code = main._new_code()
    _raw_tok, _hashed_tok = main._new_token()
    with main.SessionLocal() as db:
        db.execute(text("""
            UPDATE email_tokens SET used_at = now()
            WHERE user_id=:u AND purpose='verify' AND used_at IS NULL
        """), {"u": uid})
        db.execute(text("""
            INSERT INTO email_tokens (user_id, purpose, token_hash, expires_at,
                                       code_hash, code_expires_at)
            VALUES (:u, 'verify', :h, now() + interval '1 day',
                    :ch, now() + interval '15 minutes')
        """), {"u": uid, "h": _hashed_tok, "ch": main._hash_code(raw_code)})
        db.commit()

    try:
        for _ in range(5):
            r = client.post("/auth/verify-email-code", headers=bearer(user_token),
                            json={"code": "000000"})
            assert r.status_code == 400, r.text

        r = client.post("/auth/verify-email-code", headers=bearer(user_token),
                        json={"code": raw_code})
        assert r.status_code == 429, \
            f"يجب أن تُرفض المحاولة السادسة حتى برمز صحيح، وردّت {r.status_code}"

        with main.SessionLocal() as db:
            row = db.execute(text(
                "SELECT code_hash FROM email_tokens WHERE user_id=:u AND purpose='verify' "
                "AND used_at IS NULL ORDER BY created_at DESC LIMIT 1"
            ), {"u": uid}).mappings().fetchone()
            assert row and row["code_hash"] is None, "الرمز يجب أن يُبطَل (code_hash=NULL) بعد الحدّ"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM rate_limits WHERE key=:k"),
                      {"k": f"verifycode:uid:{uid}"})
            db.execute(text("""
                DELETE FROM email_tokens WHERE user_id=:u AND purpose='verify'
                AND used_at IS NULL
            """), {"u": uid})
            db.commit()


# ══════════════════════════════════════════════════════════════
# جولة الملاحظات ٢ — register.html وتفعيل بالرمز مع دخول تلقائي
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_77_registration_creates_verify_row_for_both_roles(client, db):
    """
    "التسجيل بالنوعين ينشئ صفّ تفعيل في email_tokens" — test_74
    يثبت إعادة الإصدار بلهجة 'company' عند company/create، وهذا
    يثبت الحالة الأبسط: صاحب مشروع (بلا company/create إطلاقاً)
    يُصدر له صفّ تفعيل من auth/register وحدها.
    """
    email = f"{SMOKE_PREFIX.lower()}reg3@seed.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        db.commit()

    r = client.post("/auth/register", json={
        "email": email, "password": "RegTest!2026", "accept_terms": True,
    })
    assert r.status_code == 200, r.text

    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar()
        row = db.execute(text(
            "SELECT id FROM email_tokens WHERE user_id=:u AND purpose='verify' "
            "AND used_at IS NULL ORDER BY created_at DESC LIMIT 1"
        ), {"u": uid}).fetchone()
        assert row, "تسجيل صاحب مشروع لم يُنشئ صفّ تفعيل في email_tokens"

        db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM profiles WHERE user_id=:u"), {"u": uid})
        db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
        db.commit()


@pytest.mark.needs_db
def test_78_correct_code_returns_session_cookie_with_right_role(client, db):
    """
    "الرمز الصحيح يعيد كعكة جلسة صالحة، والدور فيها صحيح" — يسجّل
    شركة كاملة (auth/register ثم company/create)، يُصدر رمزاً
    حقيقياً، يدخله، ويتحقّق: 200 · كعكة bn_sess في set-cookie ·
    الحقل role في الاستجابة "company" · التوجيه إلى /app/.
    """
    email = f"{SMOKE_PREFIX.lower()}reg4@seed.test"
    with main.SessionLocal() as db:
        db.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        db.commit()

    r = client.post("/auth/register", json={
        "email": email, "password": "RegTest!2026", "accept_terms": True,
    })
    assert r.status_code == 200, r.text
    tok = r.json()["token"]

    r = client.post("/company/create", headers=bearer(tok), json={
        "name": SMOKE_PREFIX + "شركة الرمز",
        "city": "بغداد", "phone": "07700000000", "spec": "مقاولات عامة",
    })
    assert r.status_code == 200, r.text
    company_tok = r.json()["token"]

    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar()
        db.execute(text("DELETE FROM rate_limits WHERE key=:k"),
                  {"k": f"verifycode:uid:{uid}"})

    raw_code = main._new_code()
    _raw_tok, hashed_tok = main._new_token()
    with main.SessionLocal() as db:
        db.execute(text("""
            UPDATE email_tokens SET used_at = now()
            WHERE user_id=:u AND purpose='verify' AND used_at IS NULL
        """), {"u": uid})
        db.execute(text("""
            INSERT INTO email_tokens (user_id, purpose, token_hash, expires_at,
                                       code_hash, code_expires_at)
            VALUES (:u, 'verify', :h, now() + interval '1 day',
                    :ch, now() + interval '15 minutes')
        """), {"u": uid, "h": hashed_tok, "ch": main._hash_code(raw_code)})
        db.commit()

    try:
        r = client.post("/auth/verify-email-code", headers=bearer(company_tok),
                        json={"code": raw_code})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("role") == "company", f"الدور يجب أن يكون company، جاء {d.get('role')}"
        assert d.get("redirect") == "/app/index.html"
        assert d.get("token"), "لا رمز جديد في الاستجابة"

        cookie = r.headers.get("set-cookie", "")
        assert main.SESSION_COOKIE in cookie, "لا كعكة جلسة في استجابة الرمز الصحيح"
        assert "HttpOnly" in cookie

        payload = _jose_jwt.decode(d["token"], main.JWT_SECRET, algorithms=[main.ALGORITHM])
        assert payload["role"] == "company", "الرمز الجديد نفسه لا يحمل دور company"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM companies WHERE owner_user_id=:u"), {"u": uid})
            db.execute(text("DELETE FROM profiles WHERE user_id=:u"), {"u": uid})
            db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
            db.execute(text("DELETE FROM rate_limits WHERE key=:k"),
                      {"k": f"verifycode:uid:{uid}"})
            db.execute(text("DELETE FROM users WHERE id=:u"), {"u": uid})
            db.commit()


@pytest.mark.needs_db
def test_79_email_link_verifies_but_creates_no_session(client, user_token):
    """
    🔴 أهمّ اختبار في الجولة — الحدّ الأمني الذي يفصل رابط البريد
    عن الرمز: من ينقر الرابط (ماسح آلي محتمل، Outlook Defender
    وأمثاله) يُفعَّل بريده فقط، ولا تُنشأ له جلسة إطلاقاً. بلا هذا
    الاختبار، تُعاد هذه الثغرة أول مرة يلمس أحد /auth/verify-email
    ويضيف إليها set_session_cookie قياساً على verify-email-code.
    """
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)=:e"),
                         {"e": "client@seed.test"}).scalar()

    raw, hashed = main._new_token()
    with main.SessionLocal() as db:
        db.execute(text("""
            UPDATE email_tokens SET used_at = now()
            WHERE user_id=:u AND purpose='verify' AND used_at IS NULL
        """), {"u": uid})
        db.execute(text("""
            INSERT INTO email_tokens (user_id, purpose, token_hash, expires_at)
            VALUES (:u, 'verify', :h, now() + interval '1 day')
        """), {"u": uid, "h": hashed})
        db.commit()

    try:
        r = client.post("/auth/verify-email", json={"token": raw})
        assert r.status_code == 200, r.text
        d = r.json()

        assert "token" not in d, "رابط البريد لا يجوز أن يعيد رمز جلسة"
        assert "redirect" not in d, "رابط البريد لا يجوز أن يقترح توجيهاً كأنه دخول"

        cookie = r.headers.get("set-cookie", "")
        assert main.SESSION_COOKIE not in cookie, \
            "رابط البريد أنشأ كعكة جلسة — يجب أن يُفعّل البريد فقط بلا جلسة"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM email_tokens WHERE user_id=:u"), {"u": uid})
            db.execute(text("UPDATE users SET is_email_verified=true WHERE id=:u"), {"u": uid})
            db.commit()


@pytest.mark.needs_db
def test_81_malformed_admin_password_hash_fails_closed(client, monkeypatch):
    """
    عطب حيّ ثانٍ لوحظ أثناء تشخيص دخول المدير: ADMIN_PASSWORD_HASH
    مصدرها متغيّر بيئة بشري (عرضة للقصّ الخاطئ عند اللصق) —
    pwd_context.verify() يرفع استثناءً (لا يعيد False) على تجزئة لا
    تطابق أي مخطّط معروف، فكان POST /login يعيد 500 بدل 401.
    مسار مصادقة ينهار على إعداد خاطئ أخطر من رفضه بأدب: يجب أن يفشل
    مغلقاً — 401 كأي كلمة مرور خاطئة، بلا كشف السبب للزائر.
    """
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "not-a-valid-bcrypt-hash")
    r = client.post("/login", json={"username": main.ADMIN_USERNAME, "password": "anything"})
    assert r.status_code == 401, (
        f"تجزئة تالفة يجب أن تُرفض بـ401 (فشل مغلق) لا {r.status_code} — "
        f"استثناء passlib غير المُعالَج ينهار المسار كاملاً"
    )
    _wipe_rate_limits()


# ══════════════════════════════════════════════════════════════
# توحيد المصادقة — الكعكة تُقبَل حين تغيب الترويسة + Reply-To
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_82_api_call_authenticates_from_cookie_alone(client, admin_token):
    """
    عطب دخول المدير الحقيقي: صفحة دخول قد تكتب الكعكة (يضعها الخادم
    دائماً) بلا أن تكتب bn_token في localStorage — فتفشل نداءات
    الـAPI (Authorization فقط) صامتة رغم جلسة صالحة فعلاً. الإصلاح:
    _decode_token يقبل كعكة الجلسة حين تغيب الترويسة، فتعمل نداءات
    الـAPI حتى لو نسيت صفحة الدخول (الحالية أو مستقبلية) كتابة
    localStorage — الاصطلاح صار محروساً لا معتمَداً على الذاكرة.
    """
    # TestClient يحتفظ بالكعكات بين الاختبارات (نفس عميل الجلسة) —
    # بلا مسحٍ صريح قد تتسرّب كعكة admin_token من اختبار سابق فتُخفي
    # الحالة "بلا جلسة" الحقيقية.
    client.cookies.clear()
    try:
        r = client.get("/admin/companies", headers={"Authorization": ""})
        assert r.status_code == 401, "بلا كعكة ولا ترويسة يجب أن يُرفض"

        client.cookies.set(main.SESSION_COOKIE, admin_token)
        r = client.get("/admin/companies", headers={"Authorization": ""})
        assert r.status_code == 200, (
            f"كعكة جلسة صالحة وحدها يجب أن تكفي لمصادقة نداء API — وردّ {r.status_code}"
        )
    finally:
        client.cookies.clear()


def test_83_mailer_send_includes_reply_to_support_email(monkeypatch):
    """
    Reply-To عنوان دعم حقيقي على كل رسالة (لا اسم قالب بعينه) —
    يُضاف مرّة واحدة في send() نفسها. يعترض httpx.post ليقرأ الحمولة
    الفعلية المُرسَلة لا افتراضاً عنها.
    """
    import mailer

    monkeypatch.setenv("RESEND_API_KEY", "smoke-fake-key")
    monkeypatch.setenv("SUPPORT_EMAIL", "support@bonyans.com")
    captured = {}

    class _FakeResp:
        status_code = 200
        text = "{}"

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp()

    monkeypatch.setattr(mailer.httpx, "post", _fake_post)

    ok = mailer.send("someone@seed.test", "موضوع", "نصّ", "<p>HTML</p>")
    assert ok is True
    assert captured["json"].get("reply_to") == "support@bonyans.com", \
        f"Reply-To غائب أو خاطئ في الحمولة المُرسَلة: {captured['json']}"


def test_84_every_mail_template_sends_both_text_and_html(monkeypatch):
    """
    "نسخة نصّية دائماً مع كل رسالة HTML" (MAIL-TEXTS.md، القاعدة ٦) —
    يعترض mailer.send نفسها ويستدعي القوالب الستّة جميعاً، فيتحقّق
    أن كل استدعاء حمل نصّاً وHTML غير فارغين معاً — لا أحدهما فقط.
    """
    import mailer

    calls = []
    monkeypatch.setattr(
        mailer, "send",
        lambda to, subject, text, html: calls.append((subject, text, html)) or True
    )

    mailer.password_reset("someone@seed.test", "https://bonyans.com/reset.html?token=x")
    mailer.email_verify("someone@seed.test", "https://bonyans.com/verify.html?token=x",
                        "user", "123456")
    mailer.email_change_confirm("someone@seed.test", "https://bonyans.com/verify.html?change=x")
    mailer.email_change_alert("someone@seed.test")
    mailer.account_deleted("someone@seed.test", "٢٠٢٦-١٠-٠١")
    mailer.project_hidden("someone@seed.test", "SMOKE مشروع", "محتوى مخالف")

    assert len(calls) == 6, f"توقّعت ٦ رسائل، نُفِّذت {len(calls)}"
    for subject, txt, html in calls:
        assert txt and txt.strip(), f"«{subject}» بلا نسخة نصّية"
        assert html and html.strip(), f"«{subject}» بلا نسخة HTML"


def test_85_no_get_route_writes_to_database(client):
    """
    الحارس الدائم على قرار CSRF في _decode_token: قبول الكعكة حين
    تغيب الترويسة آمن فقط طالما لا @app.get يكتب في القاعدة (SameSite
    =Lax يرسل الكعكة عبر المواقع في تنقّل GET كامل). فحص لمرّة واحدة
    وقت الإصلاح ليس حارساً — @app.get جديد يستدعي db.commit() يعيد
    فتح الباب صامتاً. هذا الاختبار يحوّل ذلك الفحص اليدوي إلى حارس
    آلي دائم يقرأ main.py نصّياً.
    """
    root = Path(__file__).resolve().parent.parent
    src = (root / "main.py").read_text(encoding="utf-8")
    lines = src.split("\n")

    decorators = []
    for i, line in enumerate(lines):
        m = re.match(r'@app\.(get|post|put|delete|patch)\("([^"]+)"', line.strip())
        if m:
            decorators.append((i, m.group(1), m.group(2)))

    offenders = []
    for idx, (i, method, path) in enumerate(decorators):
        if method != "get":
            continue
        end = decorators[idx + 1][0] if idx + 1 < len(decorators) else len(lines)
        body = "\n".join(lines[i:end])
        if "db.commit()" in body:
            offenders.append(path)

    # الاستثناء الوحيد المقبول: GET /company/{company_id} يكتب عدّاد
    # مشاهدة عام بلا مصادقة إطلاقاً (لا resolve_identity ولا كعكة) —
    # لا علاقة له بقرار CSRF هذا، فأي زائر يصل إليه بلا جلسة أصلاً.
    offenders = [p for p in offenders if p != "/company/{company_id}"]
    assert not offenders, (
        f"مسارات GET التالية تكتب في القاعدة — قابلة للاستغلال عبر CSRF "
        f"(SameSite=Lax يسمح بها في تنقّل كامل): {offenders}. حوّلها إلى POST."
    )


@pytest.mark.needs_db
def test_86_read_receipt_moved_off_get_to_dedicated_post(client, company_token, user_token):
    """
    كانت GET /conversations/{id}/messages تُعلّم الرسائل مقروءة —
    كتابة داخل GET، منفذ CSRF محتمل بعد قبول الكعكة في _decode_token.
    نُقلت إلى POST /conversations/{id}/mark-read: يثبت أن GET صار
    قراءة صرفة (لا تُعلّم شيئاً)، وأن POST الجديدة تفعل ذلك فعلاً.
    """
    with main.SessionLocal() as db:
        # company_id عبر بريد البذر تحديداً — لا "أوّل ملفّ شركة"
        # (فرع الاختبار الآن نسخة كاملة من الإنتاج، وأوّل ملفّ
        # زمنياً قد يكون شركة حقيقية غير company@seed.test التي
        # يصادق بها company_token فعلياً، فيُرفض الطلب بـ403 كاذب).
        cid = db.execute(text("""
            SELECT p.company_id FROM profiles p JOIN users u ON u.id=p.user_id
            WHERE p.role='company' AND lower(u.email)='company@seed.test'
            ORDER BY p.created_at LIMIT 1
        """)).scalar()
        uid = db.execute(text(
            "SELECT id FROM users WHERE lower(email)='client@seed.test'"
        )).scalar()
    assert cid and uid, "تحتاج بيانات البذر"

    with main.SessionLocal() as db:
        conv_id = db.execute(text(
            "INSERT INTO conversations(client_user_id, company_id) VALUES (:u,:c) RETURNING id"
        ), {"u": uid, "c": cid}).scalar()
        mid = db.execute(text("""
            INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
            VALUES (:conv,'client',:u,'SMOKE unread') RETURNING id
        """), {"conv": conv_id, "u": uid}).scalar()
        db.commit()

    try:
        r = client.get(f"/conversations/{conv_id}/messages", headers=bearer(company_token))
        assert r.status_code == 200, r.text
        with main.SessionLocal() as db:
            is_read = db.execute(text("SELECT is_read FROM chat_messages WHERE id=:i"),
                                 {"i": mid}).scalar()
        assert is_read is False, "GET وحدها علّمت الرسالة مقروءة — الكتابة عادت إلى GET"

        r = client.post(f"/conversations/{conv_id}/mark-read", headers=bearer(company_token))
        assert r.status_code == 200, r.text
        with main.SessionLocal() as db:
            is_read = db.execute(text("SELECT is_read FROM chat_messages WHERE id=:i"),
                                 {"i": mid}).scalar()
        assert is_read is True, "POST /mark-read لم تُعلّم الرسالة مقروءة"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM chat_messages WHERE conversation_id=:c"), {"c": conv_id})
            db.execute(text("DELETE FROM conversations WHERE id=:c"), {"c": conv_id})
            db.commit()


# ══════════════════════════════════════════════════════════════
# جولة إدارة المشاريع — ترقيم /admin/projects · إخفاء لا رجعة فيه
# ══════════════════════════════════════════════════════════════

def _seed_smoke_projects(db, owner_uid, n=3, status="published"):
    ids = []
    for i in range(n):
        pid = db.execute(text("""
            INSERT INTO projects (title, category, city, country, contact_name,
                                   contact_phone, status, owner_user_id)
            VALUES (:t, 'اختبار', 'بغداد', 'IQ', 'SMOKE مالك', '07700000000', :s, :u)
            RETURNING id
        """), {"t": f"SMOKE مشروع {i}", "s": status, "u": owner_uid}).scalar()
        ids.append(pid)
    db.commit()
    return ids


@pytest.mark.needs_db
def test_87_admin_projects_paginates_on_server(client, admin_token):
    """
    كانت /admin/projects بلا LIMIT — كل الصفوف في استجابة واحدة.
    يزرع أكثر من صفحة واحدة (per_page=2) ويتحقّق أن {items} لا يتجاوز
    الحدّ، وأن {total, pages} حسابان حقيقيان لا تقديريان.
    """
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'"),
                         ).scalar()
        ids = _seed_smoke_projects(db, uid, n=3)

    try:
        r = client.get("/admin/projects", params={"q": "SMOKE مشروع", "per_page": 2, "page": 1},
                       headers=bearer(admin_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(d.keys()) >= {"items", "page", "per_page", "total", "pages"}
        assert len(d["items"]) <= 2, "يتجاوز per_page — لا ترقيم فعلياً"
        assert d["total"] >= 3
        assert d["pages"] >= 2
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM projects WHERE id = ANY(:ids)"), {"ids": ids})
            db.commit()


@pytest.mark.needs_db
def test_88_admin_hidden_project_cannot_be_reverted_outside_unhide(client, admin_token, company_token):
    """
    🔴 أهمّ اختبار في الجولة. admin_hidden منفصلة عمداً عن closed:
    لا مسار يُخرج مشروعاً منها غير POST /unhide (يفرض سبباً مسجَّلاً).
    يثبت ثلاثة أشياء معاً: الإخفاء ينجح · العرض الجديد يُرفض على
    مشروع مخفي (submit_bid) · محاولة تجاوز الإخفاء عبر المسار العامّ
    القديم PUT /admin/projects/{id}/status تُرفض صراحةً — لا "نجاح"
    صامت يُعيد النشر بلا سبب مسجَّل.
    """
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'")).scalar()
        pid = _seed_smoke_projects(db, uid, n=1)[0]
        # submit_bid يشترط شركة معتمدة قبل فحص حالة المشروع — شركة
        # البذر قد لا تكون معتمدة على فرع طازج، فنعتمدها مؤقّتاً هنا
        # (نُعيدها في finally) لعزل ما يختبره هذا البند فعلاً: رفض
        # العروض على مشروع مخفي، لا حالة اعتماد الشركة.
        cid = db.execute(text(
            "SELECT company_id FROM profiles p JOIN users u ON u.id=p.user_id "
            "WHERE p.role='company' AND lower(u.email)='company@seed.test' "
            "ORDER BY p.created_at LIMIT 1"
        )).scalar()
        prev_company_status = db.execute(
            text("SELECT status FROM companies WHERE id=:c"), {"c": cid}
        ).scalar()
        db.execute(text("UPDATE companies SET status='approved' WHERE id=:c"), {"c": cid})
        db.commit()

    try:
        r = client.post(f"/admin/projects/{pid}/hide", headers=bearer(admin_token),
                        json={"reason": "SMOKE محتوى مخالف"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "admin_hidden"

        with main.SessionLocal() as db:
            status = db.execute(text("SELECT status FROM projects WHERE id=:i"),
                                {"i": pid}).scalar()
        assert status == "admin_hidden"

        # الطريق العامّ القديم يُرفض على مشروع مخفي — لا "نجاح" صامت
        r = client.put(f"/admin/projects/{pid}/status", headers=bearer(admin_token),
                       json={"status": "published"})
        assert r.status_code == 400, \
            f"المسار العامّ يجب أن يرفض تجاوز admin_hidden، وردّ {r.status_code}"

        with main.SessionLocal() as db:
            status = db.execute(text("SELECT status FROM projects WHERE id=:i"),
                                {"i": pid}).scalar()
        assert status == "admin_hidden", "تجاوز المسار العامّ الإخفاء الإداري فعلياً"

        # عرض جديد على مشروع مخفي يُرفض
        r = client.post(f"/projects/{pid}/bid", headers=bearer(company_token),
                        json={"price": 1000.0})
        assert r.status_code == 400, "عرض قُبل على مشروع مخفي إدارياً"

        # المسار الوحيد الصحيح للخروج
        r = client.post(f"/admin/projects/{pid}/unhide", headers=bearer(admin_token),
                        json={"reason": "SMOKE تراجعت الإدارة"})
        assert r.status_code == 200, r.text
        with main.SessionLocal() as db:
            status = db.execute(text("SELECT status FROM projects WHERE id=:i"),
                                {"i": pid}).scalar()
        assert status == "published"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM projects WHERE id=:i"), {"i": pid})
            db.execute(text("UPDATE companies SET status=:s WHERE id=:c"),
                      {"s": prev_company_status, "c": cid})
            db.commit()


@pytest.mark.needs_db
def test_89_project_admin_actions_write_audit_log_with_reason(client, admin_token):
    """لا إجراء بلا سبب مكتوب يُسجَّل في security_audit_log."""
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'")).scalar()
        pid = _seed_smoke_projects(db, uid, n=1)[0]

    try:
        r = client.post(f"/admin/projects/{pid}/hide", headers=bearer(admin_token),
                        json={"reason": "SMOKE سبب قابل للتتبّع"})
        assert r.status_code == 200, r.text

        with main.SessionLocal() as db:
            row = db.execute(text("""
                SELECT actor_type, actor_id, meta FROM security_audit_log
                WHERE action = :a ORDER BY created_at DESC LIMIT 1
            """), {"a": f"project_hidden:{pid}"}).mappings().fetchone()
        assert row, "لا صفّ في security_audit_log لإجراء الإخفاء"
        assert row["actor_type"] == "admin"
        assert row["actor_id"] == main.ADMIN_USERNAME
        assert "SMOKE سبب قابل للتتبّع" in (row["meta"] or ""), \
            "السبب المكتوب غير مسجَّل في meta"

        # السبب إلزامي فعلياً — بلا حقل reason يُرفض الطلب بدلاً من
        # المرور بسبب فارغ لا يُسجَّل شيئاً مفيداً
        r2 = client.post(f"/admin/projects/{pid}/hide", headers=bearer(admin_token), json={})
        assert r2.status_code == 422, "غياب السبب يجب أن يُرفض لا أن يُقبَل فارغاً"
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM projects WHERE id=:i"), {"i": pid})
            db.commit()


@pytest.mark.needs_db
def test_90_non_admin_rejected_on_project_admin_action_routes(client, company_token, user_token):
    """غير المدير يُرفض على كل مسارات إجراءات المشاريع الإدارية."""
    with main.SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'")).scalar()
        pid = _seed_smoke_projects(db, uid, n=1)[0]

    try:
        for tok in (company_token, user_token):
            assert client.get("/admin/projects", headers=bearer(tok)).status_code == 403
            assert client.get(f"/admin/projects/{pid}", headers=bearer(tok)).status_code == 403
            assert client.post(f"/admin/projects/{pid}/hide", headers=bearer(tok),
                               json={"reason": "x"}).status_code == 403
            assert client.post(f"/admin/projects/{pid}/unhide", headers=bearer(tok),
                               json={"reason": "x"}).status_code == 403

        # TestClient يحتفظ بالكعكات بين الاختبارات (نفس عميل الجلسة)،
        # و_decode_token صار يقبل الكعكة احتياطاً (توحيد المصادقة) —
        # بلا مسحٍ صريح قد تتسرّب كعكة دور من fixture آخر فتُخفي
        # الحالة "بلا جلسة إطلاقاً" الحقيقية (401 لا 403).
        client.cookies.clear()
        try:
            assert client.get("/admin/projects", headers={"Authorization": ""}).status_code == 401
            assert client.post(f"/admin/projects/{pid}/hide", headers={"Authorization": ""},
                               json={"reason": "x"}).status_code == 401
        finally:
            client.cookies.clear()
    finally:
        with main.SessionLocal() as db:
            db.execute(text("DELETE FROM projects WHERE id=:i"), {"i": pid})
            db.commit()


# ══════════════════════════════════════════════════════════════
# جولة الاشتراكات — بلا تسعير علنيّ، وبلا قيد على شركة بلا اشتراك
# ══════════════════════════════════════════════════════════════

@pytest.mark.needs_db
def test_91_company_without_subscription_works_fully(client, admin_token, company_token, user_token):
    """
    🔴 أهمّ اختبار في الجولة. شركة بلا صفّ في company_subscriptions
    (PRICING_LIVE=False) يجب أن تعمل بالكامل: تظهر في الدليل العام،
    تقدّم أكثر من عرض واحد شهرياً (حدّ STARTER القديم كان ١)،
    وتُراسَل وتُراسِل. لا شيء يمنعها.
    """
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles p JOIN users u ON u.id=p.user_id "
            "WHERE p.role='company' AND lower(u.email)='company@seed.test' "
            "ORDER BY p.created_at LIMIT 1"
        )).scalar()
        uid = db.execute(text("SELECT id FROM users WHERE lower(email)='client@seed.test'")).scalar()

        # لقطة الحالة الحالية — تُستعاد كاملة في finally
        prev_status = db.execute(text("SELECT status, name FROM companies WHERE id=:c"),
                                 {"c": cid}).mappings().fetchone()
        active_subs = db.execute(text(
            "SELECT id FROM company_subscriptions WHERE company_id=:c AND status='active'"
        ), {"c": cid}).mappings().fetchall()

        # بلا اشتراك نشط فعلاً — هذا ما يختبره البند
        db.execute(text("UPDATE company_subscriptions SET status='expired' "
                        "WHERE company_id=:c AND status='active'"), {"c": cid})
        db.execute(text("UPDATE companies SET status='approved' WHERE id=:c"), {"c": cid})
        db.commit()

    pids = []
    conv_id = None
    try:
        with main.SessionLocal() as db:
            pids = _seed_smoke_projects(db, uid, n=2)

        # ١ · تظهر في الدليل العام
        r = client.get("/companies", params={"q": prev_status["name"]})
        assert r.status_code == 200
        names = [c["name"] for c in r.json()["items"]]
        assert prev_status["name"] in names, "شركة بلا اشتراك غابت عن الدليل العام"

        # ٢ · أكثر من عرض واحد شهرياً — حدّ STARTER القديم كان ١
        for pid in pids:
            r = client.post(f"/projects/{pid}/bid", headers=bearer(company_token),
                            json={"price": 5000.0})
            assert r.status_code == 200, \
                f"عرض رُفض على شركة بلا اشتراك (project {pid}): {r.text}"

        # ٣ · تُراسَل وتُراسِل
        r = client.post("/conversations", headers=bearer(user_token),
                        json={"company_id": cid, "message": "SMOKE رسالة أولى"})
        assert r.status_code == 200, f"صاحب مشروع تعذّر عليه بدء محادثة: {r.text}"
        d = r.json()
        conv_id = d.get("id") or d.get("conversation_id")
        assert conv_id, f"لا رقم محادثة في الاستجابة: {r.text}"

        r = client.post(f"/conversations/{conv_id}/messages", headers=bearer(company_token),
                        json={"message": "SMOKE ردّ الشركة"})
        assert r.status_code == 200, f"شركة بلا اشتراك تعذّر عليها الردّ: {r.text}"
    finally:
        with main.SessionLocal() as db:
            for pid in pids:
                db.execute(text("DELETE FROM project_bids WHERE project_id=:p"), {"p": pid})
            if conv_id:
                db.execute(text("DELETE FROM chat_messages WHERE conversation_id=:c"), {"c": conv_id})
                db.execute(text("DELETE FROM conversations WHERE id=:c"), {"c": conv_id})
            for pid in pids:
                db.execute(text("DELETE FROM projects WHERE id=:p"), {"p": pid})
            db.execute(text("UPDATE companies SET status=:s WHERE id=:c"),
                      {"s": prev_status["status"], "c": cid})
            for sub in active_subs:
                db.execute(text("UPDATE company_subscriptions SET status='active' WHERE id=:i"),
                          {"i": sub["id"]})
            db.commit()


def test_92_public_homepage_shows_no_price_or_plan(client):
    """
    الصفحة العامة لا تعرض أي سعر أو باقة — قرار منتج (لا تسعير قبل
    مشاريع حقيقية). يفحص index.html نصّياً: القسم مخفيّ فعلياً
    (hidden)، والعلم PRICING_LIVE=false، والتحميل مشروط به لا يجري
    بلا شرط.
    """
    root = Path(__file__).resolve().parent.parent
    src = (root / "public" / "index.html").read_text(encoding="utf-8")

    m = re.search(r'<section class="sec" id="secPlans"([^>]*)>', src)
    assert m, "قسم الباقات غائب من index.html — لا يجوز حذفه، فقط إخفاؤه"
    assert "hidden" in m.group(1), "قسم الباقات ظاهر — لا يحمل hidden"

    assert re.search(r'const PRICING_LIVE\s*=\s*false\s*;', src), \
        "PRICING_LIVE يجب أن يكون false — لا تسعير علنيّ اليوم"

    boot_m = re.search(r'\(async function boot\(\)\s*\{.*?\}\)\(\);', src, re.S)
    assert boot_m, "دالّة boot غائبة"
    assert "if (PRICING_LIVE)" in boot_m.group(0), \
        "تحميل الباقات في boot() غير مشروط بـPRICING_LIVE"


@pytest.mark.needs_db
def test_93_manual_subscription_assignment_writes_audit_log(client, admin_token):
    """الإسناد اليدوي يكتب في security_audit_log بسببه ومنفّذه."""
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles p JOIN users u ON u.id=p.user_id "
            "WHERE p.role='company' AND lower(u.email)='company@seed.test' "
            "ORDER BY p.created_at LIMIT 1"
        )).scalar()
        prev_active = db.execute(text(
            "SELECT id FROM company_subscriptions WHERE company_id=:c AND status='active'"
        ), {"c": cid}).mappings().fetchall()

    try:
        r = client.put(f"/admin/company/{cid}/subscription", headers=bearer(admin_token),
                       json={"plan_code": "starter", "months": 1,
                             "notes": "SMOKE سبب إسناد قابل للتتبّع"})
        assert r.status_code == 200, r.text

        with main.SessionLocal() as db:
            row = db.execute(text("""
                SELECT actor_type, actor_id, meta FROM security_audit_log
                WHERE action = :a ORDER BY created_at DESC LIMIT 1
            """), {"a": f"subscription_assigned:{cid}"}).mappings().fetchone()
        assert row, "لا صفّ في security_audit_log لإسناد الباقة"
        assert row["actor_type"] == "admin"
        assert row["actor_id"] == main.ADMIN_USERNAME
        assert "SMOKE سبب إسناد قابل للتتبّع" in (row["meta"] or ""), \
            "السبب المكتوب غير مسجَّل في meta"

        # السبب إلزامي فعلياً
        r2 = client.put(f"/admin/company/{cid}/subscription", headers=bearer(admin_token),
                        json={"plan_code": "starter", "months": 1})
        assert r2.status_code == 422, "غياب السبب يجب أن يُرفض لا أن يُقبَل"
    finally:
        with main.SessionLocal() as db:
            ids_to_expire = db.execute(text(
                "SELECT id FROM company_subscriptions WHERE company_id=:c AND status='active'"
            ), {"c": cid}).mappings().fetchall()
            keep_ids = {r["id"] for r in prev_active}
            for row in ids_to_expire:
                if row["id"] not in keep_ids:
                    db.execute(text("UPDATE company_subscriptions SET status='expired' WHERE id=:i"),
                              {"i": row["id"]})
            for r in prev_active:
                db.execute(text("UPDATE company_subscriptions SET status='active' WHERE id=:i"),
                          {"i": r["id"]})
            db.commit()


@pytest.mark.needs_db
def test_94_non_admin_rejected_on_subscription_assignment(client, company_token, user_token):
    """غير المدير يُرفض على مسار الإسناد اليدوي."""
    with main.SessionLocal() as db:
        cid = db.execute(text(
            "SELECT company_id FROM profiles p JOIN users u ON u.id=p.user_id "
            "WHERE p.role='company' AND lower(u.email)='company@seed.test' "
            "ORDER BY p.created_at LIMIT 1"
        )).scalar()

    for tok in (company_token, user_token):
        r = client.put(f"/admin/company/{cid}/subscription", headers=bearer(tok),
                       json={"plan_code": "starter", "months": 1, "notes": "x"})
        assert r.status_code == 403

    client.cookies.clear()
    try:
        r = client.put(f"/admin/company/{cid}/subscription", headers={"Authorization": ""},
                       json={"plan_code": "starter", "months": 1, "notes": "x"})
        assert r.status_code == 401
    finally:
        client.cookies.clear()


# ══════════════════════════════════════════════════════════════
# جولة التثبيت — PWA فقط، لا Capacitor
# ══════════════════════════════════════════════════════════════

def test_95_manifest_has_all_required_install_fields(client):
    """
    manifest.json يحمل كل الحقول الإلزامية للتثبيت الفعلي: name،
    short_name، start_url، display=standalone، scope، theme_color،
    background_color، وأيقونتَي ١٩٢/٥١٢ بـpurpose=maskable على
    الأقل واحدة منهما — وملفّات الأيقونات موجودة فعلاً على القرص
    لا في manifest.json وحده.
    """
    import json as _json

    root = Path(__file__).resolve().parent.parent
    manifest_path = root / "public" / "manifest.json"
    assert manifest_path.exists(), "manifest.json غائب"
    m = _json.loads(manifest_path.read_text(encoding="utf-8"))

    for field in ("name", "short_name", "start_url", "display", "scope",
                  "theme_color", "background_color", "icons"):
        assert field in m and m[field], f"manifest.json ينقصه {field}"
    assert m["display"] == "standalone", "display يجب أن يكون standalone للتثبيت"

    sizes_present = {ic.get("sizes") for ic in m["icons"]}
    assert "192x192" in sizes_present and "512x512" in sizes_present, \
        "تحتاج أيقونتَي ١٩٢ و٥١٢ على الأقل"
    maskable = [ic for ic in m["icons"] if ic.get("purpose") == "maskable"]
    assert maskable, "لا أيقونة واحدة بـ purpose=maskable — التثبيت على أندرويد يحتاجها"

    for ic in m["icons"]:
        icon_path = root / "public" / ic["src"]
        assert icon_path.exists(), f"أيقونة مذكورة في manifest.json لكن غائبة من القرص: {ic['src']}"


def test_96_install_button_wired_through_beforeinstallprompt(client):
    """
    زرّ التثبيت في public/nav.js (كان nav-public.js قبل توحيد ملفّات
    التنقّل الثلاثة): يلتقط beforeinstallprompt ويؤجّله
    (preventDefault)، ولا يظهر إلا بعد التقاطه فعلاً (لا تخميناً أن
    المتصفّح يدعم التثبيت)، ويختفي في وضع standalone كلياً. فحص
    نصّي لمنطق الإظهار/الإخفاء — السلوك الحيّ في المتصفّح في
    test_service_worker.py.
    """
    root = Path(__file__).resolve().parent.parent
    src = (root / "public" / "nav.js").read_text(encoding="utf-8")

    assert "beforeinstallprompt" in src
    assert re.search(r"e\.preventDefault\(\)", src), \
        "لا يؤجّل beforeinstallprompt — سيظهر شريط Chrome التلقائي بدل زرّنا"
    assert "display-mode: standalone" in src or "display-mode:standalone" in src, \
        "لا يفحص وضع standalone — قد يظهر الزرّ لمن ثبّت التطبيق أصلاً"
    assert "isIOS" in src, "لا يميّز iOS — سفاري لا يُطلق beforeinstallprompt إطلاقاً"


def test_99_service_worker_cache_name_derived_not_manual(client):
    """
    CACHE_NAME في service-worker.js عُرِف يدوي نُسي تحديثه ثلاث مرّات
    في جلسة واحدة — كل نسيان أخفى نشرة كاملة عن متصفّحات عائدة
    صامتاً. الآن يُشتقّ من بصمة محتوى public/ كلّه لا يُكتب يدوياً.

    ثلاثة أشياء منفصلة: (أ) GET /service-worker.js الفعلي لا يحمل
    العلامة النائبة __CACHE_VERSION__ — لو ظهرت لعنى أن المسار
    الصريح في main.py لم يسبق StaticFiles فعلاً، والتقط الملف
    الساكن الخام بدلاً منه. (ب) CACHE_NAME في الاستجابة قيمة حقيقية
    غير فارغة. (ج) دالّة الحساب نفسها حسّاسة لأي تغيير حقيقي تحت
    public/ — لا محتوى ثابت مخبَّأ لا يتحرّك.
    """
    r = client.get("/service-worker.js")
    assert r.status_code == 200, r.text
    body = r.text

    assert "__CACHE_VERSION__" not in body, \
        "العلامة النائبة وصلت خاماً — المسار الصريح لم يسبق StaticFiles فعلياً"

    m = re.search(r"const CACHE_NAME\s*=\s*'([^']+)'", body)
    assert m, "CACHE_NAME غائب عن استجابة GET /service-worker.js"
    assert m.group(1).strip(), "CACHE_NAME قيمة فارغة"
    assert m.group(1) != "__CACHE_VERSION__"

    # دالّة الحساب حسّاسة لأي تغيير تحت public/ — بلا إعادة إقلاع خادم
    before = main._compute_public_fingerprint()
    root = Path(__file__).resolve().parent.parent / "public"
    tmp = root / ".fingerprint_smoke_test.tmp"
    try:
        tmp.write_text("smoke", encoding="utf-8")
        after = main._compute_public_fingerprint()
        assert after != before, \
            "البصمة لم تتغيّر بعد إضافة ملفّ تحت public/ — الدالّة لا تعتمد المحتوى الفعلي"
    finally:
        tmp.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════
# جولة التنقّل الموحَّد — public/nav.js يستبدل الملفّات الثلاثة
# ══════════════════════════════════════════════════════════════

def _nav_js_source():
    root = Path(__file__).resolve().parent.parent
    return (root / "public" / "nav.js").read_text(encoding="utf-8")


def test_100_company_surface_has_no_public_or_directory_link(client):
    """
    قاعدة العزل ١ — سطح الشركة لا رابط فيه إلى الصفحة العامة (/) ولا
    إلى دليل الشركات (/companies.html)، لا في القائمة الجانبية
    (COMPANY_BLOCKS) ولا في الشريط السفلي (COMPANY_TABS). فحص نصّي
    على الكتلتين تحديداً — لا الملفّ كلّه، لأن الموقع العام وسطح
    المستخدم يحملان هذين الرابطين شرعاً في مكان آخر من نفس الملفّ.
    """
    src = _nav_js_source()

    m = re.search(r"var COMPANY_BLOCKS = (\[.*?\n  \]);", src, re.S)
    assert m, "COMPANY_BLOCKS غائبة عن nav.js"
    blocks_src = m.group(1)

    m2 = re.search(r"var COMPANY_TABS = (\[.*?\n  \]);", src, re.S)
    assert m2, "COMPANY_TABS غائبة عن nav.js"
    tabs_src = m2.group(1)

    company_src = blocks_src + "\n" + tabs_src
    assert "/companies.html" not in company_src, \
        "رابط عام (دليل الشركات) تسرّب إلى سطح الشركة"
    assert '"/"' not in company_src and "'/'" not in company_src and 'href="/"' not in company_src, \
        "رابط إلى الصفحة العامة تسرّب إلى سطح الشركة"
    assert '"/index.html"' not in company_src and "'/index.html'" not in company_src, \
        "رابط مطلق إلى الرئيسية العامة تسرّب إلى سطح الشركة"


def test_101_user_navigation_links_to_companies_directory(client):
    """
    العزل مرفوع عن سطح المستخدم وحده (صاحب مشروع مشترٍ لا بائع) —
    الشريط السفلي USER_TABS يجب أن يحمل رابطاً إلى دليل الشركات.
    يفشل على القوائم القديمة الثلاث (nav-me.js لم يكن يحمل هذا الرابط
    إطلاقاً — قاعدة العزل ١ كانت تُطبَّق عليه خطأً كما لو كان سطح شركة).
    """
    src = _nav_js_source()
    m = re.search(r"var USER_TABS = (\[.*?\n  \]);", src, re.S)
    assert m, "USER_TABS غائبة عن nav.js"
    assert "/companies.html" in m.group(1), \
        "تنقّل المستخدم لا يحمل رابطاً إلى دليل الشركات"


def test_102_every_company_destination_reachable_on_mobile(client):
    """
    «لا صفحة تفقد طريقها» — التسع وجهات القديمة لسطح الشركة (كانت
    كلّها في نav-app.js) يجب أن تبقى كلّها إمّا في الشريط الأساسي
    (COMPANY_TABS) أو داخل «المزيد» (COMPANY_BLOCKS، اللوحة المنسدلة
    نفسها). فشل هذا الاختبار يعني أن وجهة يتيمة لا مسار جوّالاً إليها.
    """
    src = _nav_js_source()

    m = re.search(r"var COMPANY_BLOCKS = (\[.*?\n  \]);", src, re.S)
    blocks_src = m.group(1)
    m2 = re.search(r"var COMPANY_TABS = (\[.*?\n  \]);", src, re.S)
    tabs_src = m2.group(1)

    required = {
        "index.html", "profile.html", "gallery.html", "market.html",
        "bids.html", "messages.html", "reviews.html", "plan.html", "settings.html",
    }

    block_hrefs = set(re.findall(r"href:\s*'([^']+)'", blocks_src))
    tab_hrefs = {
        h.rsplit("/", 1)[-1]
        for h in re.findall(r"href:\s*'([^']+)'", tabs_src)
    }

    reachable = block_hrefs | tab_hrefs
    missing = required - reachable
    assert not missing, f"وجهات لا مسار جوّالاً إليها (لا في الشريط ولا في المزيد): {missing}"


# ══════════════════════════════════════════════════════════════
# جولة (ب) — بيانات التواصل خلف الدخول
# ══════════════════════════════════════════════════════════════

def _approved_company_with_phone(client, admin_token):
    """ينشئ شركة، يعتمدها، ويعيد (id, phone) — مساعد مشترك للاختبارات الثلاثة."""
    phone = "07000000095"
    body = {"name": SMOKE_PREFIX + "شركة تواصل", "city": "بغداد",
            "phone": phone, "spec": "مقاولات عامة", "desc": "اختبار"}
    r = client.post("/companies", json=body, headers=bearer(admin_token))
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r2 = client.put(f"/companies/{cid}/status", json={"status": "approved"},
                    headers=bearer(admin_token))
    assert r2.status_code == 200, r2.text
    return cid, phone


@pytest.mark.needs_db
def test_103_visitor_company_profile_omits_phone(client, admin_token):
    """
    REQUIRE_LOGIN_FOR_CONTACT=True (الافتراضي) — استجابة /company/{id}
    لزائر بلا أي رمز يجب ألّا تحمل الهاتف إطلاقاً، لا في القيمة ولا
    مخفيّاً بالعرض فقط. contact_locked=True يخبر الواجهة بعرض زرّ
    التسجيل بدل أزرار واتساب/اتصال.
    """
    cid, phone = _approved_company_with_phone(client, admin_token)
    # admin_token يفتح جلسة كعكة على client المشترك (session-scoped) —
    # بلا مسحها هنا فالطلب "الزائر" التالي يصل مصادَقاً فعلياً عبرها.
    client.cookies.clear()
    try:
        r = client.get(f"/company/{cid}")
        assert r.status_code == 200, r.text
        d = r.json()["company"]
        assert d["phone"] is None, "الهاتف وصل زائراً بلا جلسة رغم REQUIRE_LOGIN_FOR_CONTACT"
        assert d["contact_locked"] is True
        assert phone not in r.text, "رقم الهاتف تسرّب في نصّ الاستجابة الخام رغم القفل"
    finally:
        client.cookies.clear()


@pytest.mark.needs_db
def test_104_logged_in_user_sees_company_contact(client, admin_token, user_token):
    """أي دور مُصادَق (هنا صاحب مشروع) يرى الهاتف كاملاً — لا حجب لمن له جلسة."""
    cid, phone = _approved_company_with_phone(client, admin_token)
    r = client.get(f"/company/{cid}", headers=bearer(user_token))
    assert r.status_code == 200, r.text
    d = r.json()["company"]
    assert d["phone"] == phone, "مستخدم مسجَّل لم يرَ هاتف الشركة"
    assert d["contact_locked"] is False


@pytest.mark.needs_db
def test_105_flag_false_shows_contact_to_everyone(client, admin_token, monkeypatch):
    """REQUIRE_LOGIN_FOR_CONTACT=False يجب أن يُظهر الهاتف للزائر أيضاً — كلا الوضعين يعمل."""
    monkeypatch.setattr(main, "REQUIRE_LOGIN_FOR_CONTACT", False)
    cid, phone = _approved_company_with_phone(client, admin_token)
    client.cookies.clear()
    try:
        r = client.get(f"/company/{cid}")
        assert r.status_code == 200, r.text
        d = r.json()["company"]
        assert d["phone"] == phone, "المفتاح False لم يُظهر الهاتف لزائر بلا جلسة"
        assert d["contact_locked"] is False
    finally:
        client.cookies.clear()


# ══════════════════════════════════════════════════════════════
# جولة (ج) — عطلان من اختبار يدوي على الهاتف
# ══════════════════════════════════════════════════════════════

def test_106_my_projects_page_links_to_publish_project(client):
    """
    me/index.html («مشاريعي») كان بلا أي طريق لنشر مشروع — الحالة
    الفارغة تقول «لم تنشر مشروعاً بعد» بلا رابط (اكتُشف باختبار يدوي
    على الهاتف). يجب أن يحمل رابطاً إلى ?post=1 في صفحة السوق
    (تفتح لوحة النشر مباشرة) — مرّتين: زرّاً دائماً في رأس الصفحة،
    وزرّاً آخر داخل الحالة الفارغة نفسها.
    """
    root = Path(__file__).resolve().parent.parent
    src = (root / "public" / "me" / "index.html").read_text(encoding="utf-8")
    occurrences = src.count("../projects.html?post=1")
    assert occurrences >= 2, \
        f"يُتوقَّع رابطان على الأقل إلى نشر مشروع (الزرّ الدائم + الحالة الفارغة) — وُجد {occurrences}"


def test_107_all_public_pages_have_apple_pwa_meta(client):
    """
    آيفون يفتح الموقع المثبَّت داخل سفاري بشريط عنوان بلا هذه
    الوسوم الثلاثة معاً. كل صفحات public/*.html (لا /app ولا /me —
    خارج نطاق هذه الجولة) يجب أن تحملها.
    """
    root = Path(__file__).resolve().parent.parent / "public"
    required = (
        'name="apple-mobile-web-app-capable" content="yes"',
        'name="apple-mobile-web-app-status-bar-style" content="default"',
        'name="apple-mobile-web-app-title" content="بُنيان"',
    )
    missing = {}
    for f in sorted(root.glob("*.html")):
        src = f.read_text(encoding="utf-8")
        gaps = [tag for tag in required if tag not in src]
        if gaps:
            missing[f.name] = gaps
    assert not missing, f"صفحات ينقصها وسوم آيفون: {missing}"


_NO_ACTION_MARKER = "لا فعل ممكن هنا"


def test_108_every_empty_state_in_user_surface_has_an_action(client):
    """
    قاعدة عامة: أي ME.emptyState(...) في public/me/*.html يجب أن يحمل
    actionHTML غير فارغ (المعامل الثالث) — إلا ما كان مُعلَّماً صراحةً
    بتعليق يحوي «لا فعل ممكن هنا» فوق الاستدعاء (حالات انتظار حقيقية
    لا فعل خارجي لها: العروض لم تصل بعد، أو تحديد عنصر من قائمة
    مجاورة ظاهرة أصلاً). حالة فارغة توصّف فعلاً غائب الرابط أجوف.
    """
    root = Path(__file__).resolve().parent.parent / "public" / "me"
    call_re = re.compile(
        r"ME\.emptyState\(\s*'(?:[^'\\]|\\.)*'\s*,\s*'(?:[^'\\]|\\.)*'\s*,\s*'((?:[^'\\]|\\.)*)'",
        re.S,
    )
    violations = []
    for f in sorted(root.glob("*.html")):
        src = f.read_text(encoding="utf-8")
        for m in call_re.finditer(src):
            action = m.group(1)
            if action.strip():
                continue
            preceding = src[max(0, m.start() - 200):m.start()]
            if _NO_ACTION_MARKER in preceding:
                continue
            line_no = src.count("\n", 0, m.start()) + 1
            violations.append(f"{f.name}:{line_no}")
    assert not violations, f"حالات فارغة بلا فعل ولا علامة استثناء: {violations}"

