import hashlib
import io
import os
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Literal, Optional
from urllib.parse import quote

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from imagekitio import ImageKit

load_dotenv()

# ── Auth ──────────────────────────────────────────────────────────────────────
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
JWT_SECRET     = os.getenv("JWT_SECRET", "")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in .env — server cannot start.")

ALGORITHM   = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env — server cannot start.")

engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

ALLOWED_STATUSES = ("pending", "approved", "rejected")

# ── ImageKit ──────────────────────────────────────────────────────────────────
IMAGEKIT_PRIVATE_KEY  = os.getenv("IMAGEKIT_PRIVATE_KEY", "")
IMAGEKIT_URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT", "")

if not all([IMAGEKIT_PRIVATE_KEY, IMAGEKIT_URL_ENDPOINT]):
    raise RuntimeError("ImageKit keys are not set in .env — server cannot start.")

# ImageKit v5: only private_key in constructor; URL endpoint used to build URLs
imagekit = ImageKit(private_key=IMAGEKIT_PRIVATE_KEY)

# ── App ───────────────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PROD = ENVIRONMENT == "production"

# في الإنتاج تُطفأ صفحات التوثيق — كانت تكشف الـ81 نقطة نهاية بلا مصادقة.
app = FastAPI(
    title="بُنيان API",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
    openapi_url=None if IS_PROD else "/openapi.json",
)

# نطاقات صريحة من متغير البيئة. allow_origins=["*"] مع allow_credentials=True
# تركيبة غير صالحة تقنياً وترفضها المتصفحات، وخطرة في الإنتاج.
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


# ── ترويسات الأمان (المهمة 1.2) ───────────────────────────────────────────────
# ملاحظة: بلا CSP صارمة الآن — الواجهة تعتمد inline scripts بكثرة وستنكسر.
# تُؤجَّل إلى المرحلة 3 بعد قياس الأثر.
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


# ══════════════════════════════════════════════════════════════════════════════
# حارس الأسطح المسوَّرة — على الخادم (DESIGN.md §٤ قاعدة ٣)
# ══════════════════════════════════════════════════════════════════════════════
# «الحارس في الواجهة وحده يتجاوزه سطر في المتصفح.» هذا الحارس يمنع
# تقديم صفحات /app و /admin و /me أصلاً لمن لا يملك جلسة الدور.
#
# الرمز يصل في كعكة bn_sess لأن طلب التنقّل في المتصفح لا يحمل
# ترويسة Authorization. الكعكة ليست بديلاً عن حماية البيانات —
# تلك تبقى في require_company / require_user / require_admin على كل
# نقطة نهاية — بل تمنع الوصول إلى الصفحة نفسها.

SESSION_COOKIE = "bn_sess"

_SURFACE_ROLE = {
    "/app":   "company",
    "/me":    "user",
    "/admin": "admin",
}
_ROLE_HOME = {
    "company": "/app/index.html",
    "user":    "/me/index.html",
    "admin":   "/admin/index.html",
}
_ROLE_LOGIN = {"company": "company", "user": "client"}


def role_from_token(token: str) -> Optional[str]:
    """الدور من رمز موقّع، أو None إن كان غائباً أو تالفاً أو منتهياً."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        return None
    if payload.get("sub") == ADMIN_USERNAME:
        return "admin"
    t = payload.get("type")
    return t if t in ("company", "user") else None


def _is_page_request(request: Request) -> bool:
    """
    هل هذا تنقّل متصفّح إلى صفحة؟

    الحارس يخصّ الصفحات وحدها. نقاط الـ API تحت /admin تصادق
    بترويسة Authorization لا بالكعكة، وتحميها require_admin —
    وتحويلها إلى صفحة دخول يكسرها ويعيد 302 بدل 401.
    """
    dest = request.headers.get("sec-fetch-dest")
    if dest:
        return dest == "document"
    # متصفّحات لا ترسل sec-fetch-dest: اعتمد على Accept
    return "text/html" in request.headers.get("accept", "")


@app.middleware("http")
async def surface_guard(request: Request, call_next):
    path = request.url.path
    if not _is_page_request(request):
        return await call_next(request)
    for prefix, need in _SURFACE_ROLE.items():
        if path == prefix or path.startswith(prefix + "/"):
            role = role_from_token(request.cookies.get(SESSION_COOKIE, ""))
            if role == need:
                break
            if role in _ROLE_HOME:
                # دخل سطحاً ليس له — يُعاد إلى سطحه هو لا إلى الرئيسية
                return RedirectResponse(_ROLE_HOME[role], status_code=302)
            dest = "/login.html"
            if need in _ROLE_LOGIN:
                dest += f"?role={_ROLE_LOGIN[need]}&next={quote(path, safe='/')}"
            return RedirectResponse(dest, status_code=302)
    return await call_next(request)


# ── Auth helpers ──────────────────────────────────────────────────────────────
# أعمار الرموز — مصدر واحد يستعمله الرمز والكعكة معاً حتى لا يفترقا.
ADMIN_TTL   = timedelta(hours=24)
# الشركة وصاحب المشروع — سبعة أيام لا ثلاثين.
# السبب (قرار صاحب المشروع ٣٠ آب ٢٠٢٦): لا إبطال للرموز بعد
# (SCOPE.md سطر ١٢٣)، فالنافذة هي مدة بقاء رمز مسروق صالحاً.
# و.env كان مكشوفاً علناً قبل إصلاح ثغرة الملفات الثابتة، فنفترض
# أن الرموز تسرّبت. الاحتكاك مقصود: يذكّرنا ببناء refresh token
# قبل تطبيق الجوّال، حيث دخولٌ كل أسبوع غير مقبول.
SESSION_TTL = timedelta(days=7)


def set_session_cookie(response, token: str, ttl: timedelta) -> None:
    """
    يضع كعكة الجلسة بخصائصها الكاملة.

    HttpOnly     — لا يقرؤها JavaScript، فسرقة الرمز عبر XSS أصعب.
                   لهذا يضعها الخادم لا الصفحة: كعكة يكتبها JS
                   لا يمكن أن تكون HttpOnly أصلاً.
    SameSite=Lax — لا تُرسَل مع طلبات المواقع الأخرى (حماية CSRF).
    Secure       — في الإنتاج فقط، وإلا تعذّر الاختبار على http محلياً.
    Max-Age      — مطابق لعمر الرمز نفسه، فلا تبقى كعكة بعد انتهائه.
    Path=/       — الحارس يعمل على /app و /me و /admin جميعاً.
    """
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=int(ttl.total_seconds()),
        path="/",
        httponly=True,
        samesite="lax",
        secure=IS_PROD,
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=IS_PROD
    )


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + ADMIN_TTL
    return jwt.encode({"sub": subject, "exp": expire}, JWT_SECRET, algorithm=ALGORITHM)


def verify_admin(request: Request) -> None:
    auth  = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else auth.strip()
    if not token:
        raise HTTPException(status_code=401, detail="unauthorized")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("sub") != ADMIN_USERNAME:
            raise HTTPException(status_code=401, detail="unauthorized")
    except JWTError:
        raise HTTPException(status_code=401, detail="unauthorized")


def require_admin(request: Request) -> None:
    verify_admin(request)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 9 — SECURITY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

import random as _random


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# عبارة ذرّية واحدة: تُدرج أو تزيد العدّاد، وتصفّره إذا انتهت النافذة.
# ON CONFLICT يقفل الصف فلا يوجد سباق بين العمّال.
_RATE_LIMIT_SQL = text("""
    INSERT INTO rate_limits (key, hits, window_start)
    VALUES (:key, 1, now())
    ON CONFLICT (key) DO UPDATE SET
        hits = CASE
            WHEN rate_limits.window_start < now() - make_interval(secs => :window)
            THEN 1
            ELSE rate_limits.hits + 1
        END,
        window_start = CASE
            WHEN rate_limits.window_start < now() - make_interval(secs => :window)
            THEN now()
            ELSE rate_limits.window_start
        END
    RETURNING hits
""")


def _cleanup_rate_limits(db) -> None:
    """حذف النوافذ المنتهية — يعمل عشوائياً بنسبة 1% تجنّباً لجدولة منفصلة."""
    db.execute(text(
        "DELETE FROM rate_limits WHERE window_start < now() - interval '1 hour'"
    ))


def check_rate_limit(key: str, max_calls: int, window_seconds: int) -> bool:
    """
    True إذا كان الطلب مسموحاً، False إذا تجاوز الحد.

    العدّاد في جدول PostgreSQL لا في ذاكرة العملية، فيصمد أمام
    تعدّد العمّال وإعادة التشغيل.

    عند تعذّر الوصول لقاعدة البيانات نمنع الطلب (fail-closed)، لكن
    نرفع 503 لا 429: المستخدم لم يتجاوز أي حد، والخدمة هي المتعطّلة.
    رسالة «حاول بعد 10 دقائق» ستكون مضلّلة هنا.
    """
    try:
        with SessionLocal() as db:
            hits = db.execute(
                _RATE_LIMIT_SQL, {"key": key, "window": window_seconds}
            ).scalar()
            if _random.random() < 0.01:
                _cleanup_rate_limits(db)
            db.commit()
        return hits is not None and hits <= max_calls
    except Exception as e:
        print(f"[rate_limit] تعذّر التحقق من الحد — رُفض الطلب: {e}")
        raise HTTPException(
            status_code=503,
            detail="الخدمة غير متاحة مؤقتاً — تعذّر الوصول لقاعدة البيانات. حاول بعد قليل.",
        )


def write_audit_log(db, actor_type: str, actor_id: str, action: str,
                    request: Request, meta: str = "{}") -> None:
    ip_raw = get_client_ip(request)
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]
    ua = request.headers.get("user-agent", "")[:200]
    try:
        db.execute(text("""
            INSERT INTO security_audit_log(actor_type, actor_id, action, ip_hash, user_agent, meta)
            VALUES(:at, :aid, :action, :ip, :ua, :meta)
        """), {"at": actor_type, "aid": actor_id, "action": action,
               "ip": ip_hash, "ua": ua, "meta": meta})
    except Exception:
        pass  # audit log must never break the main flow


# ── DB helpers ────────────────────────────────────────────────────────────────
def row_to_company_dict(r: dict) -> dict:
    return {
        "id":                    r["id"],
        "name":                  r["name"],
        "city":                  r["city"],
        "phone":                 r["phone"],
        "spec":                  r["spec"],
        "desc":                  r["description"],
        "email":                 r["email"],
        "website":               r["website"],
        "map_link":              r["map_link"],
        "rating":                r["rating"],
        "verified":              bool(r["verified"]),
        "status":                r["status"],
        "created_at":            r["created_at"],
        "image_url":             r.get("image_url") or "",
        "verification_status":   r.get("verification_status") or "pending",
        # Phase 5B — new fields
        "slug":                  r.get("slug") or "",
        "country":               r.get("country") or "IQ",
        "cover_url":             r.get("cover_url") or "",
        "facebook_url":          r.get("facebook_url") or "",
        "instagram_url":         r.get("instagram_url") or "",
        "linkedin_url":          r.get("linkedin_url") or "",
        # الباقة من الاشتراك الفعّال وحده. عمود companies.subscription_plan
        # كان يُكتب ولا يُقرأ في أي قرار — get_company_plan يقرأ من
        # company_subscriptions — فحُذف بترحيل. المفتاح هنا يُملأ من
        # الصلة حين يوفّرها الاستعلام، وإلا فالباقة المجانية.
        "plan":                  r.get("plan_code") or "starter",
        "plan_featured":         bool(r.get("plan_featured")),
        "owner_user_id":         r.get("owner_user_id"),
    }


# ── Pydantic models ───────────────────────────────────────────────────────────
class Company(BaseModel):
    name:      str
    city:      str
    phone:     str
    spec:      str
    desc:      str
    email:     str           = ""
    website:   str           = ""
    map_link:  str           = ""
    rating:    float         = 5
    image_url: Optional[str] = ""


class CompanyStatusUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected"]


# ── Phase 11 — Category Pydantic models ──────────────────────────────────────
class CategoryCreate(BaseModel):
    name_ar:    str
    name_en:    str           = ""
    icon:       str           = "🏗"
    sort_order: int           = 0

class CategoryUpdate(BaseModel):
    name_ar:    Optional[str] = None
    name_en:    Optional[str] = None
    icon:       Optional[str] = None
    is_active:  Optional[bool]= None
    sort_order: Optional[int] = None


class CompanyUpdate(BaseModel):
    name:      Optional[str] = None
    city:      Optional[str] = None
    phone:     Optional[str] = None
    desc:      Optional[str] = None
    email:     Optional[str] = None
    website:   Optional[str] = None
    image_url: Optional[str] = None


# ── ImageKit upload helper ────────────────────────────────────────────────────
def upload_to_imagekit(file_bytes: bytes, filename: str) -> str:
    """رفع ملف إلى ImageKit v5 وإرجاع الرابط الكامل."""
    try:
        import io
        result = imagekit.files.upload(
            file=io.BytesIO(file_bytes),
            file_name=filename,
            folder="/bnyian/companies/",
            use_unique_file_name=True,
            is_private_file=False,
        )
        # v5 returns a Pydantic model — url is at result.url
        url = getattr(result, "url", None)
        if not url:
            # fallback: build URL from url_endpoint + file_path
            file_path = getattr(result, "file_path", None) or getattr(result, "name", filename)
            url = IMAGEKIT_URL_ENDPOINT.rstrip("/") + "/" + file_path.lstrip("/")
        if not url:
            raise ValueError("ImageKit returned no URL")
        return url
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")


# ── Endpoints ─────────────────────────────────────────────────────────────────

# ── Categories ────────────────────────────────────────────────────────────────

@app.get("/categories")
def get_categories():
    """إرجاع التصنيفات النشطة مرتبةً حسب sort_order."""
    with SessionLocal() as db:
        rows = db.execute(text(
            "SELECT id, name_ar, name_en, icon, sort_order FROM categories WHERE is_active=TRUE ORDER BY sort_order ASC"
        )).mappings().fetchall()
    return [dict(r) for r in rows]


@app.post("/categories")
def create_category(payload: CategoryCreate, request: Request):
    require_admin(request)
    with SessionLocal() as db:
        row = db.execute(text("""
            INSERT INTO categories (name_ar, name_en, icon, sort_order, is_active)
            VALUES (:name_ar, :name_en, :icon, :sort_order, TRUE)
            RETURNING id, name_ar, name_en, icon, sort_order, is_active
        """), payload.model_dump()).mappings().fetchone()
        db.commit()
    return dict(row)


@app.put("/categories/{cat_id}")
def update_category(cat_id: int, payload: CategoryUpdate, request: Request):
    require_admin(request)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "no fields to update")
    set_clause = ", ".join(f"{k}=:{k}" for k in updates)
    updates["cat_id"] = cat_id
    with SessionLocal() as db:
        db.execute(text(f"UPDATE categories SET {set_clause} WHERE id=:cat_id"), updates)
        db.commit()
    return {"ok": True}


@app.delete("/categories/{cat_id}")
def delete_category(cat_id: int, request: Request):
    require_admin(request)
    with SessionLocal() as db:
        db.execute(text("UPDATE categories SET is_active=FALSE WHERE id=:id"), {"id": cat_id})
        db.commit()
    return {"ok": True}


@app.post("/upload")
async def upload_image(file: UploadFile = File(...), request: Request = None):
    """رفع صورة إلى ImageKit وإرجاع رابطها."""
    _decode_token(request)  # يرفض أي طلب بدون token صالح
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: jpeg, png, webp, gif"
        )

    max_size = 5 * 1024 * 1024  # 5 MB
    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    url = upload_to_imagekit(file_bytes, file.filename or "upload.jpg")
    return {"url": url}


@app.post("/companies")
def add_company(company: Company, request: Request):
    require_admin(request)
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO companies
                (name, city, phone, spec, description, email, website,
                 map_link, rating, verified, status, created_at, image_url)
            VALUES
                (:name, :city, :phone, :spec, :description, :email, :website,
                 :map_link, :rating, :verified, :status, :created_at, :image_url)
            RETURNING *
        """), {
            "name":        company.name,
            "city":        company.city,
            "phone":       company.phone,
            "spec":        company.spec,
            "description": company.desc,
            "email":       company.email,
            "website":     company.website,
            "map_link":    company.map_link,
            "rating":      company.rating,
            "verified":    0,
            "status":      "pending",
            "created_at":  datetime.now().isoformat(),
            "image_url":   company.image_url or "",
        })
        row = result.mappings().fetchone()
        db.commit()
    return row_to_company_dict(dict(row))


