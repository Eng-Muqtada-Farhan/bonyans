"""
بذر بيانات تجريبية للتطوير المحلي — بُنيان

    python seed_dev.py            # يملأ القاعدة ببيانات اختبارية
    python seed_dev.py --clear    # يحذف كل بيانات البذر دفعةً واحدة
    python seed_dev.py --status   # يعرض ما هو مزروع الآن

كل صف مزروع يحمل علامة تجعله قابلاً للحذف الكامل:
  الشركات   : name يبدأ بـ 'شركة اختبار'
  المشاريع  : contact_name = 'عميل اختبار'
  الحسابات  : email ينتهي بـ '@seed.test'
  التقييمات : client_name يبدأ بـ 'عميل اختبار'

الهواتف صالحة الصيغة (07000000001…07000000012) لا نصّاً مثل
'07XX-TEST': رقم غير صالح يعطّل زر واتساب في صفحة الشركة فلا
يُختبَر أهم مسار تجاري. الأصفار المتتالية تُبقيها واضحة الاصطناع،
والعلامة صارت اسم الشركة لا هاتفها.

الأسماء كلها صريحة الاختبارية («شركة اختبار ١») ولا تشبه شركات
حقيقية — لئلا نكرّر خطأ FALLBACK_DATA حيث ظهرت بيانات مختلَقة
كأنها حقيقية.

⛔ يرفض العمل عندما ENVIRONMENT=production.
"""
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import dotenv_values, load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

# ── علامات البذر ──────────────────────────────────────────────────────────────
SEED_NAME    = "شركة اختبار"          # علامة الشركات — بديل الهاتف
SEED_DOMAIN  = "@seed.test"
SEED_CLIENT  = "عميل اختبار"          # علامة المشاريع والتقييمات
SEED_PROJ_PH = "07000000000"          # هاتف المشاريع — صالح الصيغة
def seed_phone(i: int) -> str:        # 07000000001 … 07000000012
    return "0700000" + f"{i + 1:04d}"

# ── حساب الشركة الذي يسجّل به المستخدم الدخول ────────────────────────────────
LOGIN_EMAIL    = "company@seed.test"
LOGIN_PASSWORD = "SeedTest!2026"

CITIES = ["بغداد", "البصرة", "أربيل", "الموصل", "النجف", "كربلاء"]
SPECS = [
    "مقاولات عامة", "تصميم واستشارات هندسية", "كهرباء وإنارة",
    "أعمال صحية وسباكة", "تشطيبات وأصباغ", "عزل مائي وحراري",
    "حديد وحدادة", "ألمنيوم وواجهات زجاجية", "تبريد وتكييف",
    "طاقة شمسية ومتجددة", "طرق وجسور وبنية تحتية", "نجارة وأعمال خشبية",
]
# ١٢ شركة: ٨ معتمدة، ٢ قيد المراجعة، ٢ مرفوضة
STATUSES = (["approved"] * 8) + (["pending"] * 2) + (["rejected"] * 2)
AR_NUM = ["١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩", "١٠", "١١", "١٢"]


def _host(url: str) -> str:
    """
    مضيف الرابط بلا لاحقة -pooler — فرع Neon نفسه يحمل مضيفين مختلفين
    حرفياً (مجمَّع وغير مجمَّع)، فالمقارنة الحرفية بينهما تُخطئ رغم أنهما
    القاعدة الفعلية نفسها. التطبيع هنا يمنع هذا الثغر بالضبط.
    """
    try:
        h = url.split("@", 1)[1].split("/", 1)[0]
    except (IndexError, AttributeError):
        h = url or ""
    return h.replace("-pooler", "")


