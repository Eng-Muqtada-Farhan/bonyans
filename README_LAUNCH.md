# بُنيان — دليل النشر والإطلاق

## متطلبات السيرفر

| المكوّن | الإصدار |
|---------|---------|
| Python  | 3.12+   |
| PostgreSQL (Supabase) | 15+ |
| RAM     | 512 MB كحد أدنى |
| نظام التشغيل | Linux (Ubuntu 22.04 LTS موصى به) / Windows |

---

## متغيرات البيئة (.env)

```env
DATABASE_URL=postgresql://user:password@host:5432/db?sslmode=require
JWT_SECRET=your-strong-secret-256-bits
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-admin-password
ADMIN_PASSWORD_HASH=bcrypt-hash-of-admin-password
IMAGEKIT_PRIVATE_KEY=your-imagekit-private-key
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your-id
```

لإنشاء ADMIN_PASSWORD_HASH:
```python
from passlib.context import CryptContext
ctx = CryptContext(schemes=["bcrypt"])
print(ctx.hash("your-admin-password"))
```

---

## خطوات النشر — Linux (Production)

### 1. تثبيت المتطلبات
```bash
git clone https://github.com/your-org/bunyan.git
cd bunyan
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. إعداد البيئة
```bash
cp .env.example .env
nano .env   # أضف جميع المتغيرات
```

### 3. تشغيل Migrations
```bash
alembic upgrade head
```

### 4. تشغيل السيرفر (Production)
```bash
# باستخدام gunicorn مع uvicorn workers
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### 5. Reverse Proxy — Nginx
```nginx
server {
    listen 80;
    server_name bunyan.iq www.bunyan.iq;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
```

### 6. SSL — Let's Encrypt
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d bunyan.iq -d www.bunyan.iq
```

---

## خطوات النشر — Windows (Development)

```powershell
# تشغيل السيرفر
.\venv\Scripts\uvicorn.exe main:app --reload --host 127.0.0.1 --port 8000

# أو في الخلفية
Start-Process .\venv\Scripts\uvicorn.exe -ArgumentList "main:app","--reload"
```

---

## فحص الصحة

بعد الإطلاق، تحقق من:

```bash
# Health check
curl https://bunyan.iq/health
# Expected: {"database":"ok","app":"ok"}

# System status (admin token required)
curl -H "Authorization: YOUR_ADMIN_TOKEN" https://bunyan.iq/admin/system-status
```

---

## النسخ الاحتياطي

### يومياً (cron)
```bash
# أضف لـ crontab
0 2 * * * pg_dump "$DATABASE_URL" -F c -f /backups/bunyan_$(date +\%Y\%m\%d).dump
# احتفظ بآخر 30 يوم
find /backups -name "*.dump" -mtime +30 -delete
```

### قبل كل تحديث
```bash
pg_dump "$DATABASE_URL" -F c -f backups/pre_update_$(date +%Y%m%d_%H%M%S).dump
```

---

## التحديثات

```bash
# 1. نسخة احتياطية
pg_dump "$DATABASE_URL" -F c -f backups/pre_update.dump

# 2. سحب الكود الجديد
git pull origin main

# 3. تثبيت المكتبات الجديدة
pip install -r requirements.txt

# 4. تشغيل migrations
alembic upgrade head

# 5. إعادة تشغيل السيرفر
sudo systemctl restart bunyan
# أو:
kill -HUP $(cat gunicorn.pid)
```

---

## systemd Service (Linux)

```ini
# /etc/systemd/system/bunyan.service
[Unit]
Description=Bunyan Platform
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/bunyan
ExecStart=/home/ubuntu/bunyan/venv/bin/gunicorn main:app \
  -w 4 -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
Restart=always
RestartSec=3
EnvironmentFile=/home/ubuntu/bunyan/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable bunyan
systemctl start bunyan
systemctl status bunyan
```

---

## Checklist قبل الإطلاق

- [ ] جميع متغيرات البيئة مضبوطة في `.env`
- [ ] `GET /health` يعيد `{"database":"ok","app":"ok"}`
- [ ] تسجيل الدخول كـ admin يعمل
- [ ] تسجيل شركة جديدة يعمل
- [ ] رفع الصور عبر ImageKit يعمل
- [ ] SSL مفعّل على النطاق
- [ ] النسخ الاحتياطي التلقائي مضبوط
- [ ] `robots.txt` و `sitemap.xml` متاحان
- [ ] `manifest.json` و service worker مفعّلان (PWA)
- [ ] Rate limiting مختبر
- [ ] `security_audit_log` يسجّل الأحداث

---

## المراحل المكتملة

| Phase | الوصف | الحالة |
|-------|-------|--------|
| 1-4   | الأساسيات، DB، Admin | ✅ |
| 5     | حسابات الشركات | ✅ |
| 6     | الاشتراكات والباقات | ✅ |
| 7     | سوق المشاريع | ✅ |
| 8     | الرسائل، الإشعارات، التقييمات | ✅ |
| 8.1   | تكامل UX العام | ✅ |
| 9     | الأمان والجاهزية | ✅ |
| 10    | UI النهائي، PWA، SEO | ✅ |

---

*بُنيان — صُنع في العراق 🇮🇶*