@app.get("/companies")
def get_companies(
    spec: Optional[str] = None,
    city: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    """
    إرجاع الشركات المعتمدة مع الفلترة والترقيم:
    ?spec=X&city=Y&q=search&page=1&per_page=20

    الشكل: {items, page, per_page, total, pages}
    """
    page     = max(page, 1)
    per_page = min(max(per_page, 1), 100)
    offset   = (page - 1) * per_page

    where_clauses = ["c.status = 'approved'"]
    params: dict = {}

    if spec and spec != "all":
        where_clauses.append("LOWER(c.spec) LIKE LOWER(:spec)")
        params["spec"] = f"%{spec}%"
    if city and city != "all":
        where_clauses.append("LOWER(c.city) LIKE LOWER(:city)")
        params["city"] = f"%{city}%"
    if q:
        where_clauses.append("(LOWER(c.name) LIKE LOWER(:q) OR LOWER(c.spec) LIKE LOWER(:q) OR LOWER(c.city) LIKE LOWER(:q))")
        params["q"] = f"%{q}%"

    where_sql = " AND ".join(where_clauses)

    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT c.*,
                   COALESCE(sp.search_priority, 0) AS _priority,
                   sp.code                         AS plan_code,
                   COALESCE(sp.is_featured, false) AS plan_featured,
                   COALESCE(rv.review_count, 0)    AS review_count,
                   rv.review_avg
            FROM companies c
            LEFT JOIN LATERAL (
                SELECT cs.plan_id
                FROM company_subscriptions cs
                WHERE cs.company_id = c.id
                  AND cs.status = 'active'
                  AND (cs.expires_at IS NULL OR cs.expires_at > now())
                ORDER BY cs.created_at DESC
                LIMIT 1
            ) active_sub ON true
            LEFT JOIN subscription_plans sp ON sp.id = active_sub.plan_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*)                        AS review_count,
                       ROUND(AVG(rating)::numeric, 1) AS review_avg
                FROM reviews
                WHERE company_id = c.id AND status = 'approved'
            ) rv ON true
            WHERE {where_sql}
            ORDER BY _priority DESC, c.id DESC
            LIMIT :_per_page OFFSET :_offset
        """), {**params, "_per_page": per_page, "_offset": offset}).mappings().fetchall()

        total = db.execute(
            text(f"SELECT COUNT(*) FROM companies c WHERE {where_sql}"), params
        ).scalar() or 0

    result = []
    for r in rows:
        d = row_to_company_dict(dict(r))
        d["review_count"] = int(r["review_count"] or 0)
        d["review_avg"]   = float(r["review_avg"]) if r["review_avg"] else None
        result.append(d)

    return {
        "items":    result,
        "page":     page,
        "per_page": per_page,
        "total":    int(total),
        "pages":    ceil(total / per_page) if total else 0,
    }


@app.get("/admin/companies")
def get_all_companies(request: Request):
    require_admin(request)
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM companies ORDER BY id DESC")
        ).mappings().fetchall()
    return [row_to_company_dict(dict(r)) for r in rows]


@app.put("/companies/{id}/status")
def update_company_status(id: int, payload: CompanyStatusUpdate, request: Request):
    require_admin(request)

    status = payload.status
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="invalid status")

    verified = 1 if status == "approved" else 0
    vs = "verified" if status == "approved" else ("rejected" if status == "rejected" else "pending")

    with SessionLocal() as db:
        result = db.execute(text("""
            UPDATE companies SET status=:status, verified=:verified, verification_status=:vs WHERE id=:id
        """), {"status": status, "verified": verified, "vs": vs, "id": id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="not found")
        db.commit()

    return {"id": id, "status": status, "verified": bool(verified)}


@app.put("/companies/{id}")
def edit_company(id: int, payload: CompanyUpdate, request: Request):
    require_admin(request)

    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")

    # map desc → description for PostgreSQL
    if "desc" in fields:
        fields["description"] = fields.pop("desc")

    set_clause = ", ".join(f"{k}=:{k}" for k in fields)
    fields["id"] = id

    with SessionLocal() as db:
        result = db.execute(
            text(f"UPDATE companies SET {set_clause} WHERE id=:id RETURNING *"),
            fields,
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="not found")
        db.commit()
    return row_to_company_dict(dict(row))


@app.put("/companies/{id}/approve")
def approve_company(id: int, request: Request):
    return update_company_status(id, CompanyStatusUpdate(status="approved"), request)


@app.put("/companies/{id}/reject")
def reject_company(id: int, request: Request):
    return update_company_status(id, CompanyStatusUpdate(status="rejected"), request)


@app.post("/login")
def login(data: dict, request: Request):
    ip = get_client_ip(request)
    if not check_rate_limit(f"login:{ip}", 5, 600):
        with SessionLocal() as db:
            write_audit_log(db, "ip", ip, "rate_limit:login", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 10 minutes.")
    username = data.get("username", "")
    password = data.get("password", "")
    hashed   = os.getenv("ADMIN_PASSWORD_HASH", "")
    if username != ADMIN_USERNAME or not hashed or not pwd_context.verify(password, hashed):
        with SessionLocal() as db:
            write_audit_log(db, "admin", username, "login_fail", request)
            db.commit()
        raise HTTPException(status_code=401, detail="invalid credentials")
    with SessionLocal() as db:
        write_audit_log(db, "admin", username, "login_success", request)
        db.commit()
    token = create_access_token(username)
    resp = JSONResponse({"token": token})
    set_session_cookie(resp, token, ADMIN_TTL)
    return resp


@app.post("/logout")
def logout():
    """
    يمسح كعكة الجلسة. لازم لأنها HttpOnly فلا تستطيع الصفحة مسحها.

    ⚠️ حدّ معروف: هذا يُنهي الجلسة في هذا المتصفح فقط. الرمز نفسه
    يبقى صالحاً حتى انتهاء صلاحيته — نسخةٌ منه أُخذت قبل الخروج
    تظل تعمل. الإبطال الحقيقي (قائمة سوداء أو رموز قصيرة + refresh)
    مؤجَّل صراحةً في SCOPE.md سطر ١٢٣.
    """
    resp = JSONResponse({"ok": True})
    clear_session_cookie(resp)
    return resp


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5 — COMPANY ACCOUNTS
# ══════════════════════════════════════════════════════════════════════════════

# ── Company Pydantic models ───────────────────────────────────────────────────

class CompanyRegister(BaseModel):
    """Claim an existing approved company. Cannot create a new company."""
    company_id: int
    email:      str
    password:   str


class CompanyLogin(BaseModel):
    email:    str
    password: str


class CompanyMeUpdate(BaseModel):
    name:      Optional[str] = None
    city:      Optional[str] = None
    phone:     Optional[str] = None
    email:     Optional[str] = None
    website:   Optional[str] = None
    map_link:  Optional[str] = None
    desc:      Optional[str] = None
    image_url: Optional[str] = None


class ProjectCreate(BaseModel):
    title:           str
    description:     Optional[str] = None
    location:        Optional[str] = None
    completion_date: Optional[str] = None
    image_url:       Optional[str] = None


class ProjectUpdate(BaseModel):
    title:           Optional[str] = None
    description:     Optional[str] = None
    location:        Optional[str] = None
    completion_date: Optional[str] = None
    image_url:       Optional[str] = None


class GalleryAdd(BaseModel):
    image_url:  str
    title:      Optional[str] = None
    project_id: int
    stage:      Optional[str] = None  # 'before'|'during'|'after'|'other'|None→'other'


# ── Phase 5B: New auth Pydantic models ───────────────────────────────────────

class UserRegister(BaseModel):
    email:        str
    password:     str
    display_name: Optional[str] = None
    phone:        Optional[str] = None


class UserLogin(BaseModel):
    email:    str
    password: str


class CompanyCreate(BaseModel):
    name:      str
    city:      str
    phone:     str
    spec:      str
    desc:      Optional[str] = None
    email:     Optional[str] = None
    website:   Optional[str] = None
    image_url: Optional[str] = None


class CompanyMeUpdateV2(BaseModel):
    name:         Optional[str] = None
    city:         Optional[str] = None
    # التخصص من صفات الشركة نفسها وتضبطه عند التسجيل، فتعديله
    # جزء من «ملف شركتي». كان غائباً عن النموذج فلا سبيل لتغييره.
    spec:         Optional[str] = None
    phone:        Optional[str] = None
    email:        Optional[str] = None
    website:      Optional[str] = None
    map_link:     Optional[str] = None
    desc:         Optional[str] = None
    image_url:    Optional[str] = None
    cover_url:    Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url:Optional[str] = None
    linkedin_url: Optional[str] = None
    slug:         Optional[str] = None


class ProjectRequestCreate(BaseModel):
    customer_name: str
    phone:         str
    email:         Optional[str] = None
    city:          str
    project_type:  str
    description:   Optional[str] = None
    budget:        Optional[str] = None


# ── JWT helpers ───────────────────────────────────────────────────────────────

def create_company_token(company_id: int) -> str:
    expire = datetime.now(timezone.utc) + SESSION_TTL
    return jwt.encode(
        {"sub": f"company:{company_id}", "type": "company", "company_id": company_id, "exp": expire},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


def create_user_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + SESSION_TTL
    return jwt.encode(
        {"sub": f"user:{user_id}", "type": "user", "user_id": user_id, "exp": expire},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


def _decode_token(request: Request) -> dict:
    auth  = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else auth.strip()
    if not token:
        raise HTTPException(status_code=401, detail="auth required")
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="invalid token")


def require_user(request: Request) -> int:
    """Requires a user JWT (type=user). Returns user_id."""
    payload = _decode_token(request)
    if payload.get("type") != "user":
        raise HTTPException(status_code=401, detail="user token required")
    try:
        return int(payload["user_id"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="invalid user token")


def require_company(request: Request) -> int:
    """Accepts both old company JWT and new user JWT. Returns company_id."""
    payload = _decode_token(request)
    token_type = payload.get("type")

    # Old Phase-5 company token
    if token_type == "company":
        try:
            return int(payload["company_id"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=401, detail="invalid company token")

    # New Phase-5B user token — look up their company via company_members
    if token_type == "user":
        try:
            user_id = int(payload["user_id"])
        except (KeyError, ValueError):
            raise HTTPException(status_code=401, detail="invalid user token")
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT company_id FROM company_members WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
                {"uid": user_id}
            ).fetchone()
        if not row:
            raise HTTPException(status_code=403, detail="No company associated with this account")
        return int(row[0])

    raise HTTPException(status_code=401, detail="not a valid company or user token")


# ── DB helpers (Phase 5) ──────────────────────────────────────────────────────

def row_to_project(r: dict) -> dict:
    return {
        "id":              r["id"],
        "company_id":      r["company_id"],
        "title":           r["title"],
        "description":     r.get("description") or "",
        "location":        r.get("location") or "",
        "completion_date": r.get("completion_date") or "",
        "image_url":       r.get("image_url") or "",
        "created_at":      str(r["created_at"]),
    }


def row_to_gallery(r: dict) -> dict:
    return {
        "id":            r["id"],
        "company_id":    r["company_id"],
        "project_id":    r.get("project_id"),
        "project_title": r.get("project_title") or "",
        "image_url":     r["image_url"],
        "title":         r.get("title") or "",
        "stage":         r.get("stage") or "other",
        "created_at":    str(r["created_at"]),
    }


# ── STEP 4: Company auth endpoints ───────────────────────────────────────────

@app.post("/company/register")
def company_register(payload: CompanyRegister):
    """
    Claim an existing approved company.
    - Company must exist AND be approved.
    - No duplicate claims: each company can have only one account.
    - Email must be unique across all company users.
    """
    with SessionLocal() as db:
        # 1. Company must exist and be approved
        company = db.execute(
            text("SELECT id, name, status FROM companies WHERE id=:id"),
            {"id": payload.company_id}
        ).mappings().fetchone()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        if company["status"] != "approved":
            raise HTTPException(
                status_code=403,
                detail="Company must be approved by admin before claiming"
            )

        # 2. Prevent duplicate claim: company_id already has an account
        existing_claim = db.execute(
            text("SELECT id FROM company_users WHERE company_id=:cid"),
            {"cid": payload.company_id}
        ).fetchone()
        if existing_claim:
            raise HTTPException(
                status_code=409,
                detail="This company already has an account"
            )

        # 3. Email must be unique
        existing_email = db.execute(
            text("SELECT id FROM company_users WHERE email=:email"),
            {"email": payload.email.lower()}
        ).fetchone()
        if existing_email:
            raise HTTPException(status_code=409, detail="Email already in use")

        # 4. Create company user
        hashed = pwd_context.hash(payload.password)
        result = db.execute(text("""
            INSERT INTO company_users (company_id, email, password_hash, provider)
            VALUES (:company_id, :email, :password_hash, 'email')
            RETURNING id, company_id, email, is_active, created_at
        """), {
            "company_id":    payload.company_id,
            "email":         payload.email.lower(),
            "password_hash": hashed,
        })
        row = result.mappings().fetchone()
        db.commit()

    return {
        "message":    "Company account created",
        "user_id":    row["id"],
        "company_id": row["company_id"],
        "email":      row["email"],
        "token":      create_company_token(payload.company_id),
    }


@app.post("/company/login")
def company_login(payload: CompanyLogin, request: Request):
    """Login for company users. Returns JWT with type=company."""
    ip = get_client_ip(request)
    if not check_rate_limit(f"login:{ip}", 5, 600):
        with SessionLocal() as db:
            write_audit_log(db, "ip", ip, "rate_limit:company_login", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 10 minutes.")
    with SessionLocal() as db:
        user = db.execute(
            text("""
                SELECT cu.id, cu.company_id, cu.password_hash, cu.is_active,
                       c.status AS company_status
                FROM company_users cu
                JOIN companies c ON c.id = cu.company_id
                WHERE cu.email = :email
            """),
            {"email": payload.email.lower()}
        ).mappings().fetchone()

    if not user or not pwd_context.verify(payload.password, user["password_hash"]):
        with SessionLocal() as db:
            write_audit_log(db, "company", payload.email.lower(), "login_fail", request)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if user["company_status"] == "rejected":
        raise HTTPException(status_code=403, detail="Company application was rejected")

    with SessionLocal() as db:
        write_audit_log(db, "company", str(user["company_id"]), "login_success", request)
        db.commit()
    token = create_company_token(user["company_id"])
    resp = JSONResponse({"token": token, "company_id": user["company_id"]})
    set_session_cookie(resp, token, SESSION_TTL)
    return resp


# ── STEP 4: Company dashboard endpoints ──────────────────────────────────────

@app.get("/company/me")
def get_company_me(request: Request):
    """Get the authenticated company's full profile."""
    company_id = require_company(request)
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT * FROM companies WHERE id=:id"),
            {"id": company_id}
        ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    return row_to_company_dict(dict(row))