def get_engine():
    if os.getenv("ENVIRONMENT", "development") == "production":
        sys.exit("⛔ رُفض: هذا السكربت للتطوير المحلي فقط، و ENVIRONMENT=production.")
    url = os.getenv("DATABASE_URL_UNPOOLED") or os.getenv("DATABASE_URL", "")
    if not url:
        sys.exit("⛔ لا يوجد رابط قاعدة بيانات في .env")

    # حارس إلزامي قبل أي اتصال — هذا سكربت يكتب بيانات فعلية، ولا
    # يجوز أن يلمس الإنتاج تحت أي ظرف. يقرأ DATABASE_URL/
    # DATABASE_URL_UNPOOLED كما هما مكتوبان في ملفّ .env مباشرة (عبر
    # dotenv_values، بلا تأثّر بأي تجاوز بيئي مرّره المستدعي) — هذان
    # مضيفا الإنتاج الحقيقيّان بصرف النظر عمّا تشير إليه متغيّرات
    # البيئة وقت التشغيل. تطابق مضيف الهدف مع أيٍّ منهما يعني أن
    # التشغيل يوشك أن يكتب على الإنتاج فعلياً — يُرفَض فوراً.
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    prod_raw = dotenv_values(env_path)
    prod_hosts = {
        _host(prod_raw.get("DATABASE_URL", "")),
        _host(prod_raw.get("DATABASE_URL_UNPOOLED", "")),
    }
    prod_hosts.discard("")
    target_host = _host(url)
    if target_host and target_host in prod_hosts:
        sys.exit(
            "⛔ رُفض: مضيف الهدف (" + target_host[:12] + "…) يطابق مضيف "
            "الإنتاج (DATABASE_URL/DATABASE_URL_UNPOOLED في .env). هذا "
            "سكربت يكتب بيانات — لن يعمل على قاعدة حقيقية أبداً. مرّر "
            "DATABASE_URL أو DATABASE_URL_UNPOOLED صراحةً بقيمة فرع "
            "اختبار مختلف عند الاستدعاء."
        )
    return create_engine(url)


# ══════════════════════════════════════════════════════════════════════════════
# الحذف
# ══════════════════════════════════════════════════════════════════════════════
def clear(engine) -> None:
    """يحذف كل ما زرعه هذا السكربت — بالترتيب العكسي للتبعيات."""
    with engine.begin() as db:
        p = {"nm": f"{SEED_NAME}%", "dom": f"%{SEED_DOMAIN}", "cl": f"{SEED_CLIENT}%"}

        company_ids = "(SELECT id FROM companies WHERE name LIKE :nm)"
        project_ids = "(SELECT id FROM projects  WHERE contact_name LIKE :cl)"
        user_ids    = "(SELECT id FROM users     WHERE email LIKE :dom)"

        steps = [
            ("chat_messages",  f"DELETE FROM chat_messages WHERE conversation_id IN "
                               f"(SELECT id FROM conversations WHERE company_id IN {company_ids} "
                               f"OR client_user_id IN {user_ids})"),
            ("conversations",  f"DELETE FROM conversations WHERE company_id IN {company_ids} "
                               f"OR client_user_id IN {user_ids}"),
            ("review_replies", f"DELETE FROM review_replies WHERE company_id IN {company_ids} "
                               f"OR review_id IN (SELECT id FROM reviews WHERE client_name LIKE :cl)"),
            ("reviews",        f"DELETE FROM reviews WHERE client_name LIKE :cl "
                               f"OR company_id IN {company_ids}"),
            ("project_bids",   f"DELETE FROM project_bids WHERE company_id IN {company_ids} "
                               f"OR project_id IN {project_ids}"),
            ("notifications",  f"DELETE FROM notifications WHERE company_id IN {company_ids} "
                               f"OR user_id IN {user_ids}"),
            ("whatsapp_clicks", f"DELETE FROM whatsapp_clicks WHERE company_id IN {company_ids}"),
            ("company_views",  f"DELETE FROM company_views WHERE company_id IN {company_ids}"),
            ("company_gallery", f"DELETE FROM company_gallery WHERE company_id IN {company_ids}"),
            ("company_projects", f"DELETE FROM company_projects WHERE company_id IN {company_ids}"),
            ("company_members", f"DELETE FROM company_members WHERE company_id IN {company_ids} "
                                f"OR user_id IN {user_ids}"),
            ("company_subscriptions", f"DELETE FROM company_subscriptions WHERE company_id IN {company_ids}"),
            ("subscription_requests", f"DELETE FROM subscription_requests WHERE company_id IN {company_ids}"),
            ("company_users",  "DELETE FROM company_users WHERE email LIKE :dom"),
            ("projects",       "DELETE FROM projects  WHERE contact_name LIKE :cl"),
            ("companies",      "DELETE FROM companies WHERE name LIKE :nm"),
            ("users",          "DELETE FROM users     WHERE email LIKE :dom"),
        ]
        total = 0
        for label, sql in steps:
            n = db.execute(text(sql), p).rowcount or 0
            if n:
                print(f"  حُذف {n:>3} من {label}")
            total += n
    print(f"\n✅ حُذفت {total} صفاً من بيانات البذر.")


