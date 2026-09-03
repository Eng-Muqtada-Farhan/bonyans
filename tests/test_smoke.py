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


def test_02_company_login(client, company_token):
    """حساب الشركة يدخل ويأخذ رمزاً موحّد الشكل بدور company."""
    payload = _jose_jwt.decode(company_token, main.JWT_SECRET, algorithms=[main.ALGORITHM])
    assert payload["role"] == main.ROLE_COMPANY
    assert payload["uid"]
    # الشركة تُقرأ من profiles لا من الرمز — رمز عمره أسبوع لا يحمل صلاحية
    assert "company_id" not in payload


def test_03_user_login(client, user_token):
    """صاحب المشروع يدخل ويأخذ الرمز نفسه بدور user."""
    payload = _jose_jwt.decode(user_token, main.JWT_SECRET, algorithms=[main.ALGORITHM])
    assert payload["role"] == main.ROLE_USER
    assert payload["uid"]


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
def test_07_09_own_surface_allowed(client, surface, need,
                                   admin_token, company_token, user_token):
    """كل دور يدخل سطحه — ٢٠٠ لا تحويل."""
    tok = {"admin": admin_token, "company": company_token, "user": user_token}[need]
    r = _visit(client, surface, tok)
    assert r.status_code == 200, f"{need} مُنع من سطحه {surface}"


@pytest.mark.parametrize("surface", list(SURFACES))
def test_10_12_no_session_redirects_to_login(client, surface):
    """بلا جلسة: تحويل إلى صفحة الدخول لا ٢٠٠ ولا ٥٠٠."""
    r = _visit(client, surface, None)
    assert r.status_code == 302
    assert r.headers["location"].startswith("/login.html")


@pytest.mark.parametrize("surface,need", [("/app/index.html", "company"),
                                          ("/me/index.html", "user"),
                                          ("/admin/index.html", "admin")])
def test_13_15_wrong_role_goes_to_own_home(client, surface, need,
                                           admin_token, company_token, user_token):
    """دور دخل سطحاً ليس له يُعاد إلى سطحه هو، لا إلى الرئيسية."""
    others = {"admin": admin_token, "company": company_token, "user": user_token}
    del others[need]
    for role, tok in others.items():
        r = _visit(client, surface, tok)
        assert r.status_code == 302, f"{role} لم يُحوَّل عن {surface}"
        assert r.headers["location"] == main._ROLE_HOME[role]


def test_16_guard_does_not_break_admin_api(client, admin_token):
    """
    الحارس يحرس الصفحات لا الواجهات البرمجية.
    بلا هذا الفصل ترجع مسارات /admin/* تحويلاً ٣٠٢ بدل ٤٠١/٢٠٠.
    """
    r = client.get("/admin/project-requests", headers=bearer(admin_token))
    assert r.status_code == 200
    assert client.get("/admin/project-requests").status_code == 401


# ══════════════════════════════════════════════════════════════
# ١٧–١٨ · القوائم: الفلاتر والترقيم
# ══════════════════════════════════════════════════════════════

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


def test_22_profiles_cover_every_user(client):
    """كل مستخدم نشط له ملفّ دور — لا حساب بلا دور بعد الترحيل."""
    with main.SessionLocal() as db:
        orphans = db.execute(text("""
            SELECT count(*) FROM users u
            WHERE u.is_active = true
              AND NOT EXISTS (SELECT 1 FROM profiles p WHERE p.user_id = u.id)
        """)).scalar()
    assert orphans == 0


def test_23_profile_shape_constraint(client):
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


def test_24_require_role_separates_401_from_403(client, user_token):
    """
    بلا رمز ٤٠١، وبرمز صالح لدور آخر ٤٠٣.

    التمييز عملي: الأول يعيد الدخول، والثاني لا يفيده التكرار.
    """
    assert client.get("/company/me").status_code == 401
    assert client.get("/company/me", headers=bearer(user_token)).status_code == 403


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


def test_26_deactivated_user_token_stops_working(client):
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


