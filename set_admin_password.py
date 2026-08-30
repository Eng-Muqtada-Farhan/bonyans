"""
ضبط كلمة مرور المدير — المهمة 0.2

يطلب كلمة المرور بلا إظهارها على الشاشة، يولّد تجزئة bcrypt،
ثم يكتب ADMIN_PASSWORD و ADMIN_PASSWORD_HASH في .env
دون المساس ببقية المتغيرات.

التشغيل:
    venv\\Scripts\\python.exe set_admin_password.py

أو ولّدها عشوائياً بلا كتابتها:
    venv\\Scripts\\python.exe set_admin_password.py --generate

لا يطبع كلمة المرور ولا التجزئة في أي مخرَج — ولا حتى مع --generate.
اقرأ القيمة من .env عند الحاجة.
"""
import argparse
import getpass
import io
import os
import re
import secrets
import sys

import bcrypt

ENV_PATH = ".env"
MIN_LEN = 16
GEN_LEN = 28

# بلا محارف ملتبسة (O/0 و l/I/1) — تُقرأ من .env وتُنسخ يدوياً أحياناً.
GEN_ALPHABET = ("ABCDEFGHJKMNPQRSTUVWXYZ"
                "abcdefghijkmnpqrstuvwxyz"
                "23456789"
                "!@#%^&*-_=+")


def generate_password(length: int = GEN_LEN) -> str:
    """كلمة عشوائية من secrets — مولّد ملائم للتعمية لا random."""
    return "".join(secrets.choice(GEN_ALPHABET) for _ in range(length))


def set_var(text: str, key: str, value: str) -> str:
    """يستبدل قيمة المتغيّر إن وُجد، أو يضيفه في النهاية."""
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    if pattern.search(text):
        return pattern.sub(f"{key}={value}", text, count=1)
    return text.rstrip("\n") + f"\n{key}={value}\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="ضبط كلمة مرور المدير")
    ap.add_argument("--generate", action="store_true",
                    help="توليد كلمة قوية داخلياً بلا طباعتها")
    args = ap.parse_args()

    if not os.path.exists(ENV_PATH):
        print(f"خطأ: {ENV_PATH} غير موجود. شغّل الأمر من جذر المشروع.")
        return 1

    if args.generate:
        # لا تُطبع ولا تُعرض — تُكتب في .env مباشرةً.
        pw1 = generate_password()
    else:
        pw1 = getpass.getpass("كلمة مرور المدير الجديدة (16 محرفاً فأكثر): ")
        if len(pw1) < MIN_LEN:
            print(f"خطأ: كلمة المرور قصيرة — المطلوب {MIN_LEN} محرفاً على الأقل.")
            return 1

        pw2 = getpass.getpass("أعد كتابتها للتأكيد: ")
        if pw1 != pw2:
            print("خطأ: الكلمتان غير متطابقتين. لم يتغيّر شيء.")
            return 1

    hashed = bcrypt.hashpw(pw1.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    text = io.open(ENV_PATH, encoding="utf-8").read()
    text = set_var(text, "ADMIN_PASSWORD", pw1)
    text = set_var(text, "ADMIN_PASSWORD_HASH", hashed)
    io.open(ENV_PATH, "w", encoding="utf-8", newline="").write(text)

    print(f"\nتم. كُتب ADMIN_PASSWORD ({len(pw1)} محرفاً) و ADMIN_PASSWORD_HASH في {ENV_PATH}")
    print("أعد تشغيل الخادم ليقرأ القيم الجديدة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