def status(engine) -> None:
    with engine.connect() as db:
        p = {"nm": f"{SEED_NAME}%", "dom": f"%{SEED_DOMAIN}", "cl": f"{SEED_CLIENT}%"}
        rows = [
            ("شركات مزروعة",  "SELECT COUNT(*) FROM companies WHERE name LIKE :nm"),
            ("مشاريع مزروعة", "SELECT COUNT(*) FROM projects WHERE contact_name LIKE :cl"),
            ("حسابات شركات",  "SELECT COUNT(*) FROM company_users WHERE email LIKE :dom"),
            ("مستخدمون",      "SELECT COUNT(*) FROM users WHERE email LIKE :dom"),
            ("تقييمات",       "SELECT COUNT(*) FROM reviews WHERE client_name LIKE :cl"),
        ]
        print("الحالة الحالية:")
        for label, sql in rows:
            print(f"  {label:<16}: {db.execute(text(sql), p).scalar()}")
        print(f"\n  إجمالي الشركات في القاعدة: "
              f"{db.execute(text('SELECT COUNT(*) FROM companies')).scalar()}")


# ══════════════════════════════════════════════════════════════════════════════
# البذر
# ══════════════════════════════════════════════════════════════════════════════
def seed(engine) -> None:
    now = datetime.now(timezone.utc)
    pw_hash = bcrypt.hashpw(LOGIN_PASSWORD.encode(), bcrypt.gensalt()).decode()

    with engine.begin() as db:
        # ── ١٢ شركة ───────────────────────────────────────────────────────────
        company_ids = []
        for i in range(12):
            st = STATUSES[i]
            cid = db.execute(text("""
                INSERT INTO companies
                    (name, city, phone, spec, description, email, website, map_link,
                     rating, verified, status, created_at, verification_status,
                     country, updated_at, image_url)
                VALUES
                    (:name, :city, :phone, :spec, :descr, :email, '', '',
                     :rating, :verified, :status, :created, :vstatus,
                     'IQ', :updated, '')
                RETURNING id
            """), {
                "name":     f"شركة اختبار {AR_NUM[i]}",
                "city":     CITIES[i % len(CITIES)],
                "phone":    seed_phone(i),
                "spec":     SPECS[i % len(SPECS)],
                "descr":    f"شركة بيانات اختبارية رقم {AR_NUM[i]} — للتطوير المحلي فقط، ليست شركة حقيقية.",
                "email":    f"company{i+1}{SEED_DOMAIN}",
                "rating":   round(3.5 + (i % 4) * 0.5, 1),
                "verified": 1 if st == "approved" else 0,
                "status":   st,
                "created":  now - timedelta(days=60 - i * 3),
                "vstatus":  "verified" if st == "approved" else "pending",
                "updated":  now,
            }).scalar()
            company_ids.append(cid)

        approved = [cid for cid, st in zip(company_ids, STATUSES) if st == "approved"]

        # ── حساب الشركة الذي يسجّل به الدخول (الشركة الأولى) ──────────────────
        db.execute(text("""
            INSERT INTO company_users
                (company_id, email, password_hash, provider, is_active, created_at, updated_at)
            VALUES (:cid, :email, :ph, 'local', TRUE, :now, :now)
        """), {"cid": company_ids[0], "email": LOGIN_EMAIL, "ph": pw_hash, "now": now})

        # ── مستخدم عميل (لصاحب المشاريع والمحادثة) ───────────────────────────
        client_uid = db.execute(text("""
            INSERT INTO users
                (email, phone, display_name, provider, password_hash,
                 is_email_verified, is_phone_verified, is_active, created_at, updated_at)
            VALUES (:email, :ph, :name, 'local', :pwh, TRUE, FALSE, TRUE, :now, :now)
            RETURNING id
        """), {
            "email": f"client{SEED_DOMAIN}", "ph": SEED_PROJ_PH,
            "name": "عميل اختبار — صاحب مشاريع", "pwh": pw_hash, "now": now,
        }).scalar()

        # ── ٥ مشاريع ─────────────────────────────────────────────────────────
        proj_titles = [
            ("بناء دار سكني — اختبار",        "مقاولات عامة",          "بغداد",  40_000,  70_000),
            ("تأهيل مبنى إداري — اختبار",     "تشطيبات وأصباغ",        "البصرة", 15_000,  30_000),
            ("تمديدات كهربائية — اختبار",     "كهرباء وإنارة",         "أربيل",   8_000,  14_000),
            ("عزل سطح ومعالجة رطوبة — اختبار", "عزل مائي وحراري",      "الموصل",  5_000,   9_000),
            ("تركيب منظومة شمسية — اختبار",   "طاقة شمسية ومتجددة",    "النجف",  12_000,  20_000),
        ]
        project_ids = []
        for i, (title, cat, city, bmin, bmax) in enumerate(proj_titles):
            pid = db.execute(text("""
                INSERT INTO projects
                    (title, category, city, country, budget_min, budget_max, description,
                     attachments, contact_name, contact_phone, contact_email,
                     status, owner_user_id, created_at, updated_at)
                VALUES
                    (:t, :cat, :city, 'IQ', :bmin, :bmax, :descr,
                     '[]', :cname, :phone, :cemail,
                     :status, :uid, :created, :now)
                RETURNING id
            """), {
                "t": title, "cat": cat, "city": city, "bmin": bmin, "bmax": bmax,
                "descr": f"وصف اختباري للمشروع «{title}» — بيانات تطوير محلي فقط.",
                "cname": SEED_CLIENT, "phone": SEED_PROJ_PH,
                "cemail": f"client{SEED_DOMAIN}",
                "status": "published" if i < 4 else "contracted",
                "uid": client_uid,
                "created": now - timedelta(days=20 - i * 3), "now": now,
            }).scalar()
            project_ids.append(pid)

        # ── عروض على المشاريع ────────────────────────────────────────────────
        bids = 0
        for i, pid in enumerate(project_ids):
            for j in range(3):
                cid = approved[(i + j) % len(approved)]
                db.execute(text("""
                    INSERT INTO project_bids
                        (project_id, company_id, price, duration_days, message,
                         status, created_at, updated_at)
                    VALUES (:pid, :cid, :price, :days, :msg, :st, :created, :now)
                """), {
                    "pid": pid, "cid": cid,
                    "price": 10_000 + (i * 5_000) + (j * 1_500),
                    "days": 30 + j * 15,
                    "msg": f"عرض اختباري رقم {j+1} على المشروع — بيانات تطوير.",
                    "st": "accepted" if (i == 4 and j == 0) else "pending",
                    "created": now - timedelta(days=10 - j), "now": now,
                })
                bids += 1

        # ── تقييمات + ردّ ────────────────────────────────────────────────────
        review_ids = []
        comments = [
            "تجربة اختبارية إيجابية — التزام بالموعد.",
            "جودة تنفيذ جيدة في بيانات الاختبار.",
            "تواصل ممتاز — تقييم اختباري.",
            "سعر مناسب مقارنةً بالعروض — اختبار.",
            "تأخر بسيط في التسليم — تقييم اختباري.",
            "أنصح بالتعامل — بيانات تجريبية.",
        ]
        for i, cid in enumerate(approved[:6]):
            rid = db.execute(text("""
                INSERT INTO reviews (company_id, client_name, rating, comment, status, created_at)
                VALUES (:cid, :cn, :rating, :cm, :st, :created)
                RETURNING id
            """), {
                "cid": cid, "cn": f"{SEED_CLIENT} {AR_NUM[i]}",
                "rating": 3 + (i % 3), "cm": comments[i],
                "st": "approved" if i < 5 else "pending",
                "created": now - timedelta(days=15 - i),
            }).scalar()
            review_ids.append((rid, cid))

        db.execute(text("""
            INSERT INTO review_replies (review_id, company_id, reply, created_at)
            VALUES (:rid, :cid, :reply, :now)
        """), {
            "rid": review_ids[0][0], "cid": review_ids[0][1],
            "reply": "شكراً لتقييمك — ردّ اختباري من الشركة.", "now": now,
        })

        # ── محادثة واحدة برسائل ──────────────────────────────────────────────
        conv_id = db.execute(text("""
            INSERT INTO conversations (project_id, client_user_id, company_id, created_at)
            VALUES (:pid, :uid, :cid, :created) RETURNING id
        """), {
            "pid": project_ids[0], "uid": client_uid, "cid": company_ids[0],
            "created": now - timedelta(days=3),
        }).scalar()

        thread = [
            ("client",  client_uid,      "السلام عليكم، هل يمكنكم تنفيذ المشروع خلال شهرين؟", True),
            ("company", company_ids[0],  "وعليكم السلام، نعم ممكن. نحتاج معاينة الموقع أولاً.", True),
            ("client",  client_uid,      "ممتاز. متى تناسبكم المعاينة؟", True),
            ("company", company_ids[0],  "الأحد القادم صباحاً إن ناسبكم.", False),
        ]
        for k, (stype, sid, msg, read) in enumerate(thread):
            db.execute(text("""
                INSERT INTO chat_messages
                    (conversation_id, sender_type, sender_id, message, is_read, created_at)
                VALUES (:cv, :st, :sid, :msg, :rd, :created)
            """), {
                "cv": conv_id, "st": stype, "sid": sid, "msg": msg, "rd": read,
                "created": now - timedelta(days=3) + timedelta(minutes=k * 20),
            })

        # ── إشعار للشركة ─────────────────────────────────────────────────────
        db.execute(text("""
            INSERT INTO notifications (company_id, type, title, message, is_read, created_at)
            VALUES (:cid, 'new_message', :t, :m, FALSE, :now)
        """), {
            "cid": company_ids[0], "t": "رسالة جديدة",
            "m": "لديك رسالة جديدة من عميل اختبار.", "now": now,
        })

    print(f"""
✅ تمّ البذر.

   {len(company_ids)} شركة  (٨ معتمدة · ٢ قيد المراجعة · ٢ مرفوضة)
   {len(project_ids)} مشاريع · {bids} عرضاً
   {len(review_ids)} تقييمات + ردّ واحد
   محادثة واحدة بـ {len(thread)} رسائل · إشعار واحد

┌─ حساب الشركة للدخول ────────────────────────────┐
   البريد      : {LOGIN_EMAIL}
   كلمة المرور : {LOGIN_PASSWORD}
   الصفحة      : /company_dashboard.html
└──────────────────────────────────────────────────┘

   للحذف الكامل:  python seed_dev.py --clear
""")


