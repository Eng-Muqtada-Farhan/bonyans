"""
نسخ احتياطي حقيقي لقاعدة بُنيان — pg_dump فعلي، لا محاكاة
═══════════════════════════════════════════════════════════════

يستهدف DATABASE_URL_UNPOOLED (لا المجمَّع — Neon توصي بالاتصال
المباشر لـpg_dump، فتجميع PgBouncer قد يتعارض مع عمليات طويلة).

الاستعمال:
    python backup_db.py                     # نسخة إلى backups/
    python backup_db.py --keep-days 30      # واحذف الأقدم من ٣٠ يوماً

النتيجة ملفّ بصيغة custom format (-F c) — يُستعاد بـpg_restore
لا بـpsql مباشرة. راجع restore_db.py للاستعادة والتحقّق.

يحتاج pg_dump على PATH (حزمة "PostgreSQL Client Tools").
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
BACKUP_DIR = ROOT / "backups"

load_dotenv(ROOT / ".env")


def _database_url() -> str:
    url = os.getenv("DATABASE_URL_UNPOOLED") or os.getenv("DATABASE_URL")
    if not url:
        sys.exit("لا يوجد DATABASE_URL_UNPOOLED ولا DATABASE_URL في .env")
    return url


def _check_pg_dump() -> None:
    try:
        subprocess.run(["pg_dump", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit(
            "pg_dump غير موجود على PATH.\n"
            "ثبّت PostgreSQL Client Tools (لا حاجة لخادم كامل):\n"
            "  winget install PostgreSQL.PostgreSQL.17 --scope machine\n"
            "  (اختر Command Line Tools فقط عند التثبيت اليدوي إن أمكن)"
        )


def run_backup(keep_days: int | None) -> Path:
    _check_pg_dump()
    BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"bunyan_{stamp}.dump"

    url = _database_url()
    t0 = time.monotonic()
    result = subprocess.run(
        ["pg_dump", url, "-F", "c", "--no-owner", "--no-acl", "-f", str(out_path)],
        capture_output=True, text=True,
    )
    elapsed = time.monotonic() - t0
    if result.returncode != 0:
        sys.exit(f"فشل pg_dump (خرج {result.returncode}):\n{result.stderr}")

    size = out_path.stat().st_size
    print(f"تم: {out_path.name} — {size:,} بايت في {elapsed:.1f}ث")

    if keep_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
        removed = 0
        for f in BACKUP_DIR.glob("bunyan_*.dump"):
            if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc) < cutoff:
                f.unlink()
                removed += 1
        if removed:
            print(f"حُذف {removed} نسخة أقدم من {keep_days} يوماً")

    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--keep-days", type=int, default=None,
                   help="احذف النسخ الأقدم من هذا العدد من الأيام بعد النجاح")
    args = p.parse_args()
    run_backup(args.keep_days)