def test_27_forgot_password_reply_never_varies(client):
    """الردّ نفسه سواء وُجد البريد أم لا — اختلافه يكشف المسجَّلين."""
    _wipe_mail_limits()
    real = client.post("/auth/forgot-password", json={"email": SEED_EMAIL})
    fake = client.post("/auth/forgot-password",
                       json={"email": "definitely-not-registered@nowhere.test"})
    assert real.status_code == fake.status_code == 200
    assert real.json() == fake.json()
    _wipe_mail_limits()


def test_28_forgot_password_rate_limited_same_reply(client):
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


def test_29_reset_token_single_use_and_hashed(client):
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


def test_30_expired_reset_token_rejected(client):
    """رمز منتهٍ يُرفض."""
    _wipe_mail_limits()
    raw, _ = _mk_reset(SEED_EMAIL, minutes=-1)
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 400
    _wipe_mail_limits()


def test_31_reset_rejects_short_password(client):
    """كلمة قصيرة تُرفض ولا تستهلك الرمز."""
    _wipe_mail_limits()
    raw, _ = _mk_reset(SEED_EMAIL)
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": "short"}).status_code == 400
    assert client.post("/auth/reset-password",
                       json={"token": raw, "password": SEED_PASS}).status_code == 200
    _wipe_mail_limits()


def test_32_change_password_requires_current(client, user_token):
    """رمز جلسة مسروق وحده لا يكفي لتغيير كلمة المرور."""
    bad = client.post("/auth/change-password", headers=bearer(user_token),
                      json={"current_password": "wrong-one",
                            "new_password": "NewPass!2026"})
    assert bad.status_code == 401
    ok = client.post("/auth/change-password", headers=bearer(user_token),
                     json={"current_password": SEED_PASS, "new_password": SEED_PASS})
    assert ok.status_code == 200, ok.text


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


def test_34_verify_and_change_tokens_do_not_cross(client):
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

def test_35_register_requires_terms(client):
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


def test_36_register_records_consent(client):
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

def test_38_delete_requires_password(client):
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


def test_39_delete_requires_typed_confirmation(client):
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


def test_40_delete_anonymizes_and_locks_out(client):
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


def test_41_delete_keeps_reviews_anonymized(client):
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


def test_42_delete_anonymizes_projects_not_bids(client):
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


def test_43_purge_only_after_grace(client):
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

def test_44_report_requires_auth_and_valid_input(client, user_token):
    """بلاغ بلا حساب مرفوض، وبنوع أو سبب مجهول مرفوض."""
    assert client.post("/report", json={
        "target_type": "company", "target_id": 1, "reason": "spam"}).status_code == 401
    assert client.post("/report", headers=bearer(user_token), json={
        "target_type": "planet", "target_id": 1, "reason": "spam"}).status_code == 400
    assert client.post("/report", headers=bearer(user_token), json={
        "target_type": "company", "target_id": 1, "reason": "because"}).status_code == 400


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


def test_55_run_purge_job_logs_and_locks(client):
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


def test_56_owner_and_client_fk_are_set_null(client):
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


def test_63_report_target_existence_still_enforced(client, user_token):
    """
    فحص مساعد بعد إعادة صياغة submit_report في هذه الجولة — يبقى
    404 لهدف غير موجود (مصدره test_53، يُعاد هنا كخطّ دفاع ثانٍ
    ضد ارتداد أثناء تعديلات لاحقة على نفس المسار).
    """
    r = client.post("/report", headers=bearer(user_token),
                    json={"target_type": "message", "target_id": 999999999, "reason": "other"})
    assert r.status_code == 404


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

    path = Path(__file__).resolve().parent.parent / "public" / "icons" / "icon-maskable-512.png"
    bg_expected = (13, 17, 23)  # #0d1117 — خلفية icon.svg
    with Image.open(path) as im:
        w, h = im.size
        for corner in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
            assert im.getpixel(corner) == bg_expected, \
                f"زاوية {corner} ليست الخلفية الصِرفة — محتوى تسرّب خارج منطقة الأمان"


# ══════════════════════════════════════════════════════════════
# الجولة د — النشر
# ══════════════════════════════════════════════════════════════

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
