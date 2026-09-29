# بُنيان — خطة العمل التنفيذية حتى النشر

> **وثيقة تنفيذ لـ Claude Code.** اقرأ المرحلة المطلوبة فقط، نفّذها بالكامل، تحقّق من
> معايير القبول، ثم اعمل commit. **لا تقفز إلى مرحلة تالية قبل نجاح معايير القبول.**

**المشروع:** منصّة مقاولات عراقية · FastAPI + PostgreSQL + HTML/CSS/JS خام
**المسار:** `F:\بنيان\MD`
**الهدف:** موقع منشور أولاً ← ثم تطبيق أندرويد و iOS عبر Capacitor
**آخر عمل فعلي:** 24 حزيران 2026 (توحيد المصادقة، لم يكتمل)

---

## قواعد ثابتة طوال العمل

1. **اعمل commit بعد كل مهمة مكتملة.** رسالة واضحة بالعربية أو الإنجليزية.
2. **لا تكتب أي مفتاح أو كلمة مرور في الكود.** كلها من `os.getenv()`.
3. **لا تحذف ملفاً قبل أن يكون في Git.** أول commit يحفظ كل شيء.
4. **بعد كل تعديل على `main.py`:** شغّل `python -c "import main"` للتأكد أنه يستورد بلا خطأ.
5. **إن فشل شيء ولم تعرف السبب — توقّف واسأل.** لا تخمّن في قاعدة البيانات أو المصادقة.
6. اللغة في الواجهة عربية RTL. حافظ عليها في كل نص جديد.

---

# المرحلة 0 — الإنقاذ

**المدة:** يوم إلى يومين · **الحالة:** لم تبدأ
**لا تكتب سطر ميزة واحداً قبل إتمام هذه المرحلة كاملة.**

## 0.1 — إنشاء مستودع Git

المشروع ليس مستودع Git إطلاقاً. لا يوجد `.git`. كل تعديل حتى الآن غير قابل للتراجع.

ملفا `.gitignore` و `.env.example` **جاهزان في المشروع مسبقاً** — لا تعد كتابتهما.

```bash
cd /d F:\بنيان\MD
git init
git add -A
git commit -m "snapshot: الحالة كما وُجدت قبل أي إصلاح"
```

**مهم:** `backups/` و `*_backup.*` **غير مستثناة عمداً** في هذا الـ commit — هي التسجيل
الوحيد لتاريخ المشروع. نحفظها في Git أولاً ثم نحذفها من القرص في المهمة 0.6.

### معايير القبول
- [ ] `git log` يُظهر commit واحداً
- [ ] `git ls-files | findstr ".env"` يُظهر `.env.example` **فقط** — إن ظهر `.env` أوقف كل شيء
- [ ] `git status` نظيف

---

## 0.2 — تدوير المفاتيح المحروقة

كل المفاتيح الحالية مكشوفة ويجب اعتبارها محروقة. `ADMIN_PASSWORD=26` — محرفان.

**هذه المهمة يُنفّذها المستخدم بنفسه** (تتطلب دخول لوحات تحكم خارجية).
اطلب منه تأكيد إتمامها قبل المتابعة، وساعده بتوليد القيم:

```bash
# JWT_SECRET جديد
python -c "import secrets; print(secrets.token_hex(32))"

# تجزئة كلمة مرور المدير الجديدة
python -c "import bcrypt; print(bcrypt.hashpw(b'كلمة_المرور_الجديدة', bcrypt.gensalt()).decode())"
```

| المفتاح | المصدر |
|---|---|
| `JWT_SECRET` | الأمر أعلاه |
| `ADMIN_PASSWORD` + `ADMIN_PASSWORD_HASH` | الأمر أعلاه — 16 محرفاً فأكثر |
| `IMAGEKIT_PRIVATE_KEY` | لوحة ImageKit ← Developer Options ← Regenerate |
| `DATABASE_URL` | مشروع قاعدة بيانات جديد (المهمة 0.4) |

