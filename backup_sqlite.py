"""
النسخ الاحتياطي لـ companies.db
تشغيل: python backup_sqlite.py

ينشئ ملف: companies.db.backup_YYYYMMDD_HHMMSS
في نفس مجلد المشروع.
"""
import shutil
import os
from datetime import datetime

SRC = "companies.db"

if not os.path.exists(SRC):
    print(f"ERROR: {SRC} not found — run from project root")
    exit(1)

dst = f"companies.db.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(SRC, dst)

src_size = os.path.getsize(SRC)
dst_size = os.path.getsize(dst)

if src_size != dst_size:
    print(f"ERROR: Size mismatch! src={src_size} dst={dst_size}")
    exit(1)

print(f"Backup created : {dst}")
print(f"Size           : {dst_size:,} bytes")
print(f"Original kept  : {SRC}")