CLIENT_LOGIN_EMAIL = f"client{SEED_DOMAIN}"


def ensure_company_login_account(engine) -> None:
    """
    يضمن أن حساب دخول الشركة (company@seed.test) يعمل فعلاً عبر
    /company/login الحالي — ذاك يقرأ users + profiles(role='company')
    + companies مباشرة (main.py:1276)، لا جدول company_users القديم
    الذي كان هذا الملفّ يكتب إليه وحده (main.py لا يقرأه إطلاقاً —
    التعليق "old company_users" في main.py:1941 يؤكّد ذلك). البذر
    الأساسي أعلاه (seed()) كان يكتب فقط إلى company_users، فيبقى
    حساب الدخول عاطلاً 401 على أي فرع Neon فارغ يُبذَر من الصفر.

    مثالي للتكرار: يُشغَّل في كل استدعاء (لا يعتمد على أن seed()
    نفّذت هذه المرّة أم تخطّت لأن الشركات موجودة أصلاً) — يتحقّق قبل
    أي إدراج، ويُصحّح الربط تلقائياً إن أشار إلى شركة غير معتمدة (قد
    يحدث من بيانات بذر سابقة غير متوافقة مع المخطّط الحالي) بدل أن
    يُترك عطباً صامتاً يُكتشَف لاحقاً بفشل غامض في اختبارات الشركة.
    """
    now = datetime.now(timezone.utc)
    with engine.begin() as db:
        approved_cid = db.execute(text(
            "SELECT id FROM companies WHERE name LIKE :nm AND status='approved' "
            "ORDER BY id LIMIT 1"
        ), {"nm": f"{SEED_NAME}%"}).scalar()
        if not approved_cid:
            print("↷ لا شركة معتمدة مزروعة بعد — تخطّي ضمان حساب دخول الشركة "
                  "(شغّل البذر الأساسي أوّلاً).")
            return

        uid = db.execute(text("SELECT id FROM users WHERE email=:e"),
                          {"e": LOGIN_EMAIL}).scalar()
        if not uid:
            pw_hash = bcrypt.hashpw(LOGIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
            uid = db.execute(text("""
                INSERT INTO users
                    (email, phone, display_name, provider, password_hash,
                     is_email_verified, is_phone_verified, is_active, created_at, updated_at)
                VALUES (:email, :ph, :name, 'local', :pwh, TRUE, FALSE, TRUE, :now, :now)
                RETURNING id
            """), {
                "email": LOGIN_EMAIL, "ph": "07000000099",
                "name": "حساب اختبار — دخول شركة", "pwh": pw_hash, "now": now,
            }).scalar()
            print(f"  أُنشئ مستخدم دخول الشركة (id={uid})")
        else:
            print(f"  مستخدم دخول الشركة موجود بالفعل (id={uid}) — لم يُكرَّر")

        prof = db.execute(text(
            "SELECT id, company_id FROM profiles WHERE user_id=:u AND role='company' LIMIT 1"
        ), {"u": uid}).mappings().fetchone()

        if not prof:
            db.execute(text("""
                INSERT INTO profiles (user_id, role, company_id, created_at)
                VALUES (:u, 'company', :c, :now)
            """), {"u": uid, "c": approved_cid, "now": now})
            print(f"  أُنشئ ملف company لدخول الشركة → company_id={approved_cid}")
            return

        if prof["company_id"] == approved_cid:
            print("  ربط دخول الشركة سليم بالفعل — لم يُكرَّر شيء")
            return

        linked_status = db.execute(text("SELECT status FROM companies WHERE id=:c"),
                                    {"c": prof["company_id"]}).scalar()
        if linked_status == "approved":
            print("  ربط دخول الشركة يشير إلى شركة أخرى approved بالفعل — لا تعديل")
            return

        db.execute(text("UPDATE profiles SET company_id=:c WHERE id=:pid"),
                   {"c": approved_cid, "pid": prof["id"]})
        print(f"  صُحِّح ربط دخول الشركة: كان يشير إلى شركة status={linked_status!r} "
              f"→ company_id={approved_cid} (approved)")


def ensure_client_login_account(engine) -> None:
    """
    يضمن أن ملف صاحب المشروع (client@seed.test) يحمل صفّ profiles
    فعلياً — identity_from_claims (main.py:1092-1105) يرفض أي طلب
    مصادَق عليه (401 «invalid token») ما لم يجد صفّ profiles مطابقاً
    لمعرّف المستخدم، بصرف النظر عن صحّة الرمز نفسه. seed() أعلاه كان
    يُنشئ صفّ users للعميل فقط، لا profiles — فيبقى /auth/login ناجحاً
    شكلياً (200) بينما كل طلب لاحق بالرمز نفسه يُرفَض 401 صامتاً.
    الدور 'client' حرفياً كما يكتبه التسجيل الحقيقي (main.py:1917) —
    لا 'user' رغم أن الثابت البرمجي لهذا الدور اسمه ROLE_USER.
    """
    now = datetime.now(timezone.utc)
    with engine.begin() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"),
                          {"e": CLIENT_LOGIN_EMAIL}).scalar()
        if not uid:
            print("↷ لا مستخدم عميل مزروع بعد — تخطّي ضمان ملفّه "
                  "(شغّل البذر الأساسي أوّلاً).")
            return

        has_profile = db.execute(text(
            "SELECT 1 FROM profiles WHERE user_id=:u AND role='client' LIMIT 1"
        ), {"u": uid}).scalar()
        if has_profile:
            print(f"  ملفّ صاحب المشروع موجود بالفعل (user_id={uid}) — لم يُكرَّر")
            return

        db.execute(text("""
            INSERT INTO profiles (user_id, role, created_at)
            VALUES (:u, 'client', :now)
        """), {"u": uid, "now": now})
        print(f"  أُنشئ ملفّ صاحب المشروع (role='client') → user_id={uid}")


def main() -> int:
    ap = argparse.ArgumentParser(description="بذر بيانات تجريبية للتطوير المحلي")
    ap.add_argument("--clear",  action="store_true", help="حذف كل بيانات البذر")
    ap.add_argument("--status", action="store_true", help="عرض ما هو مزروع حالياً")
    args = ap.parse_args()

    engine = get_engine()
    if args.status:
        status(engine)
        return 0
    if args.clear:
        clear(engine)
        return 0

    with engine.connect() as db:
        existing = db.execute(
            text("SELECT COUNT(*) FROM companies WHERE name LIKE :nm"),
            {"nm": f"{SEED_NAME}%"},
        ).scalar()
    if existing:
        print(f"↷ يوجد {existing} شركة مزروعة مسبقاً — تخطّي البذر الأساسي "
              f"(python seed_dev.py --clear لإعادة البذر من الصفر).")
    else:
        seed(engine)

    # يُشغَّلان دوماً، بذراً جديداً كان أم إعادة تشغيل على بيانات قائمة —
    # مثاليان للتكرار بذاتهما (انظر توثيقهما أعلاه).
    ensure_company_login_account(engine)
    ensure_client_login_account(engine)
    return 0


if __name__ == "__main__":
    sys.exit(main())