### معايير القبول
- [ ] المستخدم أكّد تدوير الأربعة
- [ ] `.env` محدَّث بالقيم الجديدة
- [ ] `grep -r "26\b" _test_*.py` — أزل كلمة المرور القديمة من ملفات الاختبار

---

## 0.3 — إغلاق ثغرة تسريب الملفات ⚠️ الأخطر

**السطر 2916 — آخر سطر في `main.py`:**

```python
app.mount('/', StaticFiles(directory='.', html=True), name='static')
```

`directory='.'` تعني مجلد المشروع كاملاً. Starlette لا يحجب الملفات المخفية، فيصبح
`GET /.env` يُعيد **200** بكل المفاتيح نصّاً صريحاً. وكذلك `/main.py` و `/companies.db`
و `/backups/...` و `/venv/Scripts/python.exe`.

### التنفيذ

**١. أنشئ `public/` وانقل إليها ملفات الواجهة فقط:**

```
public/
├── index.html
├── companies.html
├── projects.html
├── project_details.html
├── company_profile.html
├── company_dashboard.html
├── admin.html
├── bunyan.css
├── bunyan-nav.js
├── auth-core.js
├── auth-ui.js
├── manifest.json
├── service-worker.js
├── robots.txt
├── sitemap.xml
└── icons/
```

استخدم `git mv` لا `move` — يحفظ التاريخ:

```bash
mkdir public
git mv index.html companies.html projects.html project_details.html public/
git mv company_profile.html company_dashboard.html admin.html public/
git mv bunyan.css bunyan-nav.js auth-core.js auth-ui.js public/
git mv manifest.json service-worker.js robots.txt sitemap.xml public/
git mv icons public/
```

**٢. لا تنقل:** `main.py`, `.env`, `requirements.txt`, `db.py`, `models.py`,
`_migrate_*.py`, `_test_*.py`, `backups/`, `venv/`, `node_modules/`, `*.db`, `*.log`

**٣. غيّر السطر 2916:**

```python
app.mount('/', StaticFiles(directory='public', html=True), name='static')
```

**٤. تحقّق من مسارات الواجهة.** الملفات كانت في نفس المجلد، والآن كلها داخل `public/`
فالمسارات النسبية بينها تبقى صحيحة. لكن راجع أي مسار يبدأ بـ `/` أو يشير لملف خارج `public/`.

### معايير القبول
```bash
python -c "import main"                    # لا خطأ
uvicorn main:app --port 8077               # يقلع
curl -i http://127.0.0.1:8077/.env         # يجب: 404
curl -i http://127.0.0.1:8077/main.py      # يجب: 404
curl -i http://127.0.0.1:8077/companies.db # يجب: 404
curl -i http://127.0.0.1:8077/             # يجب: 200 + الصفحة الرئيسية
```
- [ ] الأربعة أعلاه تعطي النتيجة المتوقعة
- [ ] الصفحات تُحمَّل والتصميم سليم و RTL سليم
- [ ] commit: `fix(security): منع تقديم مجلد المشروع — نقل الواجهة إلى public/`

---

## 0.4 — قاعدة بيانات جديدة

مشروع Supabase القديم **محذوف** — الخطأ `FATAL: (ENOTFOUND) tenant/user not found`
يعني أن المشروع نفسه لم يعد قائماً، لا أن كلمة المرور خاطئة. الطبقة المجانية تُحذف بعد الخمول.

**اطلب من المستخدم إنشاء قاعدة جديدة — بخطة مدفوعة هذه المرة** (Supabase Pro أو Neon أو Railway).
المجانية ستُحذف مجدداً.

البيانات القديمة ضاعت. `companies.db` يحتوي 6 صفوف اختبار كلها `rejected` بنفس رقم
هاتف وهمي — لا قيمة لها، لا تحاول ترحيلها.

### إعادة بناء المخطط
المخطط الحالي (~26 جدولاً) مبني عبر دوال ترحيل تعمل عند الإقلاع:
`_run_phase11_migration` (سطر 264)، `_run_sectionB_migration` (297)،
`_run_bfix1_migration` (316)، `_run_bfix3_migration` (326).