@app.put("/company/me")
def update_company_me(payload: CompanyMeUpdateV2, request: Request):
    """Update the authenticated company's own profile."""
    company_id = require_company(request)

    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")
    if "desc" in fields:
        fields["description"] = fields.pop("desc")

    set_clause = ", ".join(f"{k}=:{k}" for k in fields)
    fields["id"] = company_id

    with SessionLocal() as db:
        result = db.execute(
            text(f"UPDATE companies SET {set_clause} WHERE id=:id RETURNING *"),
            fields,
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        db.commit()
    return row_to_company_dict(dict(row))


# ── STEP 4: Company image upload (reuses ImageKit) ───────────────────────────

@app.post("/company/upload")
async def company_upload(file: UploadFile = File(...), request: Request = None):
    """Upload image for company dashboard — same ImageKit, different folder."""
    require_company(request)
    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    try:
        result = imagekit.files.upload(
            file=io.BytesIO(file_bytes),
            file_name=file.filename or "upload.jpg",
            folder="/bnyian/dashboard/",
            use_unique_file_name=True,
            is_private_file=False,
        )
        url = getattr(result, "url", None)
        if not url:
            file_path = getattr(result, "file_path", None) or getattr(result, "name", file.filename)
            url = IMAGEKIT_URL_ENDPOINT.rstrip("/") + "/" + file_path.lstrip("/")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

    return {"url": url}


# ── STEP 6: Projects ──────────────────────────────────────────────────────────

@app.get("/company/projects")
def get_company_projects(request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM company_projects WHERE company_id=:cid ORDER BY created_at DESC"),
            {"cid": company_id}
        ).mappings().fetchall()
    return [row_to_project(dict(r)) for r in rows]


@app.post("/company/projects")
def add_company_project(payload: ProjectCreate, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO company_projects
                (company_id, title, description, location, completion_date, image_url)
            VALUES
                (:company_id, :title, :description, :location, :completion_date, :image_url)
            RETURNING *
        """), {
            "company_id":      company_id,
            "title":           payload.title,
            "description":     payload.description or "",
            "location":        payload.location or "",
            "completion_date": payload.completion_date or "",
            "image_url":       payload.image_url or "",
        })
        row = result.mappings().fetchone()
        db.commit()
    return row_to_project(dict(row))


@app.put("/company/projects/{project_id}")
def update_company_project(project_id: int, payload: ProjectUpdate, request: Request):
    company_id = require_company(request)

    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="no fields to update")
    set_clause = ", ".join(f"{k}=:{k}" for k in fields)
    fields["project_id"] = project_id
    fields["company_id"] = company_id

    with SessionLocal() as db:
        result = db.execute(
            text(f"UPDATE company_projects SET {set_clause} WHERE id=:project_id AND company_id=:company_id RETURNING *"),
            fields,
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        db.commit()
    return row_to_project(dict(row))


@app.delete("/company/projects/{project_id}")
def delete_company_project(project_id: int, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        result = db.execute(
            text("DELETE FROM company_projects WHERE id=:pid AND company_id=:cid"),
            {"pid": project_id, "cid": company_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        db.commit()
    return {"deleted": project_id}


@app.get("/company/projects/{project_id}/gallery")
def get_project_gallery(project_id: int, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT g.*, cp.title AS project_title
                FROM company_gallery g
                LEFT JOIN company_projects cp ON cp.id = g.project_id
                WHERE g.company_id = :cid AND g.project_id = :pid
                ORDER BY g.created_at DESC
            """),
            {"cid": company_id, "pid": project_id}
        ).mappings().fetchall()
    return [row_to_gallery(dict(r)) for r in rows]


# ── STEP 5: Gallery ───────────────────────────────────────────────────────────

