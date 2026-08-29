import os
from datetime import datetime, timedelta
from typing import Literal

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext
import sqlite3

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
JWT_SECRET     = os.getenv("JWT_SECRET", "")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set in .env — server cannot start.")

ALGORITHM   = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# السماح للـ HTML يتصل بالسيرفر
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# قاعدة البيانات
DB_PATH = "companies.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

ALLOWED_STATUSES = ("pending", "approved", "rejected")


def init_db() -> None:
    # إنشاء الجدول
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            city TEXT,
            phone TEXT,
            spec TEXT,
            desc TEXT,
            email TEXT,
            website TEXT,
            map_link TEXT,
            rating REAL DEFAULT 5,
            verified INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
        """
    )
    conn.commit()

    # إضافة أعمدة إذا لم تكن موجودة
    for ddl in (
        "ALTER TABLE companies ADD COLUMN verified INTEGER DEFAULT 0",
        "ALTER TABLE companies ADD COLUMN status TEXT DEFAULT 'pending'",
        "ALTER TABLE companies ADD COLUMN created_at TEXT",
        "ALTER TABLE companies ADD COLUMN email TEXT",
        "ALTER TABLE companies ADD COLUMN website TEXT",
        "ALTER TABLE companies ADD COLUMN map_link TEXT",
        "ALTER TABLE companies ADD COLUMN rating REAL DEFAULT 5",
    ):
        try:
            cursor.execute(ddl)
        except sqlite3.OperationalError:
            pass

    cursor.execute("UPDATE companies SET status='pending' WHERE status IS NULL OR status=''")
    conn.commit()


init_db()


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


def row_to_company_dict(r: sqlite3.Row) -> dict:
    return {
        "id": r["id"],
        "name": r["name"],
        "city": r["city"],
        "phone": r["phone"],
        "spec": r["spec"],
        "desc": r["desc"],
        "email": r["email"],
        "website": r["website"],
        "map_link": r["map_link"],
        "rating": r["rating"],
        "verified": bool(r["verified"]),
        "status": r["status"],
        "created_at": r["created_at"],
    }


# موديل البيانات
class Company(BaseModel):
    name: str
    city: str
    phone: str
    spec: str
    desc: str
    email: str = ""
    website: str = ""
    map_link: str = ""
    rating: float = 5


class CompanyStatusUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected"]


# إضافة شركة
@app.post("/companies")
def add_company(company: Company):
    cursor.execute(
        """
        INSERT INTO companies 
        (name, city, phone, spec, desc, email, website, map_link, rating, verified, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            company.name,
            company.city,
            company.phone,
            company.spec,
            company.desc,
            company.email,
            company.website,
            company.map_link,
            company.rating,
            0,
            "pending",
            datetime.now().isoformat(),
        ),
    )
    conn.commit()

    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM companies WHERE id=?", (new_id,))
    row = cursor.fetchone()
    return row_to_company_dict(row)


# جلب الشركات (العامة)
@app.get("/companies")
def get_companies():
    cursor.execute("SELECT * FROM companies WHERE status='approved' ORDER BY id DESC")
    rows = cursor.fetchall()
    return [row_to_company_dict(r) for r in rows]


# جلب الشركات (أدمن)
@app.get("/admin/companies")
def get_all_companies():
    cursor.execute("SELECT * FROM companies ORDER BY id DESC")
    rows = cursor.fetchall()
    return [row_to_company_dict(r) for r in rows]


# تحديث الحالة
@app.put("/companies/{id}/status")
def update_company_status(id: int, payload: CompanyStatusUpdate, request: Request):
    require_admin(request)

    status = payload.status
    if status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="invalid status")

    verified = 1 if status == "approved" else 0
    cursor.execute("UPDATE companies SET status=?, verified=? WHERE id=?", (status, verified, id))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="not found")

    conn.commit()
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
    hashed = os.getenv("ADMIN_PASSWORD_HASH", "")
    if username != ADMIN_USERNAME or not hashed or not pwd_context.verify(password, hashed):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return {"token": create_access_token(username)}