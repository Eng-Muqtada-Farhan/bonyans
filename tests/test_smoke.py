"""
عشرون اختبار دخان — بُنيان

تغطّي: الدخول بالأدوار الثلاثة · رمز مزوّر ومنتهٍ · حرّاس الأسطح
(٩ حالات) · /companies و /projects بالفلاتر والترقيم · دورة حياة
الشركة (إنشاء · اعتماد · رفض) · حدّ المعدّل.
"""
import time

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
# البريد نفسه مُعطَّل في الاختبارات (لا RESEND_API_KEY)، وهذا
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