@app.get("/company/gallery")
def get_company_gallery(request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT g.*, cp.title AS project_title
                FROM company_gallery g
                LEFT JOIN company_projects cp ON cp.id = g.project_id
                WHERE g.company_id = :cid
                ORDER BY g.created_at DESC
            """),
            {"cid": company_id}
        ).mappings().fetchall()
    return [row_to_gallery(dict(r)) for r in rows]


@app.post("/company/gallery")
def add_gallery_image(payload: GalleryAdd, request: Request):
    company_id = require_company(request)
    # Enforce image limit per subscription plan
    plan  = get_company_plan(company_id)
    usage = get_company_usage(company_id)
    if plan["max_images"] != -1 and usage["images_used"] >= plan["max_images"]:
        raise HTTPException(
            status_code=403,
            detail=f"وصلت للحد الأقصى من الصور ({plan['max_images']} صورة). يرجى ترقية الباقة."
        )
    with SessionLocal() as db:
        # Verify project belongs to this company
        proj = db.execute(
            text("SELECT id FROM company_projects WHERE id=:pid AND company_id=:cid"),
            {"pid": payload.project_id, "cid": company_id}
        ).fetchone()
        if not proj:
            raise HTTPException(status_code=404, detail="المشروع غير موجود")
        valid_stages = {"before", "during", "after", "other"}
        stage = payload.stage if payload.stage in valid_stages else None
        result = db.execute(text("""
            INSERT INTO company_gallery (company_id, project_id, image_url, title, stage)
            VALUES (:company_id, :project_id, :image_url, :title, :stage)
            RETURNING *
        """), {
            "company_id": company_id,
            "project_id": payload.project_id,
            "image_url":  payload.image_url,
            "title":      payload.title or "",
            "stage":      stage,
        })
        row = result.mappings().fetchone()
        db.commit()
    # Return with project_title
    with SessionLocal() as db:
        row2 = db.execute(
            text("""
                SELECT g.*, cp.title AS project_title
                FROM company_gallery g
                LEFT JOIN company_projects cp ON cp.id = g.project_id
                WHERE g.id = :id
            """),
            {"id": row["id"]}
        ).mappings().fetchone()
    return row_to_gallery(dict(row2))


@app.delete("/company/gallery/{image_id}")
def delete_gallery_image(image_id: int, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        result = db.execute(
            text("DELETE FROM company_gallery WHERE id=:iid AND company_id=:cid"),
            {"iid": image_id, "cid": company_id}
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Image not found")
        db.commit()
    return {"deleted": image_id}


# ── PHASE 7: Subscription helpers (must be before wildcard routes) ────────────

def get_company_plan(company_id: int) -> dict:
    """Returns the active plan for a company. Defaults to STARTER if none."""
    with SessionLocal() as db:
        sub = db.execute(text("""
            SELECT cs.*, sp.code, sp.name AS plan_name, sp.monthly_price,
                   sp.max_images, sp.max_project_leads, sp.search_priority,
                   sp.is_verified, sp.is_featured
            FROM company_subscriptions cs
            JOIN subscription_plans sp ON sp.id = cs.plan_id
            WHERE cs.company_id = :cid
              AND cs.status = 'active'
              AND (cs.expires_at IS NULL OR cs.expires_at > now())
            ORDER BY cs.created_at DESC
            LIMIT 1
        """), {"cid": company_id}).mappings().fetchone()

        if sub:
            return dict(sub)

        starter = db.execute(
            text("SELECT * FROM subscription_plans WHERE code='starter'")
        ).mappings().fetchone()

    if starter:
        return {**dict(starter), "status": "free", "is_founder": False,
                "expires_at": None, "plan_name": "STARTER"}
    return {
        "code": "starter", "plan_name": "STARTER", "monthly_price": 0,
        "max_images": 3, "max_project_leads": 1, "search_priority": 0,
        "is_verified": False, "is_featured": False,
        "is_founder": False, "status": "free", "expires_at": None,
    }


def get_company_usage(company_id: int) -> dict:
    with SessionLocal() as db:
        images = db.execute(
            text("SELECT COUNT(*) FROM company_gallery WHERE company_id=:cid"),
            {"cid": company_id}
        ).scalar() or 0
        leads = db.execute(text("""
            SELECT COUNT(*) FROM project_bids
            WHERE company_id=:cid
              AND DATE_TRUNC('month', created_at) = DATE_TRUNC('month', now())
        """), {"cid": company_id}).scalar() or 0
    return {"images_used": int(images), "leads_used_this_month": int(leads)}


def get_founder_count() -> int:
    with SessionLocal() as db:
        return int(db.execute(text(
            "SELECT COUNT(*) FROM company_subscriptions WHERE is_founder=true AND status='active'"
        )).scalar() or 0)


@app.get("/company/subscription")
def company_subscription(request: Request):
    company_id = require_company(request)
    plan  = get_company_plan(company_id)
    usage = get_company_usage(company_id)
    return {
        "plan_code":    plan.get("code", "starter"),
        "plan_name":    plan.get("plan_name") or plan.get("name", "STARTER"),
        "monthly_price": float(plan.get("monthly_price", 0)),
        "status":       plan.get("status", "free"),
        "is_founder":   bool(plan.get("is_founder", False)),
        "expires_at":   str(plan["expires_at"]) if plan.get("expires_at") else None,
        "max_images":   plan.get("max_images", 3),
        "max_project_leads": plan.get("max_project_leads", 1),
        "is_verified":  bool(plan.get("is_verified", False)),
        "is_featured":  bool(plan.get("is_featured", False)),
        "usage":        usage,
        "founder_slots_remaining": max(0, 50 - get_founder_count()),
    }


@app.get("/company/subscription/usage")
def company_subscription_usage(request: Request):
    company_id = require_company(request)
    plan  = get_company_plan(company_id)
    usage = get_company_usage(company_id)
    max_img  = plan.get("max_images", 3)
    max_lead = plan.get("max_project_leads", 1)
    return {
        "images_used":    usage["images_used"],
        "images_max":     max_img,
        "images_unlimited": max_img == -1,
        "leads_used_this_month":  usage["leads_used_this_month"],
        "leads_max":      max_lead,
        "leads_unlimited": max_lead == -1,
    }


# ── Company bids (must be before /company/{company_id} wildcard) ─────────────

@app.get("/company/bids")
def company_bids_route(request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT pb.*, c.name AS company_name, c.image_url AS company_image,
                   p.title AS project_title, p.city AS project_city,
                   p.budget_min, p.budget_max, p.status AS project_status
            FROM project_bids pb
            JOIN companies c ON c.id = pb.company_id
            JOIN projects p ON p.id = pb.project_id
            WHERE pb.company_id = :cid
            ORDER BY pb.created_at DESC
        """), {"cid": company_id}).mappings().fetchall()
    result = []
    for r in rows:
        d = row_to_bid_dict(dict(r))
        d["project_title"]  = r.get("project_title") or ""
        d["project_city"]   = r.get("project_city") or ""
        d["project_status"] = r.get("project_status") or ""
        # الاستعلام يجلبهما أصلاً؛ بلا تمريرهما تضطر شاشة «عروضي»
        # لمغادرة سطح /app لمعرفة نطاق ميزانية المشروع.
        d["budget_min"] = float(r["budget_min"]) if r.get("budget_min") is not None else None
        d["budget_max"] = float(r["budget_max"]) if r.get("budget_max") is not None else None
        result.append(d)
    return result


# ── Section B: WhatsApp click tracking (must be before /company/{company_id}) ─

@app.post("/company/{company_id}/wa-click")
def track_wa_click(company_id: int, request: Request):
    """Public — record a WhatsApp click (no auth required, just IP hash)."""
    ip_raw  = get_client_ip(request)
    ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]
    with SessionLocal() as db:
        # بدون هذا التحقق يفشل الإدراج بـ ForeignKeyViolation فيُعيد 500
        # بدل 404 — كان الخطأ محفوظاً في srv_err.txt.
        exists = db.execute(
            text("SELECT 1 FROM companies WHERE id = :cid"), {"cid": company_id}
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail="الشركة غير موجودة")
        db.execute(text("""
            INSERT INTO whatsapp_clicks (company_id, ip_hash)
            VALUES (:cid, :ip)
        """), {"cid": company_id, "ip": ip_hash})
        db.commit()
    return {"ok": True}


@app.get("/company/{company_id}/wa-stats")
def get_wa_stats(company_id: int, request: Request):
    """Company owner or admin can see WA click stats."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        raise HTTPException(status_code=401, detail="auth required")
    with SessionLocal() as db:
        total = db.execute(text(
            "SELECT COUNT(*) FROM whatsapp_clicks WHERE company_id=:cid"
        ), {"cid": company_id}).scalar() or 0
        last_30 = db.execute(text("""
            SELECT DATE(clicked_at) AS day, COUNT(*) AS clicks
            FROM whatsapp_clicks
            WHERE company_id=:cid AND clicked_at >= NOW() - INTERVAL '30 days'
            GROUP BY day ORDER BY day DESC
        """), {"cid": company_id}).mappings().fetchall()
    return {
        "company_id":    company_id,
        "total_clicks":  int(total),
        "last_30_days":  [{"day": str(r["day"]), "clicks": r["clicks"]} for r in last_30],
    }


# ── PHASE 8 Part D: Activity log (must be before /company/{company_id}) ──────

@app.get("/company/activity")
def company_activity(request: Request):
    cid = require_company(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, action, metadata, created_at
            FROM activity_log
            WHERE company_id = :cid
            ORDER BY created_at DESC
            LIMIT 50
        """), {"cid": cid}).mappings().fetchall()
    return [{"id": r["id"], "action": r["action"],
             "metadata": r["metadata"], "created_at": str(r["created_at"])} for r in rows]


# ── STEP 7: Public company page ───────────────────────────────────────────────

@app.get("/company/{company_id}")
def get_company_public(company_id: int, request: Request):
    """
    Public company profile — no auth required.
    Records a view and returns company + projects + gallery.
    """
    with SessionLocal() as db:
        company = db.execute(
            text("SELECT * FROM companies WHERE id=:id AND status='approved'"),
            {"id": company_id}
        ).mappings().fetchone()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        projects = db.execute(
            text("SELECT * FROM company_projects WHERE company_id=:cid ORDER BY created_at DESC"),
            {"cid": company_id}
        ).mappings().fetchall()

        gallery = db.execute(
            text("""
                SELECT g.*, cp.title AS project_title
                FROM company_gallery g
                LEFT JOIN company_projects cp ON cp.id = g.project_id
                WHERE g.company_id = :cid
                ORDER BY g.created_at DESC
            """),
            {"cid": company_id}
        ).mappings().fetchall()

        # Record view (STEP 9)
        ip_raw = request.client.host if request.client else "unknown"
        ip_hash = hashlib.sha256(ip_raw.encode()).hexdigest()[:16]
        ua = request.headers.get("user-agent", "")[:200]
        db.execute(text("""
            INSERT INTO company_views (company_id, ip_hash, user_agent)
            VALUES (:cid, :ip_hash, :ua)
        """), {"cid": company_id, "ip_hash": ip_hash, "ua": ua})
        db.commit()

    return {
        "company":  row_to_company_dict(dict(company)),
        "projects": [row_to_project(dict(r)) for r in projects],
        "gallery":  [row_to_gallery(dict(r)) for r in gallery],
    }


# ── STEP 8: Admin — update verification_status ───────────────────────────────