أضف `DATABASE_URL` الجديد إلى `.env` ثم شغّل الخادم مرة — الدوال ستبني الجداول تلقائياً.
هذا حل مؤقّت؛ ننقلها إلى Alembic في المهمة 1.3.

**ابحث أولاً في `C:\Users\Lenovo\supabase` و `.supabase`** — قد تحتوي ملفات ترحيل
من Supabase CLI تعطيك المخطط جاهزاً.

### معايير القبول
- [ ] `curl http://127.0.0.1:8077/health` يُعيد **200** لا 503
- [ ] `curl http://127.0.0.1:8077/companies` يُعيد **200** بمصفوفة فارغة `[]`
- [ ] `curl http://127.0.0.1:8077/stats` يُعيد **200**

---

## 0.5 — إعادة بناء البيئة الافتراضية

`venv/` الحالية تشير إلى `C:\Users\313\...` — جهاز آخر. المشروع نُسخ نسخاً.

```bash
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.12.10 مثبَّت على الجهاز وكل الحزم الـ37 تُثبَّت بلا تعارض (تم التحقق).

### معايير القبول
- [ ] `venv\Scripts\python.exe --version` يعمل
- [ ] `pip install -r requirements.txt` ينتهي بـ exit 0

---

## 0.6 — تنظيف

الآن وكل شيء في Git، احذف الضجيج من القرص:

```bash
git rm -r --cached backups/ node_modules/
rmdir /s /q backups node_modules __pycache__
del *_backup.py *_backup.html
del server*.log srv*.log srv_err.txt srv_out.txt test_img.png
del companies.db companies.db.backup_*
```

ثم أضف إلى `.gitignore`:
```
backups/
*_backup.*
```

**احتفظ بـ:** `_migrate_*.py` (مرجع للمخطط حتى ننقلها لـ Alembic)،
`bunyan_audit_report.docx`، `خطة تطوير بنيان.docx`، `README_LAUNCH.md`، `backup_strategy.md`

`db.py` و `models.py` ميّتان — لا يستوردهما `main.py`. احذفهما.

### معايير القبول
- [ ] الخادم ما زال يقلع ويعمل
- [ ] commit: `chore: تنظيف النسخ اليدوية والسجلات — استبدلها Git`

---

# المرحلة 1 — تصليب الخادم

**المدة:** أسبوع · تبدأ بعد نجاح كل معايير المرحلة 0

## 1.1 — CORS و /docs

**الحالي (سطر 55–61):**
```python
app.add_middleware(CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])
```

`allow_origins=["*"]` مع `allow_credentials=True` تركيبة **غير صالحة تقنياً** — المتصفحات
ترفضها — وخطرة: أي موقع يستدعي الـ API نيابةً عن مستخدميك.

**البديل — عدّل السطر 53 وما بعده:**

```python
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PROD = ENVIRONMENT == "production"

