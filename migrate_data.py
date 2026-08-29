"""
سكريبت الترحيل: SQLite -> PostgreSQL
تشغيل: python migrate_data.py

المتطلبات قبل التشغيل:
  1. DATABASE_URL مضبوط وغير معلَّق في .env
  2. قاعدة بيانات PostgreSQL موجودة وقابلة للوصول
  3. companies.db موجود في نفس المجلد
  4. تشغيل backup_sqlite.py اولاً

الضمانات:
  - يحافظ على نفس الـ IDs تماماً
  - يتعامل مع null بأمان
  - العمود desc في SQLite يُرحَّل باسم description في PostgreSQL
  - ON CONFLICT DO NOTHING يمنع التكرار عند إعادة التشغيل
  - لا يحذف ولا يعدّل companies.db
"""
import sqlite3
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

SQLITE_PATH  = "companies.db"
DATABASE_URL = os.getenv("DATABASE_URL", "")


def abort(msg: str) -> None:
    print(f"\nABORT: {msg}")
    sys.exit(1)


def remap_row(row: dict) -> dict:
    """
    يُعيد تسمية 'desc' -> 'description' لأن desc كلمة محجوزة في PostgreSQL.
    يعمل بأمان حتى لو كان المفتاح غير موجود.
    """
    out = dict(row)
    if "desc" in out:
        out["description"] = out.pop("desc")
    return out


def main() -> None:
    # ── 1. التحقق من المتطلبات ──────────────────────────────────────────
    print("Phase 3 - Data Migration: SQLite -> PostgreSQL")
    print("=" * 50)

    if not DATABASE_URL:
        abort("DATABASE_URL is not set in .env — uncomment and fill it first")
    if not os.path.exists(SQLITE_PATH):
        abort(f"{SQLITE_PATH} not found — run from project root")

    # ── 2. قراءة البيانات من SQLite ──────────────────────────────────────
    print("\n[1/5] Reading SQLite data...")
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()
    cur.execute("SELECT * FROM companies ORDER BY id")
    raw_rows = [dict(r) for r in cur.fetchall()]
    sqlite_conn.close()

    # إعادة تسمية desc -> description لجميع الصفوف
    rows = [remap_row(r) for r in raw_rows]
    print(f"      Found {len(rows)} rows")
    if rows:
        print(f"      Columns: {list(rows[0].keys())}")

    if not rows:
        print("      No rows to migrate. Exiting.")
        return

    # ── 3. الاتصال بـ PostgreSQL ─────────────────────────────────────────
    print("\n[2/5] Connecting to PostgreSQL...")
    try:
        pg_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with pg_engine.connect() as c:
            c.execute(text("SELECT 1"))
        print("      Connection OK")
    except Exception as e:
        abort(f"Cannot connect to PostgreSQL: {e}")

    # ── 4. إنشاء الجدول إن لم يكن موجوداً ──────────────────────────────
    # ملاحظة: 'description' بدلاً من 'desc' — desc كلمة محجوزة في PostgreSQL
    print("\n[3/5] Creating table (if not exists)...")
    with pg_engine.begin() as pg:
        pg.execute(text("""
            CREATE TABLE IF NOT EXISTS companies (
                id          SERIAL PRIMARY KEY,
                name        TEXT,
                city        TEXT,
                phone       TEXT,
                spec        TEXT,
                description TEXT,
                email       TEXT,
                website     TEXT,
                map_link    TEXT,
                rating      DOUBLE PRECISION DEFAULT 5,
                verified    INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT
            )
        """))
    print("      Table ready")

    # ── 5. نقل البيانات مع الحفاظ على الـ IDs ───────────────────────────
    print(f"\n[4/5] Migrating {len(rows)} rows...")
    inserted = 0
    skipped  = 0

    with pg_engine.begin() as pg:
        pg.execute(text("ALTER TABLE companies DISABLE TRIGGER ALL"))

        for row in rows:
            result = pg.execute(text("""
                INSERT INTO companies
                    (id, name, city, phone, spec, description, email, website,
                     map_link, rating, verified, status, created_at)
                VALUES
                    (:id, :name, :city, :phone, :spec, :description, :email, :website,
                     :map_link, :rating, :verified, :status, :created_at)
                ON CONFLICT (id) DO NOTHING
            """), row)
            if result.rowcount == 1:
                inserted += 1
            else:
                skipped += 1

        pg.execute(text("ALTER TABLE companies ENABLE TRIGGER ALL"))

        # إعادة ضبط الـ sequence ليكمل بعد أعلى id
        pg.execute(text(
            "SELECT setval('companies_id_seq', (SELECT MAX(id) FROM companies))"
        ))

    print(f"      Inserted : {inserted}")
    print(f"      Skipped  : {skipped} (already existed)")

    # ── 6. التحقق من التطابق ─────────────────────────────────────────────
    print("\n[5/5] Verifying row counts...")
    with pg_engine.connect() as pg:
        pg_count  = pg.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        pg_cols   = pg.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'companies' ORDER BY ordinal_position
        """)).fetchall()

    col_names = [r[0] for r in pg_cols]
    print(f"      SQLite rows       : {len(rows)}")
    print(f"      PostgreSQL rows   : {pg_count}")
    print(f"      PostgreSQL columns: {col_names}")

    # تأكد أن 'desc' غير موجود كعمود
    if "desc" in col_names:
        abort("CRITICAL: column 'desc' found in PostgreSQL — reserved word not renamed!")
    if "description" not in col_names:
        abort("CRITICAL: column 'description' missing from PostgreSQL table!")

    if pg_count < len(rows) - skipped:
        abort(f"Row count mismatch! Expected at least {len(rows) - skipped}, got {pg_count}")

    # ── النتيجة ──────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print("Migration successful!")
    print(f"  SQLite file preserved at : {SQLITE_PATH}")
    print(f"  PostgreSQL total rows    : {pg_count}")
    print("  Column 'desc' renamed to 'description': OK")
    print("\nNext step: modify main.py to switch active database to PostgreSQL")


if __name__ == "__main__":
    main()