@app.put("/admin/companies/{company_id}/verification")
def update_verification_status(company_id: int, request: Request, data: dict):
    require_admin(request)
    vs = data.get("verification_status", "")
    if vs not in ("pending", "verified", "premium"):
        raise HTTPException(status_code=400, detail="Invalid verification_status")
    with SessionLocal() as db:
        result = db.execute(
            text("UPDATE companies SET verification_status=:vs WHERE id=:id RETURNING id, verification_status"),
            {"vs": vs, "id": company_id}
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        db.commit()
    return {"id": row["id"], "verification_status": row["verification_status"]}


# ── STEP 9: Analytics ─────────────────────────────────────────────────────────

@app.get("/company/{company_id}/views")
def get_company_views(company_id: int, request: Request):
    """View count — accessible to the company owner or admin."""
    payload = _decode_token(request)
    token_type = payload.get("type")

    if payload.get("sub") == ADMIN_USERNAME:
        pass  # admin: unrestricted
    elif token_type == "company":
        if int(payload.get("company_id", 0)) != company_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    elif token_type == "user":
        uid = int(payload.get("user_id", 0))
        with SessionLocal() as db:
            cid = db.execute(
                text("SELECT company_id FROM company_members WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
                {"uid": uid}
            ).scalar()
        if cid != company_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    with SessionLocal() as db:
        count = db.execute(
            text("SELECT COUNT(*) FROM company_views WHERE company_id=:cid"),
            {"cid": company_id}
        ).scalar()
        recent = db.execute(
            text("""
                SELECT DATE(viewed_at) AS day, COUNT(*) AS views
                FROM company_views
                WHERE company_id=:cid
                  AND viewed_at >= NOW() - INTERVAL '30 days'
                GROUP BY day
                ORDER BY day DESC
            """),
            {"cid": company_id}
        ).mappings().fetchall()
    return {
        "company_id":  company_id,
        "total_views": count,
        "last_30_days": [{"day": str(r["day"]), "views": r["views"]} for r in recent],
    }


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 5B — NEW AUTH SYSTEM (users + company_members)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register")
def auth_register(payload: UserRegister):
    """
    Create a new user account.
    Returns a user JWT. The user can then call POST /company/create to set up
    their company profile (status=pending, awaiting admin approval).
    OAuth-ready: password_hash is nullable for future Google/Apple/Facebook login.
    """
    email = payload.email.strip().lower()
    if not email or not payload.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    hashed = pwd_context.hash(payload.password)
    with SessionLocal() as db:
        existing = db.execute(
            text("SELECT id FROM users WHERE email=:email"),
            {"email": email}
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        result = db.execute(text("""
            INSERT INTO users (email, display_name, phone, password_hash, provider)
            VALUES (:email, :display_name, :phone, :password_hash, 'email')
            RETURNING id, email, display_name, created_at
        """), {
            "email":        email,
            "display_name": payload.display_name or "",
            "phone":        payload.phone or None,
            "password_hash": hashed,
        })
        row = result.mappings().fetchone()
        db.commit()

    return {
        "message":      "Account created",
        "user_id":      row["id"],
        "email":        row["email"],
        "display_name": row["display_name"],
        "token":        create_user_token(row["id"]),
    }


@app.post("/auth/login")
def auth_login(payload: UserLogin, request: Request):
    """
    Login with email + password.
    Returns a user JWT and the associated company_id (null if no company yet).
    Accepts users from both old company_users and new users table.
    """
    ip = get_client_ip(request)
    if not check_rate_limit(f"login:{ip}", 5, 600):
        with SessionLocal() as db:
            write_audit_log(db, "ip", ip, "rate_limit:auth_login", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 10 minutes.")
    email = payload.email.strip().lower()
    with SessionLocal() as db:
        user = db.execute(
            text("SELECT * FROM users WHERE email=:email AND is_active=true"),
            {"email": email}
        ).mappings().fetchone()

    if not user or not user["password_hash"] or not pwd_context.verify(payload.password, user["password_hash"]):
        with SessionLocal() as db:
            write_audit_log(db, "user", email, "login_fail", request)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = user["id"]
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT company_id FROM company_members WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
            {"uid": user_id}
        ).fetchone()
    company_id = int(row[0]) if row else None

    with SessionLocal() as db:
        write_audit_log(db, "user", str(user_id), "login_success", request)
        db.commit()
    token = create_user_token(user_id)
    resp = JSONResponse({
        "token":      token,
        "user_id":    user_id,
        "company_id": company_id,
    })
    set_session_cookie(resp, token, SESSION_TTL)
    return resp


@app.post("/company/create")
def company_create(payload: CompanyCreate, request: Request):
    """
    Create a new company profile linked to the authenticated user.
    Company starts as status='pending' — admin must approve before it appears publicly.
    One user can own one company.
    """
    user_id = require_user(request)

    with SessionLocal() as db:
        existing = db.execute(
            text("SELECT company_id FROM company_members WHERE user_id=:uid AND role='owner'"),
            {"uid": user_id}
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="You already have a registered company")

        result = db.execute(text("""
            INSERT INTO companies
                (name, city, phone, spec, description, email, website,
                 rating, verified, status, created_at, image_url,
                 owner_user_id, slug, country)
            VALUES
                (:name, :city, :phone, :spec, :description, :email, :website,
                 5.0, 0, 'pending', now(), :image_url,
                 :owner_user_id, :slug, 'IQ')
            RETURNING *
        """), {
            "name":         payload.name.strip(),
            "city":         payload.city.strip(),
            "phone":        payload.phone.strip(),
            "spec":         payload.spec.strip(),
            "description":  payload.desc or "",
            "email":        payload.email or "",
            "website":      payload.website or "",
            "image_url":    payload.image_url or "",
            "owner_user_id": user_id,
            "slug":         None,  # will set after getting id
        })
        row = result.mappings().fetchone()
        company_id = row["id"]

        # Set slug now that we have the id
        db.execute(
            text("UPDATE companies SET slug='company-' || id::text WHERE id=:id"),
            {"id": company_id}
        )

        # Add to company_members as owner
        db.execute(text("""
            INSERT INTO company_members (company_id, user_id, role)
            VALUES (:company_id, :user_id, 'owner')
            ON CONFLICT (company_id, user_id) DO NOTHING
        """), {"company_id": company_id, "user_id": user_id})

        db.commit()

    return {
        "message":    "Company registered — pending admin approval",
        "company_id": company_id,
        "status":     "pending",
        "token":      create_user_token(user_id),
    }


@app.get("/auth/me")
def auth_me(request: Request):
    """Get authenticated user's info + company_id."""
    user_id = require_user(request)
    with SessionLocal() as db:
        user = db.execute(
            text("SELECT id, email, display_name, avatar_url, phone, provider, is_active, created_at FROM users WHERE id=:id"),
            {"id": user_id}
        ).mappings().fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        row = db.execute(
            text("SELECT company_id FROM company_members WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
            {"uid": user_id}
        ).fetchone()
    return {
        "user_id":      user["id"],
        "email":        user["email"],
        "display_name": user["display_name"] or "",
        "avatar_url":   user["avatar_url"] or "",
        "phone":        user["phone"] or "",
        "provider":     user["provider"],
        "is_active":    user["is_active"],
        "created_at":   str(user["created_at"]),
        "company_id":   int(row[0]) if row else None,
    }


# ── Project Requests (public submission, future bidding system) ───────────────

@app.post("/project-requests")
def submit_project_request(payload: ProjectRequestCreate):
    """Public endpoint — anyone can submit a project request (no auth required)."""
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO project_requests
                (customer_name, phone, email, city, project_type, description, budget, status)
            VALUES
                (:customer_name, :phone, :email, :city, :project_type, :description, :budget, 'open')
            RETURNING id, created_at
        """), {
            "customer_name": payload.customer_name.strip(),
            "phone":         payload.phone.strip(),
            "email":         payload.email or None,
            "city":          payload.city.strip(),
            "project_type":  payload.project_type.strip(),
            "description":   payload.description or None,
            "budget":        payload.budget or None,
        })
        row = result.mappings().fetchone()
        db.commit()
    return {"message": "Request submitted", "id": row["id"]}


@app.get("/admin/project-requests")
def get_project_requests(request: Request):
    """Admin: list all project requests."""
    require_admin(request)
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM project_requests ORDER BY created_at DESC")
        ).mappings().fetchall()
    return [dict(r) for r in rows]


# ── PROJECT MARKETPLACE (Phase 6) ────────────────────────────────────────────

class MarketProjectCreate(BaseModel):
    title: str
    category: str
    city: str
    country: str = "IQ"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    description: Optional[str] = None
    contact_name: str
    contact_phone: str
    contact_email: Optional[str] = None

class ProjectBidCreate(BaseModel):
    price: float
    duration_days: Optional[int] = None
    message: Optional[str] = None

class ProjectBidUpdate(BaseModel):
    price: Optional[float] = None
    duration_days: Optional[int] = None
    message: Optional[str] = None


def row_to_project_dict(r: dict) -> dict:
    return {
        "id":           r["id"],
        "title":        r["title"],
        "category":     r["category"],
        "city":         r["city"],
        "country":      r.get("country") or "IQ",
        "budget_min":   float(r["budget_min"]) if r.get("budget_min") is not None else None,
        "budget_max":   float(r["budget_max"]) if r.get("budget_max") is not None else None,
        "description":  r.get("description") or "",
        "contact_name":  r.get("contact_name") or "",
        "contact_phone": r.get("contact_phone") or "",
        "contact_email": r.get("contact_email") or "",
        "status":        r["status"],
        "owner_user_id": r.get("owner_user_id"),
        "created_at":    str(r["created_at"]),
        "bids_count":    int(r["bids_count"]) if r.get("bids_count") is not None else 0,
    }


def row_to_bid_dict(r: dict) -> dict:
    return {
        "id":           r["id"],
        "project_id":   r["project_id"],
        "company_id":   r["company_id"],
        "company_name": r.get("company_name") or "",
        "company_image": r.get("company_image") or "",
        "price":        float(r["price"]),
        "duration_days": r.get("duration_days"),
        "message":      r.get("message") or "",
        "status":       r["status"],
        "created_at":   str(r["created_at"]),
    }


@app.post("/projects")
def create_project(payload: MarketProjectCreate, request: Request):
    user_id = require_user(request)
    # B5: Block company members — they cannot create client projects
    with SessionLocal() as db:
        is_company_member = db.execute(
            text("SELECT 1 FROM company_members WHERE user_id=:uid LIMIT 1"),
            {"uid": user_id}
        ).fetchone()
    if is_company_member:
        raise HTTPException(status_code=403, detail="لا يمكن لحسابات الشركات إنشاء طلبات مشاريع كعميل")
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO projects
                (title, category, city, country, budget_min, budget_max,
                 description, contact_name, contact_phone, contact_email,
                 status, owner_user_id)
            VALUES
                (:title, :category, :city, :country, :budget_min, :budget_max,
                 :description, :contact_name, :contact_phone, :contact_email,
                 'published', :owner_user_id)
            RETURNING *
        """), {
            "title":        payload.title.strip(),
            "category":     payload.category.strip(),
            "city":         payload.city.strip(),
            "country":      payload.country,
            "budget_min":   payload.budget_min,
            "budget_max":   payload.budget_max,
            "description":  payload.description or "",
            "contact_name":  payload.contact_name.strip(),
            "contact_phone": payload.contact_phone.strip(),
            "contact_email": payload.contact_email or "",
            "owner_user_id": user_id,
        })
        row = result.mappings().fetchone()
        db.commit()

    project_row = dict(row)

    # Notify approved companies that match city OR specialization
    try:
        with SessionLocal() as db:
            matches = db.execute(text("""
                SELECT id FROM companies
                WHERE status = 'approved'
                  AND (city = :city OR spec ILIKE :cat_pattern)
            """), {
                "city":        payload.city.strip(),
                "cat_pattern": f"%{payload.category.strip()}%",
            }).fetchall()
            for m in matches:
                create_notification(
                    db,
                    company_id=m[0],
                    ntype="new_project",
                    title=f"مشروع جديد في {payload.city}",
                    message=f"{payload.title} — {payload.category}",
                )
            db.commit()
    except Exception:
        pass  # Notifications are non-critical — never fail the project creation

    return {**row_to_project_dict(project_row), "bids_count": 0}


@app.get("/projects")
def list_projects(
    city: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
):
    """الشكل: {items, page, per_page, total, pages}"""
    page     = max(page, 1)
    per_page = min(max(per_page, 1), 100)
    offset   = (page - 1) * per_page

    where_parts = ["p.status = 'published'"]
    params: dict = {}
    if status:
        where_parts = [f"p.status = :status"]
        params["status"] = status
    if city:
        where_parts.append("p.city = :city")
        params["city"] = city
    if category:
        where_parts.append("p.category = :category")
        params["category"] = category
    where = " AND ".join(where_parts)
    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_bids pb WHERE pb.project_id = p.id) AS bids_count
            FROM projects p
            WHERE {where}
            ORDER BY p.created_at DESC
            LIMIT :_per_page OFFSET :_offset
        """), {**params, "_per_page": per_page, "_offset": offset}).mappings().fetchall()

        total = db.execute(
            text(f"SELECT COUNT(*) FROM projects p WHERE {where}"), params
        ).scalar() or 0

    return {
        # القائمة العامّة لا تحمل بيانات تواصل أصلاً: تسريبها هنا
        # أسوأ من تسريبها في صفحة واحدة — نداء واحد يجمع أرقام
        # كل أصحاب المشاريع. من يحقّ له يقرؤها من /projects/{id}.
        "items":    [_strip_contact(row_to_project_dict(dict(r))) for r in rows],
        "page":     page,
        "per_page": per_page,
        "total":    int(total),
        "pages":    ceil(total / per_page) if total else 0,
    }


_CONTACT_FIELDS = ("contact_name", "contact_phone", "contact_email")


def _strip_contact(d: dict) -> dict:
    """يحذف حقول التواصل من الاستجابة كلياً — لا يُفرّغها."""
    for f in _CONTACT_FIELDS:
        d.pop(f, None)
    return d


def _may_see_project_contact(request: Request, project: dict) -> bool:
    """
    من يحقّ له رؤية بيانات تواصل صاحب المشروع:
      · صاحب المشروع نفسه
      · الشركة التي قُبل عرضها
      · المدير

    إخفاؤها في الواجهة وحدها مسرحٌ أمني — نداء واحد يكشفها.
    فالحَكَم هنا، ولمن لا يحقّ له تُحذف الحقول من الاستجابة كلياً
    لا تُفرَّغ: حقلٌ فارغ يقول «لا رقم له»، وغيابه يقول «ليس لك».
    """
    try:
        payload = _decode_token(request)
    except HTTPException:
        return False

    if payload.get("sub") == ADMIN_USERNAME:
        return True

    token_type = payload.get("type")

    if token_type == "user":
        try:
            user_id = int(payload["user_id"])
        except (KeyError, ValueError):
            return False
        if project.get("owner_user_id") == user_id:
            return True

    # شركة — عبر رمز الشركة القديم أو عضوية مستخدم في شركة
    company_id = None
    if token_type == "company":
        try:
            company_id = int(payload["company_id"])
        except (KeyError, ValueError):
            return False
    elif token_type == "user":
        with SessionLocal() as db:
            cm = db.execute(
                text("SELECT company_id FROM company_members "
                     "WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
                {"uid": payload.get("user_id")},
            ).fetchone()
        company_id = int(cm[0]) if cm else None

    if company_id is None:
        return False

    with SessionLocal() as db:
        won = db.execute(
            text("SELECT 1 FROM project_bids WHERE project_id=:pid "
                 "AND company_id=:cid AND status='accepted'"),
            {"pid": project["id"], "cid": company_id},
        ).first()
    return won is not None


@app.get("/projects/{project_id}")
def get_project(project_id: int, request: Request):
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_bids pb WHERE pb.project_id = p.id) AS bids_count
            FROM projects p WHERE p.id = :id
        """), {"id": project_id}).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")

    out = row_to_project_dict(dict(row))
    if not _may_see_project_contact(request, out):
        _strip_contact(out)
    return out