app = FastAPI(
    title="بُنيان API",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
if not _origins:
    if IS_PROD:
        raise RuntimeError("CORS_ORIGINS must be set in production.")
    _origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

`CORS_ORIGINS` و `ENVIRONMENT` موجودان في `.env.example` مسبقاً.
لاحقاً عند Capacitor أضف `capacitor://localhost` و `https://localhost`.

---

## 1.2 — ترويسات الأمان

الوسيط الوحيد حالياً هو CORS. لا HSTS ولا CSP ولا X-Frame-Options.

```python
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    if IS_PROD:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

ضعه بعد `add_middleware(CORSMiddleware, ...)` مباشرة.

**تنبيه:** لا تضف CSP صارمة الآن — الواجهة تستخدم inline scripts بكثرة وستنكسر.
أجّلها إلى المرحلة 3 بعد قياس الأثر.

---

## 1.3 — نقل المخطط الكامل إلى Alembic

المخطط لا يقتصر على الدوال الأربع في الإقلاع، بل يشمل أيضاً السكربتات الستة في
المشروع: `_migrate_phase5.py`, `_migrate_phase5b.py`, `_migrate_phase6.py`,
`_migrate_phase7.py`, `_migrate_phase8.py`, `_migrate_phase9.py`، بالإضافة إلى
بناء `categories` و `whatsapp_clicks` داخل `main.py`.

المشكلة الحقيقية: الإقلاع يطبّق DDL على كل بدء، وهو بطيء ويخاطر بالتعارض في
النسخ المتعددة، كما أن `DATABASE_URL` الحالي يعمل عبر Neon Pooler في وضع المعاملات
الذي لا يدعم بعض DDL. الحل الصحيح هو: ترحيل كل المخطط عبر Alembic على اتصال
Neon المباشر (`DATABASE_URL` بدون `-pooler`)، ثم إبقاء الخادم خالياً من DDL عند التشغيل.

```bash
alembic init alembic
```

- اضبط Alembic لقراءة `DATABASE_URL_UNPOOLED` من `.env` (ثم `DATABASE_URL` احتياطاً)
- استخدم اتصال Neon المباشر (بدون `-pooler`) للترحيل فقط، ويبقى المجمَّع للتطبيق
- قم بإنشاء ترحيلات مرقمة تمثل كلّ نصوص SQL الستة + `categories` + `whatsapp_clicks`
- **امحِ كل استدعاءات DDL من الإقلاع** حتى لا يقوم الخادم بإنشاء الجداول أو الأعمدة
- أضف `alembic upgrade head` إلى خطوات النشر قبل بدء الخدمة
- الهدف النهائي: قاعدة فارغة تصل إلى 22 جدولاً بعد تشغيل Alembic فقط

### معايير القبول
- [ ] `alembic upgrade head` يبني قاعدة فارغة كاملة من الصفر إلى 22 جدولاً
- [ ] الخادم يقلع بلا تشغيل أي ترحيل
- [ ] يستخدم Alembic رابط Neon المباشر (بدون `-pooler`)
- [ ] الإقلاع أسرع محسوساً

---

## 1.4 — تحديد المعدّل إلى قاعدة البيانات

`_rate_store` (سطر 94) قاموس Python في ذاكرة العملية. `README_LAUNCH.md` يوصي بـ
`gunicorn -w 4` — أربع عمليات، كل واحدة بعدّادها، فيصبح حد «5 محاولات» فعلياً **20**.
وكل إعادة تشغيل تصفّر العدّادات.

الحل الأبسط بلا خدمة إضافية — جدول PostgreSQL:

```sql
CREATE TABLE rate_limits (
    key         TEXT PRIMARY KEY,
    hits        INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_rate_limits_window ON rate_limits(window_start);
```

استبدل منطق `_rate_store` بقراءة/كتابة على هذا الجدول داخل معاملة واحدة.
أضف مهمة تنظيف تحذف السجلات الأقدم من ساعة.

---

## 1.5 — ترقيم الصفحات ⚠️ إلزامي للجوّال

`/companies` و `/projects` يُعيدان **كل** السجلات دفعةً واحدة. عند 200 شركة بصورها
هذا يقتل التطبيق على شبكة الجوّال.

```python
@app.get("/companies")
def list_companies(
    page: int = 1,
    per_page: int = 20,
    ...
):
    per_page = min(max(per_page, 1), 100)
    offset = (page - 1) * per_page
    # SELECT ... LIMIT :per_page OFFSET :offset
    return {
        "items": rows,
        "page": page,
        "per_page": per_page,
        "total": total_count,
        "pages": ceil(total_count / per_page),
    }
```

**حدّث الواجهة أيضاً:** `public/companies.html` و `public/projects.html` تتوقع مصفوفة
مباشرة، وستنكسر مع الشكل الجديد. أضف زر «تحميل المزيد» أو ترقيماً.

---

## 1.6 — إصلاحات صغيرة

**`datetime.utcnow()` مهجور في Python 3.12** — سبعة مواضع:
الأسطر `66`, `698`, `707`, `1981`, `2268`, `2334`, `2365`

```python
# أضف timezone إلى الاستيراد في السطر 4
from datetime import datetime, timedelta, timezone

# ثم استبدل كل موضع
datetime.utcnow()  →  datetime.now(timezone.utc)
```

**خطأ `wa-click` — السطر 1269.** يُدرج بلا التحقق من وجود الشركة فيُعيد 500 بدل 404.
الخطأ محفوظ في `srv_err.txt`:
```
ForeignKeyViolation: Key (company_id)=(1) is not present in table "companies"
```

```python
@app.post("/company/{company_id}/wa-click")
def track_wa_click(company_id: int, request: Request):
    with SessionLocal() as db:
        exists = db.execute(text(
            "SELECT 1 FROM companies WHERE id = :cid"), {"cid": company_id}).first()
        if not exists:
            raise HTTPException(status_code=404, detail="الشركة غير موجودة")
        ...
```

**راجع نمط معالجة الأخطاء عبر الـ API كله** — هذا مثال على عدم اتّساق عام.

### معايير القبول للمرحلة 1
- [ ] لا تحذير إهمال عند الإقلاع
- [ ] `/companies?page=2&per_page=10` يعمل ويُعيد الشكل الجديد
- [ ] `/docs` يُعيد 404 عند `ENVIRONMENT=production`
- [ ] `curl -I /` يُظهر ترويسات الأمان
- [ ] `wa-click` بمعرّف غير موجود يُعيد 404

---

# المرحلة 2 — ما يمنع المتجران النشر بدونه

**المدة:** أسبوعان · **هذه المرحلة هي المسافة الحقيقية إلى المتاجر، لا الكود.**

## 2.1 — خدمة البريد

لا توجد أي خدمة بريد في المشروع. كل ما يلي يعتمد عليها.

**استخدم Resend** — أبسط خيار، طبقة مجانية 3000 رسالة شهرياً.
`RESEND_API_KEY` و `MAIL_FROM` موجودان في `.env.example`.

اكتب `mailer.py` بدالة واحدة:
```python
def send_mail(to: str, subject: str, html: str) -> bool
```
قوالب الرسائل بالعربية RTL.

## 2.2 — استعادة كلمة المرور

**صفر إشارة في الكود حالياً.** بدونها الرفض من المتجرين شبه مؤكد.

- جدول `password_resets(token_hash, user_id, expires_at, used_at)`
- `POST /auth/forgot-password` — يقبل البريد، يرسل رابطاً، **يُعيد نفس الرد دائماً**
  (لا تكشف إن كان البريد مسجّلاً — تسريب معلومات)
- `POST /auth/reset-password` — يقبل الرمز وكلمة المرور الجديدة
- صلاحية الرمز 30 دقيقة، استخدام واحد فقط
- صفحة `public/reset-password.html`
- **طبّق تحديد المعدّل** على الطلب

## 2.3 — تفعيل البريد الإلكتروني

- عمود `email_verified_at` في جداول المستخدمين
- إرسال رمز التفعيل عند التسجيل
- `GET /auth/verify?token=...`
- امنع الوظائف الحساسة قبل التفعيل (نشر مشروع، تقديم عرض)

## 2.4 — حذف الحساب ⚠️ شرط Apple الصريح 5.1.1(v)

**Apple ترفض أي تطبيق فيه تسجيل حساب بلا حذف حساب داخل التطبيق.** لا استثناء.

- `DELETE /account` — يتطلب مصادقة + تأكيد كلمة المرور
- احذف فعلياً أو أخفِ البيانات نهائياً (anonymize)
- ماذا يحدث لمشاريع الشركة وعروضها ورسائلها؟ **قرّر واكتب السياسة**
- زر واضح في `company_dashboard.html`
- رسالة تأكيد بالبريد

## 2.5 — سياسة الخصوصية والشروط

**إلزامي للمتجرين، ويجب أن تكون على رابط عام ثابت** يعمل حتى قبل تسجيل الدخول.

- `public/privacy.html` و `public/terms.html`
- تغطي: ما تجمعه (بريد، هاتف، IP مجزّأ، صور)، لماذا، أين يُخزَّن (Supabase/ImageKit)،
  مدة الاحتفاظ، حقوق المستخدم، كيفية الحذف، بيانات التواصل
- روابطهما في تذييل كل صفحة
- **راجعهما مع مختص قانوني قبل النشر** — أنا لا أقدّم استشارة قانونية

## 2.6 — الإبلاغ والحجب ⚠️ شرط Apple 1.2

منصّتك فيها محتوى من المستخدمين (ملفات شركات، مشاريع، رسائل، تقييمات).
Apple تشترط آلية إبلاغ وحجب.

- `POST /report` — نوع المحتوى، المعرّف، السبب، ملاحظة
- `POST /block/{user_id}` — يمنع الرسائل
- قسم البلاغات في `admin.html` مع إجراءات
- **التزم بمعالجة البلاغ خلال 24 ساعة** — Apple تسأل عن هذا

## 2.7 — إكمال توحيد المصادقة

**هذا ما كنت تعمل عليه ليلة 24 حزيران وتوقّفت في منتصفه.**

ثلاثة أنظمة متوازية: `admin_token` / `COMPANY_TOKEN` / `project_user_token`
وثلاثة جداول: `company_users` / `users` / `company_members`

أنشأتَ `auth-core.js` (منطق بلا DOM) و `auth-ui.js`، وأعدتَ كتابة `bunyan-nav.js`.
التعليق في الرأس يقول:
```
Load order: auth-core.js → auth-ui.js → bunyan-nav.js
```

**آخر ملفين لمستهما:** `company_dashboard.html` و `project_details.html` عند 03:16.

اقرأ الثلاثة أولاً، افهم الخطة، ثم أكملها على باقي الصفحات. **لا تعد التصميم من الصفر.**

### معايير القبول للمرحلة 2
- [ ] دورة كاملة: تسجيل ← تفعيل بريد ← دخول ← نسيت كلمة المرور ← إعادة تعيين ← دخول
- [ ] حذف الحساب يعمل والبيانات تختفي فعلاً
- [ ] `/privacy` و `/terms` يعملان بلا تسجيل دخول
- [ ] الإبلاغ يصل للوحة الإدارة
- [ ] نظام مصادقة واحد في كل الصفحات

---

# المرحلة 3 — النشر على الإنترنت

**المدة:** 3–5 أيام

## 3.1 — الخادم
**Railway أو Render** — أبسط بكثير من إعداد VPS اليدوي في `README_LAUNCH.md`.
- `gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app`
- كل متغيرات `.env` في لوحة المنصة، **لا في الكود**
- `ENVIRONMENT=production`
- `alembic upgrade head` في أمر البناء

## 3.2 — الواجهة
**Cloudflare Pages أو Netlify** لمجلد `public/`.
يفصل الواجهة عن الخادم ويقتل ثغرة SEC-01 بنيوياً — لا يعود FastAPI يقدّم ملفات إطلاقاً.

الواجهة تستخدم سلسلة فارغة كـ API base. أنشئ `public/config.js`:
```javascript
window.API_URL = "https://api.bunyan.iq";
```
واستبدل كل استدعاءات `fetch` لتستخدمه.

## 3.3 — النطاق والمراقبة
- نطاق + SSL (Cloudflare مجاني)
- `api.` للخادم، الجذر للواجهة
- GitHub Actions للنشر التلقائي عند الدفع إلى `main`
- مراقبة `/health` — UptimeRobot مجاني
- **نسخ احتياطي يومي بـ `pg_dump`** — لا تكرر خسارة قاعدة البيانات

## 3.4 — البذر بمحتوى حقيقي 🔴 الأهم تجارياً

**خطتك الأصلية تقول:** «30-50 شركة مسجلة بملفات كاملة قبل أي إعلان — صور حقيقية
لكل شركة، لا حقول فارغة».

**عندك صفر شركة.** ومراجعو المتاجر يرفضون التطبيقات الفارغة.

هذه ليست مهمة برمجية بل تطوير أعمال، **ويجب أن تبدأ الآن بالتوازي مع المرحلة 1**
لا بعد الانتهاء. أطلق كموقع، اجمع شركات حقيقية، ثم ارفع للمتاجر.

---

# المرحلة 4 — التغليف بـ Capacitor

**المدة:** أسبوع إلى أسبوعين

الواجهة PWA بالفعل: `manifest.json` جاهز، service worker مكتوب، التصميم يستجيب
(اختُبر على 375px — شريط سفلي وتنقّل جوّال يعملان). هذه الحالة المثالية لـ Capacitor.

**لا تعد الكتابة بـ React Native أو Flutter** — 5,700 سطر واجهة و3–5 أشهر بلا ميزة
جديدة واحدة للمستخدم.

```bash
npm init -y
npm i @capacitor/core @capacitor/cli
npx cap init بنيان iq.bunyan.app --web-dir=public
npm i @capacitor/android @capacitor/ios
npx cap add android
npx cap add ios
```

## ⚠️ قاعدة Apple 4.2 — الحد الأدنى من الوظائف

**Apple ترفض التطبيقات التي هي «مجرد موقع داخل WebView».** يجب أن يقدّم التطبيق
قيمة أصلية حقيقية. هذه ليست ميزات كمالية — هي شرط القبول:

| الميزة | الحزمة | المبرر |
|---|---|---|
| إشعارات فورية | `@capacitor/push-notifications` + FCM | رسالة جديدة، عرض على مشروعك، موافقة اشتراك |
| الكاميرا | `@capacitor/camera` | رفع صور المشاريع مباشرة من الموقع |
| المشاركة الأصلية | `@capacitor/share` | مشاركة ملف الشركة |
| تخزين آمن | `@capacitor/preferences` | **الرموز هنا لا في localStorage** |

## معالجات إلزامية
- المنطقة الآمنة (النوتش) — `env(safe-area-inset-*)`
- زر الرجوع في أندرويد
- شاشة البدء والأيقونات التكيّفية
- **أصلح تسجيل service worker** — يفشل حالياً بـ `unknown error when fetching the script`
- أضف `capacitor://localhost` و `https://localhost` إلى `CORS_ORIGINS`

---

# المرحلة 5 — المتاجر

**المدة:** أسبوع تجهيز + 1–3 أسابيع مراجعة

## 🔴 اقرأ هذا قبل كتابة أي كود دفع

بُنيان يبيع اشتراكات رقمية. **قاعدة Apple 3.1.1** تقول: أي محتوى رقمي يُستهلك داخل
التطبيق يجب أن يُشترى عبر المشتريات داخل التطبيق بعمولة 15–30٪.
**دمج ZainCash أو Qi Card داخل التطبيق سيُرفض.**

**المسار الموصى به — استثناء «الأعمال»:** Apple تعفي التطبيقات التي تبيع لمؤسسات
لا لأفراد. عملاؤك شركات مقاولات، وهذا ينطبق عليك.

- الاشتراك يُدار **على الموقع فقط**
- التطبيق يعرض حالة الاشتراك ولا يذكر سعراً ولا زر شراء ولا **رابطاً** — Apple ترفض حتى الرابط
- اكتب سرد المراجعة بعناية موضّحاً أن العملاء شركات

**ملاحظة:** Google أكثر تساهلاً من Apple في B2B. قد تستطيع وضع الدفع في نسخة أندرويد
وتقييد iOS وحدها. تحقّق من سياسة Google الحالية قبل أن تقرّر.

## قائمة التجهيز

| المتطلب | المتجر | الحالة |
|---|---|---|
| حساب مطوّر | Google $25 مرة · Apple $99/سنة | يحتاج تسجيل |
| جهاز macOS أو CI سحابي | Apple فقط | **جهازك ويندوز — استخدم Codemagic أو GitHub Actions بعدّاء macOS** |
| أيقونة 1024×1024 | كلاهما | لديك 192 و 512 فقط |
| لقطات شاشة لكل مقاس | كلاهما | غير موجودة |
| نموذج Data Safety | Google | يحتاج إعداد — **الأخطاء هنا تعني رفضاً** |
| App Privacy | Apple | يحتاج إعداد |
| تصنيف المحتوى | كلاهما | استبيان |
| Target API 35+ · AAB · Play App Signing | Google | يحتاج إعداد |
| **حساب اختبار جاهز للمراجع** | كلاهما | **أكثر سبب للرفض هو تعذّر تسجيل الدخول** |

## التسلسل
1. Internal Testing على Play · TestFlight على Apple
2. أصلح ما يظهر
3. النشر العام

**توقّع رفضاً أو رفضين. هذا طبيعي** — عالج الملاحظة وأعد الرفع.

---

# ما بعد الإطلاق — دَين تقني مؤجَّل

لا تنفّذ شيئاً من هذا قبل الإطلاق:

- تقسيم `main.py` (2,916 سطراً، 81 نقطة نهاية) إلى `routers/`
- اختبارات `pytest` حقيقية بـ `TestClient` — ابدأ بالمصادقة والشركات والعروض.
  الـ14 ملف `_test_*.py` الحالية ليست اختبارات وحدة بل سكربتات تكامل تحتاج خادماً حياً،
  وتكتب مسار `D:/Q/MD` الميت، وتضع كلمة المرور `26` صراحةً
- ربط `companies.spec` بـ `category_id` بدل النص الحر (الفلترة بـ LIKE غير دقيقة)
- ربط `reviews.client_name` بحساب حقيقي — قابل للتزوير حالياً
- استبدال `passlib` بمكتبة `bcrypt` مباشرةً — `passlib` شبه متوقّف عن التطوير
  و `bcrypt` عالق على 4.0.1 بسببه
- إبطال رموز JWT وإضافة refresh token — حالياً 24 ساعة بلا قائمة سوداء،
  وتغيير كلمة المرور لا يُبطل الرمز الحالي
- **غير موثَّق حالياً:** أي نقطة نهاية خاضعة لتحديد المعدّل (rate limiting،
  main.py: `_RATE_LIMIT_SQL`) تفشل مغلقة (503) لا مفتوحة إن تعطّلت قاعدة
  البيانات — بما فيها محاولة تسجيل دخول خاطئة عمداً، التي تتوقّع 401 لا
  503 في الوضع الطبيعي. اكتُشف عرضاً أثناء جولة اختبارات (سبتمبر ٢٠٢٦):
  عطل Neon جعل `test_04_wrong_password_is_401` يفشل لأن الاستجابة كانت
  503 بدل 401 المتوقّعة. هذا سلوك fail-closed سليم أمنياً (لا يفتح
  المصادقة عند عطل القاعدة)، لكنه غير موثَّق فيؤدي بمراقب الإنتاج إلى
  الظنّ أن تسجيل الدخول نفسه معطوب حين يكون العطل في Neon فقط. يحتاج
  توثيقاً (أو صفحة حالة تفرّق بين الحالتين) لا إصلاحاً.

---

## المرجع السريع

| الملف | أسطر | الدور |
|---|---|---|
| `main.py` | 2,916 | كل الخادم — 81 نقطة نهاية |
| `public/company_dashboard.html` | 1,781 | لوحة تحكم الشركة |
| `public/index.html` | 1,317 | الرئيسية + الدليل |
| `public/bunyan.css` | 1,266 | نظام "Royal Glass" + الوضع الليلي |
| `public/admin.html` | 855 | لوحة الإدارة |
| `public/bunyan-nav.js` | 615 | التنقّل الموحّد |
| `public/auth-core.js` / `auth-ui.js` | 130 / 220 | المصادقة الجديدة — غير مكتملة |

**التقنيات:** Python 3.12.10 · FastAPI 0.137.2 · SQLAlchemy 2.0.41 (Core، SQL خام) ·
Pydantic 2.13.4 · psycopg2 2.9.10 · python-jose 3.5.0 · passlib 1.7.4 · bcrypt 4.0.1
(مثبَّت قسراً) · ImageKit SDK 5.7.0 · Alembic 1.16.1 (غير مستخدم)
