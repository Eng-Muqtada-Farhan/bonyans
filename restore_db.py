"""
استعادة نسخة احتياطية والتحقّق من نجاحها — لا تُعدّ نسخة نجحت
حتى تُستعاد فعلياً وتُقارَن بياناتها بالمصدر
═══════════════════════════════════════════════════════════════

⛔ --target يجب أن يكون قاعدة نظيفة مخصَّصة لهذا الاختبار وحده —
   لن يُقبل رابط يطابق DATABASE_URL أو DATABASE_URL_UNPOOLED من
   .env كأمان إضافي ضد استعادة تكتب فوق الإنتاج بالخطأ.

الاستعمال:
    python restore_db.py --file backups/bunyan_20260903_120000.dump \
                          --target "postgresql://user:pass@host/clean_db"

يشغّل pg_restore على --target، ثم يقارن COUNT(*) لكل جدول عام بين
المصدر (DATABASE_URL_UNPOOLED في .env) والهدف بعد الاستعادة،
ويطبع جدول تطابق صريحاً. أي فارق = فشل التحقّق، لا نجاح مع تحذير.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _check_binary(name: str) -> None:
    try:
        subprocess.run([name, "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit(f"{name} غير موجود على PATH — ثبّت PostgreSQL Client Tools أولاً.")


def _guard_target(target: str) -> None:
    prod_urls = {os.getenv("DATABASE_URL", ""), os.getenv("DATABASE_URL_UNPOOLED", "")}
    prod_urls.discard("")
    if target in prod_urls:
        sys.exit(
            "⛔ رُفض: --target يطابق DATABASE_URL أو DATABASE_URL_UNPOOLED "
            "من .env — هذا سكربت استعادة إلى قاعدة نظيفة منفصلة، لا كتابة "
            "فوق الإنتاج. مرّر رابط قاعدة اختبار مخصَّصة."
        )


def _table_counts(url: str) -> dict[str, int]:
    eng = create_engine(url)
    try:
        with eng.connect() as c:
            tables = [r[0] for r in c.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1"
            ))]
            return {t: c.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar() for t in tables}
    finally:
        eng.dispose()


def restore_and_verify(dump_file: Path, target: str) -> bool:
    _check_binary("pg_restore")
    _guard_target(target)
    if not dump_file.exists():
        sys.exit(f"لا يوجد الملفّ {dump_file}")

    print(f"استعادة {dump_file.name} إلى القاعدة الهدف...")
    result = subprocess.run(
        ["pg_restore", "--no-owner", "--no-acl", "--clean", "--if-exists",
         "-d", target, str(dump_file)],
        capture_output=True, text=True,
    )
    # pg_restore يُعيد رمز خروج غير صفري أحياناً حتى مع نجاح فعلي
    # (تحذيرات عن أدوار/امتدادات غير موجودة على الهدف) — الحكم
    # الحقيقي هو مطابقة البيانات أدناه لا رمز الخروج وحده.
    if result.returncode != 0:
        print("── تحذيرات/أخطاء pg_restore ──", file=sys.stderr)
        print(result.stderr, file=sys.stderr)

    source_url = os.getenv("DATABASE_URL_UNPOOLED") or os.getenv("DATABASE_URL")
    if not source_url:
        sys.exit("لا يوجد DATABASE_URL_UNPOOLED للمقارنة")

    print("\nمقارنة عدد الصفوف — المصدر مقابل الهدف بعد الاستعادة:")
    src = _table_counts(source_url)
    dst = _table_counts(target)

    all_tables = sorted(set(src) | set(dst))
    ok = True
    for t in all_tables:
        s, d = src.get(t, "غائب"), dst.get(t, "غائب")
        match = s == d
        ok = ok and match
        print(f"  {'✓' if match else '✗'} {t:<28} مصدر={s:<8} هدف={d}")

    print()
    if ok:
        print(f"✓ نجحت الاستعادة والتحقّق — {len(all_tables)} جدولاً متطابقة تماماً.")
    else:
        print("✗ فشل التحقّق — فرق في عدد الصفوف لجدول واحد على الأقل.")
    return ok


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, type=Path)
    p.add_argument("--target", required=True,
                   help="رابط اتصال قاعدة نظيفة مخصَّصة لهذا الاختبار — ليس الإنتاج")
    args = p.parse_args()
    success = restore_and_verify(args.file, args.target)
    sys.exit(0 if success else 1)