@app.post("/projects/{project_id}/bid")
def submit_bid(project_id: int, payload: ProjectBidCreate, request: Request):
    company_id = require_company(request)
    if not check_rate_limit(f"bid:company:{company_id}", 30, 3600):
        with SessionLocal() as db:
            write_audit_log(db, "company", str(company_id), "rate_limit:bid", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many bid submissions. Try again later.")
    with SessionLocal() as db:
        company = db.execute(
            text("SELECT status FROM companies WHERE id=:id"),
            {"id": company_id}
        ).mappings().fetchone()
    if not company or company["status"] != "approved":
        raise HTTPException(status_code=403, detail="Only approved companies can submit bids")

    # Enforce monthly project lead limit per subscription plan
    plan  = get_company_plan(company_id)
    usage = get_company_usage(company_id)
    if plan["max_project_leads"] != -1 and usage["leads_used_this_month"] >= plan["max_project_leads"]:
        raise HTTPException(
            status_code=403,
            detail=f"وصلت للحد الأقصى من فرص المشاريع هذا الشهر ({plan['max_project_leads']}). يرجى ترقية الباقة."
        )

    with SessionLocal() as db:
        project = db.execute(
            text("SELECT id, status FROM projects WHERE id=:id"),
            {"id": project_id}
        ).mappings().fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] not in ("published", "pending"):
        raise HTTPException(status_code=400, detail=f"Cannot bid on a {project['status']} project")

    with SessionLocal() as db:
        try:
            result = db.execute(text("""
                INSERT INTO project_bids
                    (project_id, company_id, price, duration_days, message, status)
                VALUES
                    (:project_id, :company_id, :price, :duration_days, :message, 'submitted')
                RETURNING *
            """), {
                "project_id":   project_id,
                "company_id":   company_id,
                "price":        payload.price,
                "duration_days": payload.duration_days,
                "message":      payload.message or "",
            })
            row = result.mappings().fetchone()
            db.commit()
            bid_id = row["id"]
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail="You have already submitted a bid for this project")
            raise HTTPException(status_code=500, detail=str(e))

    with SessionLocal() as db:
        bid_row = db.execute(text("""
            SELECT pb.*, c.name AS company_name, c.image_url AS company_image
            FROM project_bids pb
            JOIN companies c ON c.id = pb.company_id
            WHERE pb.id = :id
        """), {"id": bid_id}).mappings().fetchone()
    return row_to_bid_dict(dict(bid_row))


@app.get("/projects/{project_id}/bids")
def get_project_bids(project_id: int, request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = _decode_token(request)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid token")

    token_type = payload.get("type")

    # Admin sees all bids
    if payload.get("sub") == ADMIN_USERNAME:
        with SessionLocal() as db:
            rows = db.execute(text("""
                SELECT pb.*, c.name AS company_name, c.image_url AS company_image
                FROM project_bids pb
                JOIN companies c ON c.id = pb.company_id
                WHERE pb.project_id = :pid
                ORDER BY pb.price ASC
            """), {"pid": project_id}).mappings().fetchall()
        return [row_to_bid_dict(dict(r)) for r in rows]

    # Project owner sees all bids
    if token_type == "user":
        user_id = int(payload["user_id"])
        with SessionLocal() as db:
            proj = db.execute(
                text("SELECT owner_user_id FROM projects WHERE id=:id"),
                {"id": project_id}
            ).mappings().fetchone()
        if proj and proj["owner_user_id"] == user_id:
            with SessionLocal() as db:
                rows = db.execute(text("""
                    SELECT pb.*, c.name AS company_name, c.image_url AS company_image
                    FROM project_bids pb
                    JOIN companies c ON c.id = pb.company_id
                    WHERE pb.project_id = :pid
                    ORDER BY pb.price ASC
                """), {"pid": project_id}).mappings().fetchall()
            return [row_to_bid_dict(dict(r)) for r in rows]

    # Company sees only their own bid
    if token_type in ("company", "user"):
        if token_type == "company":
            company_id = int(payload["company_id"])
        else:
            user_id = int(payload["user_id"])
            with SessionLocal() as db:
                cm = db.execute(
                    text("SELECT company_id FROM company_members WHERE user_id=:uid ORDER BY created_at LIMIT 1"),
                    {"uid": user_id}
                ).fetchone()
            if not cm:
                raise HTTPException(status_code=403, detail="No company associated")
            company_id = int(cm[0])
        with SessionLocal() as db:
            rows = db.execute(text("""
                SELECT pb.*, c.name AS company_name, c.image_url AS company_image
                FROM project_bids pb
                JOIN companies c ON c.id = pb.company_id
                WHERE pb.project_id = :pid AND pb.company_id = :cid
            """), {"pid": project_id, "cid": company_id}).mappings().fetchall()
        return [row_to_bid_dict(dict(r)) for r in rows]

    raise HTTPException(status_code=403, detail="Access denied")


@app.put("/bids/{bid_id}")
def update_bid(bid_id: int, payload: ProjectBidUpdate, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        bid = db.execute(
            text("SELECT * FROM project_bids WHERE id=:id AND company_id=:cid"),
            {"id": bid_id, "cid": company_id}
        ).mappings().fetchone()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid["status"] in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Cannot modify a finalized bid")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    updates["updated_at"] = datetime.now(timezone.utc)
    updates["id"] = bid_id
    set_clause = ", ".join(f"{k}=:{k}" for k in updates if k != "id")

    with SessionLocal() as db:
        result = db.execute(
            text(f"UPDATE project_bids SET {set_clause} WHERE id=:id RETURNING *"),
            updates
        )
        row = result.mappings().fetchone()
        db.commit()
    return {"id": row["id"], "price": float(row["price"]), "duration_days": row["duration_days"],
            "message": row["message"] or "", "status": row["status"]}


@app.delete("/bids/{bid_id}")
def delete_bid(bid_id: int, request: Request):
    company_id = require_company(request)
    with SessionLocal() as db:
        bid = db.execute(
            text("SELECT * FROM project_bids WHERE id=:id AND company_id=:cid"),
            {"id": bid_id, "cid": company_id}
        ).mappings().fetchone()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    if bid["status"] == "accepted":
        raise HTTPException(status_code=400, detail="Cannot withdraw an accepted bid")
    with SessionLocal() as db:
        db.execute(text("DELETE FROM project_bids WHERE id=:id"), {"id": bid_id})
        db.commit()
    return {"deleted": bid_id}


@app.post("/projects/{project_id}/select-company")
async def select_company(project_id: int, request: Request):
    user_id = require_user(request)
    body = await request.json()
    bid_id = body.get("bid_id")
    if not bid_id:
        raise HTTPException(status_code=400, detail="bid_id is required")

    with SessionLocal() as db:
        project = db.execute(
            text("SELECT * FROM projects WHERE id=:id"),
            {"id": project_id}
        ).mappings().fetchone()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["owner_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the project owner can select a company")
    if project["status"] == "contracted":
        raise HTTPException(status_code=400, detail="A company has already been selected for this project")

    with SessionLocal() as db:
        bid = db.execute(
            text("SELECT * FROM project_bids WHERE id=:bid_id AND project_id=:pid"),
            {"bid_id": bid_id, "pid": project_id}
        ).mappings().fetchone()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found for this project")

    with SessionLocal() as db:
        db.execute(
            text("UPDATE project_bids SET status='accepted', updated_at=now() WHERE id=:id"),
            {"id": bid_id}
        )
        db.execute(
            text("UPDATE project_bids SET status='rejected', updated_at=now() WHERE project_id=:pid AND id!=:bid_id"),
            {"pid": project_id, "bid_id": bid_id}
        )
        db.execute(
            text("UPDATE projects SET status='contracted', updated_at=now() WHERE id=:id"),
            {"id": project_id}
        )
        db.commit()
    return {"project_id": project_id, "status": "contracted", "accepted_bid_id": bid_id}


@app.get("/my/projects")
def my_projects(request: Request):
    user_id = require_user(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_bids pb WHERE pb.project_id = p.id) AS bids_count
            FROM projects p
            WHERE p.owner_user_id = :uid
            ORDER BY p.created_at DESC
        """), {"uid": user_id}).mappings().fetchall()
    return [row_to_project_dict(dict(r)) for r in rows]


@app.get("/admin/projects")
def admin_list_projects(request: Request, status: Optional[str] = None):
    require_admin(request)
    where = "WHERE p.status = :status" if status else ""
    params = {"status": status} if status else {}
    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT p.*,
                   (SELECT COUNT(*) FROM project_bids pb WHERE pb.project_id = p.id) AS bids_count
            FROM projects p {where} ORDER BY p.created_at DESC
        """), params).mappings().fetchall()
    return [row_to_project_dict(dict(r)) for r in rows]


@app.get("/admin/bids")
def admin_list_bids(request: Request):
    require_admin(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT pb.*, c.name AS company_name, c.image_url AS company_image,
                   p.title AS project_title
            FROM project_bids pb
            JOIN companies c ON c.id = pb.company_id
            JOIN projects p ON p.id = pb.project_id
            ORDER BY pb.created_at DESC
        """)).mappings().fetchall()
    result = []
    for r in rows:
        d = row_to_bid_dict(dict(r))
        d["project_title"] = r.get("project_title") or ""
        result.append(d)
    return result


@app.put("/admin/projects/{project_id}/status")
async def admin_update_project_status(project_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    status = body.get("status", "")
    valid = ("pending", "published", "closed", "cancelled", "contracted")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")
    with SessionLocal() as db:
        result = db.execute(
            text("UPDATE projects SET status=:status, updated_at=now() WHERE id=:id RETURNING id, status"),
            {"status": status, "id": project_id}
        )
        row = result.mappings().fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        db.commit()
    return {"id": row["id"], "status": row["status"]}


# ── PHASE 7: SUBSCRIPTIONS & MONETIZATION ────────────────────────────────────

class SubscriptionRequestCreate(BaseModel):
    plan_code: str
    notes: Optional[str] = None

class AdminSubscriptionSet(BaseModel):
    plan_code: str
    months: int = 1
    is_founder: bool = False
    notes: Optional[str] = None


@app.get("/subscription/plans")
def list_plans():
    """Public — list all subscription plans."""
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM subscription_plans ORDER BY search_priority ASC")
        ).mappings().fetchall()
    return [dict(r) for r in rows]


@app.post("/subscription/request")
def request_subscription(payload: SubscriptionRequestCreate, request: Request):
    """Company requests a plan upgrade. Admin approves manually."""
    company_id = require_company(request)

    with SessionLocal() as db:
        plan = db.execute(
            text("SELECT * FROM subscription_plans WHERE code=:code"),
            {"code": payload.plan_code.lower()}
        ).mappings().fetchone()
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan code: {payload.plan_code}")

    # Reject if a pending request already exists
    with SessionLocal() as db:
        existing = db.execute(text("""
            SELECT id FROM subscription_requests
            WHERE company_id=:cid AND status='pending'
            ORDER BY created_at DESC LIMIT 1
        """), {"cid": company_id}).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="You already have a pending subscription request")

    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO subscription_requests (company_id, plan_id, status, notes)
            VALUES (:cid, :pid, 'pending', :notes)
            RETURNING id, created_at
        """), {"cid": company_id, "pid": plan["id"], "notes": payload.notes or ""})
        row = result.mappings().fetchone()
        db.commit()

    return {
        "message": "Subscription request submitted — pending admin approval",
        "request_id": row["id"],
        "plan": payload.plan_code,
        "status": "pending",
        "created_at": str(row["created_at"]),
    }


@app.get("/subscription/request")
def get_my_subscription_request(request: Request):
    """Company checks their latest subscription request status."""
    company_id = require_company(request)
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT sr.*, sp.code AS plan_code, sp.name AS plan_name, sp.monthly_price
            FROM subscription_requests sr
            JOIN subscription_plans sp ON sp.id = sr.plan_id
            WHERE sr.company_id = :cid
            ORDER BY sr.created_at DESC LIMIT 1
        """), {"cid": company_id}).mappings().fetchone()
    if not row:
        return {"status": "none", "message": "No subscription requests found"}
    return {
        "request_id":  row["id"],
        "plan_code":   row["plan_code"],
        "plan_name":   row["plan_name"],
        "monthly_price": float(row["monthly_price"]),
        "status":      row["status"],
        "notes":       row["notes"] or "",
        "created_at":  str(row["created_at"]),
        "processed_at": str(row["processed_at"]) if row["processed_at"] else None,
    }


@app.get("/admin/subscription-requests")
def admin_list_subscription_requests(request: Request, status: Optional[str] = None):
    require_admin(request)
    where = "WHERE 1=1"
    params: dict = {}
    if status:
        where += " AND sr.status=:status"
        params["status"] = status
    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT sr.*, sp.code AS plan_code, sp.name AS plan_name,
                   sp.monthly_price, c.name AS company_name
            FROM subscription_requests sr
            JOIN subscription_plans sp ON sp.id = sr.plan_id
            JOIN companies c ON c.id = sr.company_id
            {where}
            ORDER BY sr.created_at DESC
        """), params).mappings().fetchall()
    return [dict(r) for r in rows]


