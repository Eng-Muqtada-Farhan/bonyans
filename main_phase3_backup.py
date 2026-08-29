import os
from datetime import datetime, timedelta
from typing import Literal

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# ── Auth config ───────────────────────────────────────────────────────────────
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
    auth = request.headers.get("Authorization", "")
    # Accept both raw token (current admin.html) and standard "Bearer <token>"
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
    }


# ── Pydantic models ───────────────────────────────────────────────────────────
class Company(BaseModel):
    name:     str
    city:     str
    phone:    str
    spec:     str
    desc:     str
    email:    str   = ""
    website:  str   = ""
    map_link: str   = ""
    rating:   float = 5


class CompanyStatusUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected"]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/companies")
def add_company(company: Company):
    with SessionLocal() as db:
        result = db.execute(text("""
            INSERT INTO companies
                (name, city, phone, spec, description, email, website,
                 map_link, rating, verified, status, created_at)
            VALUES
                (:name, :city, :phone, :spec, :description, :email, :website,
                 :map_link, :rating, :verified, :status, :created_at)
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
