"""
إصلاح RESEND_API_KEY المكرّر في .env — بلا لصق ولا تحرير يدوي
═══════════════════════════════════════════════════════════════

    python fix_key.py

المفتاح في .env صحيح لكنه مكتوب مرتين متتاليتين (لصق مزدوج في
getpass، وهو غير مرئي لأنه لا يعرض شيئاً).

السكربت يحذف النسخة الثانية فقط. لا يطبع المفتاح أبداً — الطول وحده.
ولا يكتب شيئاً إن لم تكن القيمة تكراراً بسيطاً مؤكَّداً.
"""
import io
import os
import re
import shutil
import sys

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
KEY = "RESEND_API_KEY"
PATTERN = re.compile(r"(?m)^[ \t]*" + KEY + r"[ \t]*=(.*)$")


def main() -> int:
    if not os.path.exists(ENV_PATH):
        print("لا يوجد ملفّ .env بجانب هذا السكربت.")
        return 1

    text = io.open(ENV_PATH, encoding="utf-8-sig").read()
    m = PATTERN.search(text)
    if not m:
        print(KEY + " غير موجود في .env — شغّل set_mail_key.py أولاً.")
        return 1

    value = m.group(1).strip()

    # سليم أصلاً
    if value.count("re_") == 1 and value.startswith("re_"):
        print(KEY + " سليم بالفعل (" + str(len(value)) + " محرفاً). لم يتغيّر شيء.")
        return 0

    half = len(value) // 2
    first, second = value[:half], value[half:]

    # لا أخمّن: أكتب فقط إن كانت القيمة نصفين متطابقين تماماً
    if len(value) % 2 != 0 or first != second:
        print("القيمة ليست تكراراً بسيطاً — لن أخمّن ولن أكتب شيئاً.")
        print("الطول: " + str(len(value)) + " · عدد re_ فيها: " + str(value.count("re_")))
        print("احذف سطر " + KEY + " من .env وشغّل set_mail_key.py من جديد.")
        return 1

    if not first.startswith("re_"):
        print("النصف الأول لا يبدأ بـ re_ — لن أكتب شيئاً.")
        return 1

    shutil.copyfile(ENV_PATH, ENV_PATH + ".bak2")
    fixed = text[:m.start(1)] + first + text[m.end(1):]
    io.open(ENV_PATH, "w", encoding="utf-8", newline="\n").write(fixed)

    # تحقّق من القرص لا من الذاكرة
    back = io.open(ENV_PATH, encoding="utf-8-sig").read()
    m2 = PATTERN.search(back)
    ok = bool(m2) and m2.group(1).strip() == first and first.count("re_") == 1

    print("")
    print("حُذفت النسخة المكرّرة. " + KEY + " صار " + str(len(first)) + " محرفاً.")
    print("تحقّق من القرص: " + ("نجح" if ok else "فشل — الأصل في .env.bak2"))
    print("نسخة احتياطية: .env.bak2")
    print("")
    print("أعد تشغيل الخادم ليقرأ القيمة الجديدة.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