@app.put("/admin/subscription-requests/{req_id}/approve")
async def admin_approve_subscription(req_id: int, request: Request):
    require_admin(request)
    try:
        body = await request.json()
        months = max(1, int(body.get("months", 1)))
    except Exception:
        months = 1

    with SessionLocal() as db:
        req = db.execute(
            text("SELECT * FROM subscription_requests WHERE id=:id"),
            {"id": req_id}
        ).mappings().fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    with SessionLocal() as db:
        plan = db.execute(
            text("SELECT * FROM subscription_plans WHERE id=:id"),
            {"id": req["plan_id"]}
        ).mappings().fetchone()

    # Auto-assign founder status for first 50 paid companies
    is_founder = False
    if plan["monthly_price"] > 0:
        is_founder = (get_founder_count() < 50)

    now     = datetime.now(timezone.utc)
    expires = now + timedelta(days=30 * months)

    with SessionLocal() as db:
        # Deactivate existing active subscription
        db.execute(text("""
            UPDATE company_subscriptions SET status='expired'
            WHERE company_id=:cid AND status='active'
        """), {"cid": req["company_id"]})

        # Create new subscription
        db.execute(text("""
            INSERT INTO company_subscriptions
                (company_id, plan_id, status, is_founder, start_date, expires_at, auto_renew)
            VALUES
                (:cid, :pid, 'active', :founder, :start, :expires, false)
        """), {
            "cid": req["company_id"], "pid": req["plan_id"],
            "founder": is_founder, "start": now, "expires": expires,
        })

        # Mark request approved
        db.execute(text("""
            UPDATE subscription_requests
            SET status='approved', processed_at=:now, processed_by='admin'
            WHERE id=:id
        """), {"now": now, "id": req_id})

        # لا نسخة ثانية للباقة على جدول companies: الاشتراك أعلاه
        # هو المصدر الوحيد، ونسخةٌ ثانية تفترق عنه بصمت.

        db.commit()

    return {
        "request_id": req_id,
        "company_id": req["company_id"],
        "plan":       plan["code"],
        "is_founder": is_founder,
        "expires_at": str(expires),
        "months":     months,
    }


@app.put("/admin/subscription-requests/{req_id}/reject")
async def admin_reject_subscription(req_id: int, request: Request):
    require_admin(request)
    body = await request.json()
    notes = body.get("notes", "")

    with SessionLocal() as db:
        req = db.execute(
            text("SELECT * FROM subscription_requests WHERE id=:id"),
            {"id": req_id}
        ).mappings().fetchone()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req['status']}")

    with SessionLocal() as db:
        db.execute(text("""
            UPDATE subscription_requests
            SET status='rejected', notes=:notes, processed_at=:now, processed_by='admin'
            WHERE id=:id
        """), {"notes": notes, "now": datetime.now(timezone.utc), "id": req_id})
        db.commit()

    return {"request_id": req_id, "status": "rejected", "notes": notes}


@app.put("/admin/company/{company_id}/subscription")
def admin_set_company_subscription(company_id: int, payload: AdminSubscriptionSet, request: Request):
    """Admin directly sets a company's plan (bypasses request flow)."""
    require_admin(request)

    with SessionLocal() as db:
        plan = db.execute(
            text("SELECT * FROM subscription_plans WHERE code=:code"),
            {"code": payload.plan_code.lower()}
        ).mappings().fetchone()
    if not plan:
        raise HTTPException(status_code=400, detail=f"Invalid plan code: {payload.plan_code}")

    with SessionLocal() as db:
        company = db.execute(
            text("SELECT id FROM companies WHERE id=:id"),
            {"id": company_id}
        ).fetchone()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    is_founder = payload.is_founder
    if not is_founder and plan["monthly_price"] > 0:
        is_founder = (get_founder_count() < 50)

    now     = datetime.now(timezone.utc)
    expires = now + timedelta(days=30 * payload.months)

    with SessionLocal() as db:
        db.execute(text("""
            UPDATE company_subscriptions SET status='expired'
            WHERE company_id=:cid AND status='active'
        """), {"cid": company_id})

        db.execute(text("""
            INSERT INTO company_subscriptions
                (company_id, plan_id, status, is_founder, start_date, expires_at, auto_renew)
            VALUES
                (:cid, :pid, 'active', :founder, :start, :expires, false)
        """), {
            "cid": company_id, "pid": plan["id"],
            "founder": is_founder, "start": now, "expires": expires,
        })

        # المصدر الوحيد للباقة هو company_subscriptions أعلاه.

        db.commit()

    return {
        "company_id": company_id,
        "plan":       plan["code"],
        "is_founder": is_founder,
        "expires_at": str(expires),
        "months":     payload.months,
    }


# ── PHASE 8 HELPERS ──────────────────────────────────────────────────────────

def log_activity(db, company_id=None, user_id=None, action="", metadata="{}"):
    db.execute(text("""
        INSERT INTO activity_log(company_id, user_id, action, metadata)
        VALUES(:cid, :uid, :action, :meta)
    """), {"cid": company_id, "uid": user_id, "action": action, "meta": metadata})


def create_notification(db, user_id=None, company_id=None,
                        ntype="info", title="", message=""):
    db.execute(text("""
        INSERT INTO notifications(user_id, company_id, type, title, message)
        VALUES(:uid, :cid, :type, :title, :msg)
    """), {"uid": user_id, "cid": company_id, "type": ntype,
           "title": title, "msg": message})


def _resolve_auth(request: Request):
    """Decode token; return ('company', company_id) or ('user', user_id).
    Handles dual-JWT: user tokens belonging to company members → company role."""
    payload = _decode_token(request)
    if payload.get("type") == "company":
        cid = payload.get("company_id")
        if not cid:
            raise HTTPException(status_code=401, detail="invalid company token")
        return ("company", int(cid))
    if payload.get("type") == "user":
        uid = int(payload.get("user_id", 0))
        if not uid:
            raise HTTPException(status_code=401, detail="invalid user token")
        with SessionLocal() as db:
            cid = db.execute(text(
                "SELECT company_id FROM company_members WHERE user_id=:uid "
                "ORDER BY created_at LIMIT 1"
            ), {"uid": uid}).scalar()
        if cid:
            return ("company", int(cid))
        return ("user", uid)
    raise HTTPException(status_code=401, detail="Unauthorized")


# ── PHASE 8 Part A: Messaging ─────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    company_id: int
    project_id: Optional[int] = None
    message: str


class MessageCreate(BaseModel):
    message: str


@app.post("/conversations")
def start_conversation(payload: ConversationCreate, request: Request):
    role, actor_id = _resolve_auth(request)
    if role != "user":
        raise HTTPException(status_code=403, detail="Only clients can start conversations")
    uid = actor_id
    with SessionLocal() as db:
        existing = db.execute(text("""
            SELECT id FROM conversations
            WHERE client_user_id=:uid AND company_id=:cid
              AND (project_id IS NOT DISTINCT FROM :pid)
            LIMIT 1
        """), {"uid": uid, "cid": payload.company_id, "pid": payload.project_id}).scalar()
        if existing:
            conv_id = existing
        else:
            conv_id = db.execute(text("""
                INSERT INTO conversations(client_user_id, company_id, project_id)
                VALUES(:uid, :cid, :pid) RETURNING id
            """), {"uid": uid, "cid": payload.company_id, "pid": payload.project_id}).scalar()
        db.execute(text("""
            INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
            VALUES(:conv, 'client', :uid, :msg)
        """), {"conv": conv_id, "uid": uid, "msg": payload.message})
        create_notification(db, company_id=payload.company_id,
                            ntype="new_message", title="رسالة جديدة",
                            message="لديك رسالة جديدة من عميل")
        log_activity(db, user_id=uid, action="start_conversation",
                     metadata=f'{{"conversation_id":{conv_id}}}')
        db.commit()
    return {"conversation_id": conv_id}


