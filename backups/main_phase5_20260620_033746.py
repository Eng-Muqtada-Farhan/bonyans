import os
from datetime import datetime, timedelta
from typing import Literal, Optional

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth helpers ──────────────────────────────────────────────────────────────
def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
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


# ── DB helpers ────────────────────────────────────────────────────────────────
def row_to_company_dict(r: dict) -> dict:
    return {
        "id":         r["id"],
        "name":       r["name"],
        "city":       r["city"],
        "phone":      r["phone"],
        "spec":       r["spec"],
        "desc":       r["description"],   # PostgreSQL column is 'description'
        "email":      r["email"],
        "website":    r["website"],
        "map_link":   r["map_link"],
        "rating":     r["rating"],
        "verified":   bool(r["verified"]),
        "status":     r["status"],
        "created_at": r["created_at"],
        "image_url":  r.get("image_url") or "",
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

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """رفع صورة إلى ImageKit وإرجاع رابطها."""
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
def add_company(company: Company):
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
def get_companies():
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT * FROM companies WHERE status='approved' ORDER BY id DESC")
        ).mappings().fetchall()
    return [row_to_company_dict(dict(r)) for r in rows]


@app.get("/admin/companies")
def get_all_companies():
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

    with SessionLocal() as db:
        result = db.execute(text("""
            UPDATE companies SET status=:status, verified=:verified WHERE id=:id
        """), {"status": status, "verified": verified, "id": id})
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
def login(data: dict):
    username = data.get("username", "")
    password = data.get("password", "")
    hashed   = os.getenv("ADMIN_PASSWORD_HASH", "")
    if username != ADMIN_USERNAME or not hashed or not pwd_context.verify(password, hashed):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_access_token(username)}
