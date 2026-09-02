"""
كتابة RESEND_API_KEY في .env — بلا مرور عبر أي محادثة
═══════════════════════════════════════════════════════════════

    python set_mail_key.py

يُقرأ المفتاح من الطرفية بـ getpass فلا يظهر على الشاشة ولا يدخل
سجلّ الأوامر ولا نافذة محادثة. يُطبع طوله فقط للتأكيد.

نظيره set_admin_password.py لكلمة مرور الإدارة.
"""
import getpass
import io
import os
import re
import shutil
import sys

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
KEY = "RESEND_API_KEY"


def set_var(text: str, name: str, value: str) -> str:
    """
    يستبدل كل أسطر المتغيّر أو يضيفه في النهاية.

    «كل الأسطر» مقصودة: ملفّ فيه المفتاح مرّتين يقرأ الأخير،
    فيصير التعديل الظاهر بلا أثر — وهو عطب يصعب رؤيته.
    """
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(name) + r"[ \t]*=.*$")
    line = f"{name}={value}"
    if pattern.search(text):
        return pattern.sub(line, text)
    sep = "" if text.endswith("\n") else "\n"
    return text + sep + line + "\n"


def main() -> int:
    if not os.path.exists(ENV_PATH):
        print(f"لا يوجد ملفّ .env في {ENV_PATH}")
        return 1

    print("الصق مفتاح Resend. لن يظهر أثناء الكتابة.")
    key = getpass.getpass("RESEND_API_KEY: ").strip()

    if not key:
        print("لم تُدخل شيئاً. لم يتغيّر شيء.")
        return 1
    if not key.startswith("re_"):
        # مفاتيح Resend تبدأ بـ re_ — الفحص يمنع لصق قيمة خاطئة
        # تُكتشف لاحقاً برسالة لم تصل بلا سبب ظاهر.
        print("هذا لا يبدو مفتاح Resend (يجب أن يبدأ بـ re_). لم يتغيّر شيء.")
        return 1
    if len(key) < 20:
        print("المفتاح أقصر من المتوقّع — تأكّد أنك نسخته كاملاً. لم يتغيّر شيء.")
        return 1

    # نسخة احتياطية قبل الكتابة — .env ليس في Git فلا رجعة بدونها
    shutil.copyfile(ENV_PATH, ENV_PATH + ".bak")

    text = io.open(ENV_PATH, encoding="utf-8-sig").read()
    text = set_var(text, KEY, key)
    io.open(ENV_PATH, "w", encoding="utf-8", newline="\n").write(text)

    # تحقّق من القرص لا من الذاكرة
    back = io.open(ENV_PATH, encoding="utf-8-sig").read()
    ok = any(ln.strip().startswith(KEY + "=") and ln.strip().endswith(key)
             for ln in back.split("\n"))

    print(f"\nكُتب {KEY} ({len(key)} محرفاً) في .env")
    print("تحقّق من القرص:", "نجح" if ok else "فشل — راجع الملفّ")
    print("نسخة احتياطية: .env.bak")
    print("\nأعد تشغيل الخادم ليقرأ القيمة الجديدة.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