@app.get("/conversations")
def list_conversations(request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        if role == "company":
            rows = db.execute(text("""
                SELECT c.id, c.project_id, c.company_id, c.created_at,
                       u.display_name AS client_name,
                       (SELECT COUNT(*) FROM chat_messages m
                        WHERE m.conversation_id=c.id AND m.is_read=false
                          AND m.sender_type = 'client') AS unread
                FROM conversations c
                JOIN users u ON u.id=c.client_user_id
                WHERE c.company_id=:cid
                ORDER BY c.created_at DESC
            """), {"cid": actor_id}).mappings().fetchall()
        else:
            rows = db.execute(text("""
                SELECT c.id, c.project_id, c.company_id, c.created_at,
                       co.name AS company_name,
                       (SELECT COUNT(*) FROM chat_messages m
                        WHERE m.conversation_id=c.id AND m.is_read=false
                          AND m.sender_type != 'client') AS unread
                FROM conversations c
                JOIN companies co ON co.id=c.company_id
                WHERE c.client_user_id=:uid
                ORDER BY c.created_at DESC
            """), {"uid": actor_id}).mappings().fetchall()
    return [dict(r) for r in rows]


@app.get("/conversations/{conv_id}")
def get_conversation(conv_id: int, request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        conv = db.execute(text(
            "SELECT * FROM conversations WHERE id=:id"
        ), {"id": conv_id}).mappings().first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if role == "company" and conv["company_id"] != actor_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if role == "user" and conv["client_user_id"] != actor_id:
            raise HTTPException(status_code=403, detail="Forbidden")
    return dict(conv)


@app.post("/conversations/{conv_id}/messages")
def send_message(conv_id: int, payload: MessageCreate, request: Request):
    role, actor_id = _resolve_auth(request)
    rl_key = f"msg:{role}:{actor_id}"
    if not check_rate_limit(rl_key, 30, 3600):
        with SessionLocal() as db:
            write_audit_log(db, role, str(actor_id), "rate_limit:send_message", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many messages. Try again later.")
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")
    with SessionLocal() as db:
        conv = db.execute(text(
            "SELECT * FROM conversations WHERE id=:id"
        ), {"id": conv_id}).mappings().first()
        if not conv:
            raise HTTPException(status_code=404, detail="Not found")
        if role == "user":
            if conv["client_user_id"] != actor_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            sender_type, sender_id = "client", actor_id
            create_notification(db, company_id=conv["company_id"],
                                ntype="new_message", title="رسالة جديدة",
                                message="لديك رسالة جديدة من عميل")
        else:
            if conv["company_id"] != actor_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            sender_type, sender_id = "company", actor_id
            create_notification(db, user_id=conv["client_user_id"],
                                ntype="new_message", title="رد من الشركة",
                                message="ردّت الشركة على رسالتك")
        msg_id = db.execute(text("""
            INSERT INTO chat_messages(conversation_id, sender_type, sender_id, message)
            VALUES(:conv, :st, :sid, :msg) RETURNING id
        """), {"conv": conv_id, "st": sender_type,
               "sid": sender_id, "msg": payload.message}).scalar()
        db.commit()
    return {"message_id": msg_id}


@app.get("/conversations/{conv_id}/messages")
def get_messages(conv_id: int, request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        conv = db.execute(text(
            "SELECT * FROM conversations WHERE id=:id"
        ), {"id": conv_id}).mappings().first()
        if not conv:
            raise HTTPException(status_code=404, detail="Not found")
        if role == "company":
            if conv["company_id"] != actor_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            db.execute(text("""
                UPDATE chat_messages SET is_read=true
                WHERE conversation_id=:cid AND sender_type = 'client'
            """), {"cid": conv_id})
        else:
            if conv["client_user_id"] != actor_id:
                raise HTTPException(status_code=403, detail="Forbidden")
            db.execute(text("""
                UPDATE chat_messages SET is_read=true
                WHERE conversation_id=:cid AND sender_type != 'client'
            """), {"cid": conv_id})
        db.commit()
        rows = db.execute(text("""
            SELECT id, sender_type, sender_id, message, is_read, created_at
            FROM chat_messages WHERE conversation_id=:cid
            ORDER BY created_at ASC
        """), {"cid": conv_id}).mappings().fetchall()
    return [dict(r) for r in rows]


@app.put("/messages/{msg_id}/read")
def mark_message_read(msg_id: int, request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        msg = db.execute(text("""
            SELECT m.*, c.client_user_id, c.company_id
            FROM chat_messages m JOIN conversations c ON c.id=m.conversation_id
            WHERE m.id=:id
        """), {"id": msg_id}).mappings().first()
        if not msg:
            raise HTTPException(status_code=404, detail="Not found")
        allowed = ((role == "user" and msg["client_user_id"] == actor_id) or
                   (role == "company" and msg["company_id"] == actor_id))
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        db.execute(text("UPDATE chat_messages SET is_read=true WHERE id=:id"),
                   {"id": msg_id})
        db.commit()
    return {"ok": True}


# ── PHASE 8 Part B: Notifications ─────────────────────────────────────────────

@app.get("/notifications")
def get_notifications(request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        if role == "company":
            rows = db.execute(text("""
                SELECT * FROM notifications WHERE company_id=:cid
                ORDER BY created_at DESC LIMIT 50
            """), {"cid": actor_id}).mappings().fetchall()
        else:
            rows = db.execute(text("""
                SELECT * FROM notifications WHERE user_id=:uid
                ORDER BY created_at DESC LIMIT 50
            """), {"uid": actor_id}).mappings().fetchall()
    return [dict(r) for r in rows]


@app.put("/notifications/read-all")
def mark_all_notifications_read(request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        if role == "company":
            db.execute(text(
                "UPDATE notifications SET is_read=true WHERE company_id=:cid"
            ), {"cid": actor_id})
        else:
            db.execute(text(
                "UPDATE notifications SET is_read=true WHERE user_id=:uid"
            ), {"uid": actor_id})
        db.commit()
    return {"ok": True}


@app.put("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: int, request: Request):
    role, actor_id = _resolve_auth(request)
    with SessionLocal() as db:
        n = db.execute(text(
            "SELECT * FROM notifications WHERE id=:id"
        ), {"id": notif_id}).mappings().first()
        if not n:
            raise HTTPException(status_code=404, detail="Not found")
        allowed = ((role == "company" and n["company_id"] == actor_id) or
                   (role == "user" and n["user_id"] == actor_id))
        if not allowed:
            raise HTTPException(status_code=403, detail="Forbidden")
        db.execute(text("UPDATE notifications SET is_read=true WHERE id=:id"),
                   {"id": notif_id})
        db.commit()
    return {"ok": True}


# ── PHASE 8 Part C: Reviews ───────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    company_id: int
    client_name: str
    project_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None


class ReviewReplyCreate(BaseModel):
    reply: str


@app.post("/reviews")
def submit_review(payload: ReviewCreate, request: Request):
    # B5: Only authenticated users (not guests, not companies) can submit reviews
    user_id = require_user(request)
    # Block company members from reviewing
    with SessionLocal() as db:
        is_company_member = db.execute(
            text("SELECT 1 FROM company_members WHERE user_id=:uid LIMIT 1"),
            {"uid": user_id}
        ).fetchone()
    if is_company_member:
        raise HTTPException(status_code=403, detail="لا يمكن لحسابات الشركات إضافة تقييمات")
    ip = get_client_ip(request)
    if not check_rate_limit(f"review:{ip}", 30, 3600):
        with SessionLocal() as db:
            write_audit_log(db, "ip", ip, "rate_limit:review", request)
            db.commit()
        raise HTTPException(status_code=429, detail="Too many reviews. Try again later.")
    if not payload.client_name or not payload.client_name.strip():
        raise HTTPException(status_code=422, detail="Client name is required")
    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be 1-5")
    with SessionLocal() as db:
        # Check company exists
        co = db.execute(text("SELECT id FROM companies WHERE id=:id"),
                        {"id": payload.company_id}).scalar()
        if not co:
            raise HTTPException(status_code=404, detail="Company not found")
        try:
            rev_id = db.execute(text("""
                INSERT INTO reviews(company_id, client_name, project_id, rating, comment)
                VALUES(:cid, :cname, :pid, :rating, :comment)
                RETURNING id
            """), {"cid": payload.company_id, "cname": payload.client_name,
                   "pid": payload.project_id, "rating": payload.rating,
                   "comment": payload.comment}).scalar()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Review for this project already exists")
        create_notification(db, company_id=payload.company_id,
                            ntype="new_review", title="تقييم جديد",
                            message=f"تلقيت تقييماً جديداً بتقدير {payload.rating}/5")
        db.commit()
    return {"review_id": rev_id, "status": "pending"}


@app.get("/company/{company_id}/reviews")
def get_company_reviews(company_id: int):
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT r.id, r.client_name, r.rating, r.comment, r.created_at,
                   rr.reply, rr.created_at AS reply_at
            FROM reviews r
            LEFT JOIN review_replies rr ON rr.review_id=r.id
            WHERE r.company_id=:cid AND r.status='approved'
            ORDER BY r.created_at DESC
        """), {"cid": company_id}).mappings().fetchall()
    return [dict(r) for r in rows]


@app.post("/reviews/{review_id}/reply")
def reply_to_review(review_id: int, payload: ReviewReplyCreate, request: Request):
    cid = require_company(request)
    with SessionLocal() as db:
        rev = db.execute(text(
            "SELECT * FROM reviews WHERE id=:id"
        ), {"id": review_id}).mappings().first()
        if not rev:
            raise HTTPException(status_code=404, detail="Review not found")
        if rev["company_id"] != cid:
            raise HTTPException(status_code=403, detail="Forbidden")
        # Delete existing reply then insert
        db.execute(text("DELETE FROM review_replies WHERE review_id=:rid"),
                   {"rid": review_id})
        db.execute(text("""
            INSERT INTO review_replies(review_id, company_id, reply)
            VALUES(:rid, :cid, :reply)
        """), {"rid": review_id, "cid": cid, "reply": payload.reply})
        db.commit()
    return {"ok": True}


@app.get("/admin/reviews")
def admin_list_reviews(request: Request, status: Optional[str] = None):
    require_admin(request)
    where = "WHERE r.status = :status" if status else ""
    params = {"status": status} if status else {}
    with SessionLocal() as db:
        rows = db.execute(text(f"""
            SELECT r.*, co.name AS company_name
            FROM reviews r JOIN companies co ON co.id=r.company_id
            {where}
            ORDER BY r.created_at DESC
        """), params).mappings().fetchall()
    return [dict(r) for r in rows]


@app.put("/admin/subscription-plans/{plan_id}/recommended")
def set_plan_recommended(plan_id: int, payload: dict, request: Request):
    """
    مفتاح «توصيتنا» على باقة. توصية واحدة فقط في كل وقت.

    شارة رأي منسوبة إلى المنصّة، لا إحصاء. تُستبدَل بإحصاء حقيقي
    حين يوجد مشتركون فعليون (DESIGN.md §٥·٥).
    """
    require_admin(request)
    on = bool(payload.get("is_recommended", True))
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT id FROM subscription_plans WHERE id=:id"), {"id": plan_id}
        ).first()
        if not row:
            raise HTTPException(status_code=404, detail="الباقة غير موجودة")
        if on:
            db.execute(text("UPDATE subscription_plans SET is_recommended=FALSE"))
        db.execute(
            text("UPDATE subscription_plans SET is_recommended=:v WHERE id=:id"),
            {"v": on, "id": plan_id},
        )
        write_audit_log(db, "admin", ADMIN_USERNAME,
                        f"plan_recommended:{plan_id}:{on}", request)
        db.commit()
    return {"ok": True, "plan_id": plan_id, "is_recommended": on}


@app.get("/admin/users")
def admin_list_users(request: Request):
    require_admin(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, email, display_name AS name, is_active, created_at
            FROM users ORDER BY created_at DESC LIMIT 200
        """)).mappings().fetchall()
    return [dict(r) for r in rows]


@app.put("/admin/reviews/{review_id}/approve")
def admin_approve_review(review_id: int, request: Request):
    require_admin(request)
    with SessionLocal() as db:
        db.execute(text("UPDATE reviews SET status='approved' WHERE id=:id"),
                   {"id": review_id})
        db.commit()
    return {"ok": True}


@app.put("/admin/reviews/{review_id}/reject")
def admin_reject_review(review_id: int, request: Request):
    require_admin(request)
    with SessionLocal() as db:
        db.execute(text("UPDATE reviews SET status='rejected' WHERE id=:id"),
                   {"id": review_id})
        db.commit()
    return {"ok": True}


# ── PHASE 8 Part D (admin): Activity log ──────────────────────────────────────

@app.get("/admin/audit-log")
def admin_audit_log(request: Request, limit: int = 200):
    """
    سجل التدقيق الأمني — security_audit_log.

    كان الجدول يُكتَب ولا يُقرأ: system-status يعدّ صفوفه، ولا مسار
    يعرضها. فشاشة «سجل التدقيق» كانت تقرأ activity_log (نشاط
    الشركات) وتظهر فارغة بينما ١٦٥ حدثاً أمنياً مسجَّل.

    ip_hash لا يُعاد: تجزئة العنوان تكفي للربط بين الأحداث ولا
    حاجة لتسريبها إلى الواجهة.
    """
    require_admin(request)
    limit = min(max(limit, 1), 500)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT id, actor_type, actor_id, action, user_agent, meta, created_at
            FROM security_audit_log
            ORDER BY created_at DESC
            LIMIT :lim
        """), {"lim": limit}).mappings().fetchall()
    return [{
        "id":         r["id"],
        "actor_type": r["actor_type"],
        "actor_id":   r["actor_id"],
        "action":     r["action"],
        "user_agent": (r["user_agent"] or "")[:180],
        "meta":       r["meta"],
        "created_at": str(r["created_at"]),
    } for r in rows]


@app.get("/admin/activity")
def admin_activity(request: Request):
    require_admin(request)
    with SessionLocal() as db:
        rows = db.execute(text("""
            SELECT al.*, co.name AS company_name
            FROM activity_log al
            LEFT JOIN companies co ON co.id=al.company_id
            ORDER BY al.created_at DESC
            LIMIT 200
        """)).mappings().fetchall()
    return [dict(r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 10 — SEO & LAUNCH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/company/slug/{slug}")
def company_by_slug(slug: str):
    """
    Resolve a human-readable slug to a company ID.
    Slug is derived from the company name: lowercase, spaces→hyphens, Arabic allowed.
    Falls back to numeric ID if slug is a number.
    """
    if slug.isdigit():
        return {"company_id": int(slug), "redirect": f"/company/{slug}"}
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT id FROM companies
            WHERE status='approved'
              AND LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9؀-ۿ]+', '-', 'g')) = LOWER(:slug)
            LIMIT 1
        """), {"slug": slug}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"company_id": row[0], "redirect": f"/company/{row[0]}"}


@app.get("/stats")
def public_stats():
    """Public platform statistics for homepage."""
    with SessionLocal() as db:
        companies  = db.execute(text("SELECT COUNT(*) FROM companies WHERE status='approved'")).scalar() or 0
        projects   = db.execute(text("SELECT COUNT(*) FROM projects WHERE status='published'")).scalar() or 0
        reviews    = db.execute(text("SELECT COUNT(*) FROM reviews WHERE status='approved'")).scalar() or 0
        avg_rating = db.execute(text("SELECT ROUND(AVG(rating)::numeric,1) FROM reviews WHERE status='approved'")).scalar()
    return {
        "companies":  int(companies),
        "projects":   int(projects),
        "reviews":    int(reviews),
        "avg_rating": float(avg_rating) if avg_rating else 0.0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 9 — HEALTH & MONITORING
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
def health_check():
    """Public health endpoint — checks DB connectivity."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"database": "ok", "app": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail={"database": "error", "app": "ok", "error": str(e)})


@app.get("/admin/system-status")
def system_status(request: Request):
    """Admin-only system status with aggregate counts."""
    require_admin(request)
    with SessionLocal() as db:
        def count(table, where=""):
            sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
            return db.execute(text(sql)).scalar() or 0

        return {
            "companies":    {"total": count("companies"), "approved": count("companies", "status='approved'"), "pending": count("companies", "status='pending'")},
            "projects":     {"total": count("projects"), "published": count("projects", "status='published'")},
            "subscriptions":{"total": count("company_subscriptions"), "active": count("company_subscriptions", "status='active'")},
            "messages":     {"total": count("chat_messages")},
            "conversations":{"total": count("conversations")},
            "reviews":      {"total": count("reviews"), "approved": count("reviews", "status='approved'"), "pending": count("reviews", "status='pending'")},
            "users":        {"total": count("users"), "active": count("users", "is_active=true")},
            "audit_log":    {"total": count("security_audit_log")},
        }


# ── Static files (MUST be last) ──────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
app.mount('/', StaticFiles(directory='public', html=True), name='static')
