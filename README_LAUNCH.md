# بُنيان — دليل النشر

أصل واحد: **Railway** يخدم main.py (والذي يخدم public/ ذاتياً)، و**Cloudflare**
أمامه لـ DNS وTLS. **Neon** قاعدة البيانات. لا Cloudflare Pages، لا CORS بين
أصلين، لا `window.API_URL` — main.py وpublic/ يعيشان معاً دائماً.

---

## ١ · متطلّبات الخدمة

| المكوّن | التفاصيل |
|---|---|
| Python | 3.12 (متطابق مع التطوير المحلي) |
| القاعدة | Neon Postgres — `DATABASE_URL` (مجمَّع) و`DATABASE_URL_UNPOOLED` (Alembic وpg_dump) |
| البريد | Resend، نطاق `bonyans.com` موثَّق (SPF/DKIM/DMARC) |
| الصور | ImageKit |

## ٢ · إعداد Railway

- `Procfile` في الجذر يحدّد عملية `web` فقط:
  ```
  web: uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
  ⚠️ **لا سطر `release:`** — جُرِّب فعلياً على Railway (بانيه Nixpacks)
  فوصل uvicorn إلى `import main` مباشرة بلا أي محاولة ترحيل تسبقه؛
  Nixpacks لا يقرأ عملية `release` في Procfile كما تفعل Heroku. سطر
  كهذا يبدو أنه يعمل (لا خطأ عند الرفع) بينما هو بلا أثر إطلاقاً —
  أخطر من غيابه الصريح.

  **الترحيلات تُضبط من مكان مختلف تماماً:**
  1. لوحة Railway → اختر خدمة الويب → **Settings → Deploy**.
  2. حقل **Pre-Deploy Command** → اكتب: `alembic upgrade head`
  3. احفظ. من الآن، كل نشر يُشغِّل هذا الأمر أولاً، وفشله وحده
     **يمنع النشر** — لا يصل الكود الجديد لمن يتصفّح الموقع.

  ⛔ **لا تتجاهل هذه الخطوة.** بلاها، الخادم يُقلِع وقاعدته البيانات
  ما زالت على مخطّطها القديم (أو فارغة تماماً في أول نشر) بصمت —
  لا خطأ عند الإقلاع، فقط أعطال `relation does not exist` عند أول
  طلب يلمس جدولاً غير موجود.
- `.railwayignore` يستبعد ملفّات التطوير من صورة النشر (`_test_*.py`،
  `_diag.py`، `tests/`، `venv/`، إلخ) — راجع الملفّ للقائمة الكاملة.
- Railway يضبط `$PORT` تلقائياً — **لا تضبطه أنت**.

## ٣ · متغيّرات البيئة على Railway

تُضبط من لوحة Railway (Settings → Variables) — **ليس في `.env` المحلي،
وليس في أي ملفّ يُرفع لـ Git**. القائمة الكاملة بالأسماء فقط (لا قيم):

```
ENVIRONMENT=production
PUBLIC_BASE_URL=https://bonyans.com
CORS_ORIGINS=https://bonyans.com,https://www.bonyans.com,capacitor://localhost
DATABASE_URL
DATABASE_URL_UNPOOLED
JWT_SECRET
ADMIN_USERNAME
ADMIN_PASSWORD_HASH
IMAGEKIT_PRIVATE_KEY
IMAGEKIT_URL_ENDPOINT
RESEND_API_KEY
MAIL_FROM
SUPPORT_EMAIL
```

**اضبطها قبل أول نشر علني — لا بعده** (القسم ٤): غيابها ليس "تعطيلاً
آمناً"، بل يعني ببساطة أن الموقع علني بلا حماية من لحظة أول نشر:
```
PRELAUNCH_LOCK=1        # غيابه أو أي قيمة غير 1 = لا قفل إطلاقاً
PRELAUNCH_USER
PRELAUNCH_PASS
```

اختياري (آمن الغياب — يُعطّل مساره لا موقعك كلّه):
```
INTERNAL_JOB_TOKEN      # فارغ = /internal/run-purge-job يرفض كل شيء (404)
```

لا تضبط `DISABLE_PURGE_LOOP` في الإنتاج — تلك للاختبارات المحلية وحدها
(`tests/conftest.py` يضبطها هي، لا `.env`).

## ٤ · قفل ما قبل الإطلاق

الموقع لا يجب أن يكون علنياً قبل جاهزيته. اضبط `PRELAUNCH_LOCK=1` مع
`PRELAUNCH_USER`/`PRELAUNCH_PASS` على Railway — HTTP Basic Auth يغطّي كل
مسار عدا `/health`. **لإزالته بعد الإطلاق: احذف `PRELAUNCH_LOCK` من
متغيّرات البيئة (أو اضبطه لأي قيمة غير `1`) — سطر واحد، بلا نشر كود.**

## ٥ · DNS وCloudflare

- `bonyans.com` وWWW يشيران إلى خدمة Railway عبر Cloudflare (proxied — سحابة
  برتقالية) — Cloudflare يتولّى TLS، Railway لا يحتاج شهادة يدوية.
- سجلّات البريد (SPF/DKIM/DMARC) لـResend موثَّقة فعلاً حسب `.env`.

## ٦ · النسخ الاحتياطي

- `backup_db.py` — `pg_dump` حقيقي يستهدف `DATABASE_URL_UNPOOLED`، ينتج
  ملفّاً بصيغة custom format في `backups/`.
- `restore_db.py` — يستعيد ملفّاً إلى قاعدة **مختلفة** يحدّدها `--target`
  صراحةً (يرفض أي رابط يطابق الإنتاج)، ثم يقارن عدد الصفوف جدولاً جدولاً
  بين المصدر والهدف ويطبع تطابقاً صريحاً — لا نسخة "نجحت" بلا هذا التحقّق.
- `.github/workflows/backup.yml` — نسخة يومية مجدولة عبر GitHub Actions
  (لا على قرص Railway المؤقّت). يحتاج سرّاً في إعدادات المستودع:
  `DATABASE_URL_UNPOOLED`. الأرشفة الحالية أثر تشغيل GitHub (٩٠ يوماً) —
  انقلها لاحقاً إلى تخزين دائم (Cloudflare R2 مثلاً).

## ٧ · حلقة تطهير الحسابات تحت Railway

`main.py` يشغّل حلقة داخلية تحاول التطهير كل ٦ ساعات (تفاصيل السلوك تحت
إعادة النشر وتعدّد النسخ موثَّقة في تعليق `_purge_loop` بالكود نفسه).
احتياطاً لو توقّفت الخدمة أو نامت: `POST /internal/run-purge-job` محمي
برأس `X-Internal-Token` يطابق `INTERNAL_JOB_TOKEN` — اربطه بـRailway Cron
Job أو أي مُجدوِل خارجي يستدعيه يومياً.

## ٨ · قاعدة الاختبارات — فرع Neon مستقلّ

`tests/conftest.py` كان يفحص `ENVIRONMENT != production` فقط ويظنّها
حارساً كافياً — لكنها لا تفحص القاعدة الفعلية. منذ صار bonyans.com حيّاً
و`DATABASE_URL` في `.env` المحلي يشير إلى قاعدة الإنتاج نفسها، فبيئة
محلية (`ENVIRONMENT=development`) تعني اختبارات تكتب وتمحو في قاعدة
الموقع الحيّ. الحارس الآن يفحص القاعدة لا اسم البيئة: يرفض العمل إن
غاب `TEST_DATABASE_URL` أو طابق `DATABASE_URL` حرفياً.

**إنشاء الفرع (مرّة واحدة):**

1. لوحة Neon → المشروع → **Branches** → **Create branch**.
2. اسمِه `test` (أو أي اسم واضح)، والفرع الأصل `main` — Neon ينسخ
   البيانات الحالية عند الإنشاء (نسخ فوري copy-on-write، لا يكلّف
   مساحة إضافية حتى تتغيّر الصفوف).
3. من تفاصيل الفرع الجديد، انسخ رابط الاتصال (Pooled connection) وضعه
   في `.env` المحلي:
   ```
   TEST_DATABASE_URL=postgresql://...@ep-xxxxx-pooler.../neondb?sslmode=require&channel_binding=require
   ```
4. رحّل الفرع الجديد إلى أحدث مخطّط (منفصل عن `.env` — لا يُقرأ منه
   افتراضياً؛ `ALEMBIC_DATABASE_URL` يتفوّق على `DATABASE_URL_UNPOOLED`
   وعلى `DATABASE_URL` في `alembic/env.py`):
   ```bash
   ALEMBIC_DATABASE_URL="<TEST_DATABASE_URL نفسها>" alembic upgrade head
   ```

بعدها `pytest tests/` يعمل معزولاً تماماً عن الإنتاج — لا صفّ يكتبه أو
يمحوه يلمس قاعدة bonyans.com الحيّة. فرع Neon مستقلّ لا يُلغي بطء
الشبكة (الاستعلامات لا تزال تعبر إلى فرانكفورت، فالحزمة الكاملة تأخذ
دقائق) لكنه يُلغي الخطر الفعلي: تلوّث بيانات الإنتاج ببيانات اختبار،
أو محوها بالخطأ.

## ٩ · بعد النشر مباشرة

`set_admin_password.py` مُستبعَد من صورة النشر عمداً (`.railwayignore`) —
**لا يمكن تشغيله على Railway نفسها، فالملفّ غير موجود هناك أصلاً.**
شغّله محلياً على جهازك، حيث `.env` المحلي يحمل نفس `DATABASE_URL`
(نفس قاعدة Neon):

```bash
python set_admin_password.py
```

كلمة مرور جديدة ١٦ محرفاً عشوائياً على الأقل — الحالية ظهرت في محادثة
سابقة (بوّابة SCOPE.md). السكربت يكتب `ADMIN_PASSWORD_HASH` الجديدة في
**`.env` المحلي وحده**، لا في Railway. بعدها:

1. افتح `.env` المحلي وانسخ قيمة `ADMIN_PASSWORD_HASH` الجديدة.
2. الصقها يدوياً في متغيّرات بيئة Railway (تستبدل القديمة).
3. لا حاجة لإعادة نشر كود — تغيير متغيّر بيئة يكفي لإعادة تشغيل الخدمة.

## ١٠ · فحوص ما بعد النشر (على الموقع الحيّ)

- `https://bonyans.com/docs` → 404 (`ENVIRONMENT=production` يطفئها)
- ترويسة `Set-Cookie` على تسجيل دخول حقيقي تحمل `Secure`، وHSTS موجودة
- `/.env` و`/main.py` → 404
- `/health` → 200
- استعادة كلمة مرور حقيقية: رابط الرسالة يشير إلى `https://bonyans.com`
  لا `127.0.0.1` — هذا وحده يثبت أن `PUBLIC_BASE_URL` مضبوط صحيحاً
- نشرة ثانية تُظهر شريط "نسخة جديدة متاحة" (عامل الخدمة، الجولة ج)

*بُنيان — صُنع في العراق*
