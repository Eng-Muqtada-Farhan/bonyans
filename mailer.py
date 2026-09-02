"""
بُنيان — إرسال البريد
═══════════════════════════════════════════════════════════════
المرجع: MAIL-TEXTS.md — النصوص والقيود وقواعد الإرسال.

دالّة إرسال واحدة. كل رسالة HTML معها نسخة نصّية (بعض العملاء
يحجب HTML). الفشل يُسجَّل ويُعاد False — ولا تُدّعى نجاحاً أبداً:
«لا تخبر المستخدم أرسلنا إن لم تُرسَل».

قوالب الرسائل الأربع في نهاية الملف، نصوصها منقولة حرفياً من
MAIL-TEXTS.md ولا تُغيَّر بلا موافقة.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

log = logging.getLogger("bunyan.mail")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
# onboarding@resend.dev هو مرسِل Resend التجريبي: لا يصل إلا بريد
# صاحب الحساب. بوابة نشر في SCOPE.md تُلزم بتبديله بنطاق موثَّق.
MAIL_FROM      = os.getenv("MAIL_FROM", "onboarding@resend.dev")
SUPPORT_EMAIL  = os.getenv("SUPPORT_EMAIL", MAIL_FROM)
BASE_URL       = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

RESEND_ENDPOINT = "https://api.resend.com/emails"

BRONZE = "#96703C"   # اللون الوحيد المسموح في البريد (MAIL-TEXTS.md)


def mail_enabled() -> bool:
    return bool(RESEND_API_KEY)


def send(to: str, subject: str, text: str, html: str) -> bool:
    """
    يُرسل رسالة واحدة. True عند القبول، False عند أي فشل.

    لا يرفع استثناءً: المسار الذي يستدعيه لا يجوز أن ينهار لأن
    مزوّد البريد تعطّل — لكنّه أيضاً لا يجوز أن يقول «أرسلنا».
    """
    if not mail_enabled():
        log.error("[mail] RESEND_API_KEY غير مضبوط — لم تُرسَل الرسالة إلى %s (%s)",
                  _mask(to), subject)
        return False
    try:
        r = httpx.post(
            RESEND_ENDPOINT,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                     "Content-Type": "application/json"},
            json={"from": MAIL_FROM, "to": [to], "subject": subject,
                  "text": text, "html": html},
            timeout=15.0,
        )
    except Exception as e:                                   # noqa: BLE001
        log.error("[mail] تعذّر الاتصال بمزوّد البريد لإرسال «%s» إلى %s: %s",
                  subject, _mask(to), e)
        return False

    if r.status_code >= 400:
        # نصّ الخطأ من المزوّد يُسجَّل كما هو — بلا تخمين للسبب
        log.error("[mail] رفض المزوّد الرسالة «%s» إلى %s — %s %s",
                  subject, _mask(to), r.status_code, r.text[:400])
        return False

    log.info("[mail] أُرسلت «%s» إلى %s", subject, _mask(to))
    return True


def _mask(email: str) -> str:
    """لا يُكتب عنوان كامل في السجلّات."""
    e = str(email or "")
    if "@" not in e:
        return "***"
    name, _, dom = e.partition("@")
    return (name[:2] + "***@" + dom) if len(name) > 2 else ("***@" + dom)


# ══════════════════════════════════════════════════════════════
# القالب — قيود البريد الإلكتروني (MAIL-TEXTS.md)
#   أنماط داخل السطر · جداول للتخطيط · خطوط النظام ·
#   ٦٠٠ بكسل · dir=rtl على كل خلية · بلا صور · بلا وضع ليلي
# ══════════════════════════════════════════════════════════════

_FONT = "Tahoma, Arial, sans-serif"


def _esc(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _button(url: str, label: str) -> str:
    return f"""
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center">
        <tr>
          <td align="center" bgcolor="{BRONZE}" style="border-radius:8px;">
            <a href="{_esc(url)}"
               style="display:inline-block;padding:14px 32px;font-family:{_FONT};
                      font-size:15px;font-weight:bold;color:#ffffff;text-decoration:none;">
              {_esc(label)}
            </a>
          </td>
        </tr>
      </table>"""


def _shell(body_rows: str) -> str:
    """إطار الرسالة — جدول ٦٠٠ بكسل، أسود على أبيض."""
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body dir="rtl" style="margin:0;padding:0;background-color:#f4f4f4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:#f4f4f4;">
  <tr><td align="center" style="padding:24px 12px;">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
           style="width:600px;max-width:600px;background-color:#ffffff;border-radius:10px;">
      <tr><td dir="rtl" align="right"
              style="padding:28px 32px 8px;font-family:{_FONT};font-size:20px;
                     font-weight:bold;color:#1d1a15;">
        بُ<span style="color:{BRONZE};">نيان</span>
      </td></tr>
      {body_rows}
      <tr><td dir="rtl" align="right"
              style="padding:8px 32px 28px;font-family:{_FONT};font-size:12px;
                     color:#8a8378;border-top:1px solid #eeeeee;padding-top:16px;">
        بُنيان · حيث تلتقي المشاريع بالشركات الموثوقة
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _para(html: str, size: int = 15, color: str = "#3a352d") -> str:
    return (f'<tr><td dir="rtl" align="right" style="padding:6px 32px;font-family:{_FONT};'
            f'font-size:{size}px;line-height:1.9;color:{color};">{html}</td></tr>')


def _url_row(url: str) -> str:
    """الرابط نصّاً كاملاً تحت الزر — لمن يحجب عميلُه الأزرار."""
    return (f'<tr><td dir="rtl" align="right" style="padding:14px 32px 6px;font-family:{_FONT};'
            f'font-size:12px;line-height:1.7;color:#8a8378;word-break:break-all;">'
            f'أو انسخ هذا الرابط:<br>'
            f'<span dir="ltr" style="color:{BRONZE};">{_esc(url)}</span></td></tr>')


def _button_row(url: str, label: str) -> str:
    return f'<tr><td align="center" style="padding:20px 32px;">{_button(url, label)}</td></tr>'


# ══════════════════════════════════════════════════════════════
# الرسائل الأربع — النصوص حرفياً من MAIL-TEXTS.md
# ══════════════════════════════════════════════════════════════

def password_reset(to: str, reset_url: str) -> bool:
    subject = "إعادة تعيين كلمة المرور — بُنيان"
    text = f"""مرحباً،

وصلنا طلب لإعادة تعيين كلمة مرور حسابك في بُنيان.

اختر كلمة مرور جديدة من هنا:
{reset_url}

الرابط صالح ٣٠ دقيقة، ويُستخدم مرة واحدة فقط.

إن لم تطلب هذا، تجاهل الرسالة — كلمة مرورك لم تتغيّر، ولا
يحتاج الأمر أي إجراء منك.

—
بُنيان · حيث تلتقي المشاريع بالشركات الموثوقة"""
    html = _shell(
        _para("مرحباً،")
        + _para("وصلنا طلب لإعادة تعيين كلمة مرور حسابك في بُنيان.")
        + _button_row(reset_url, "اختيار كلمة مرور جديدة")
        + _url_row(reset_url)
        + _para("الرابط صالح ٣٠ دقيقة، ويُستخدم مرة واحدة فقط.", 13, "#6b6459")
        + _para("إن لم تطلب هذا، تجاهل الرسالة — كلمة مرورك لم تتغيّر، "
                "ولا يحتاج الأمر أي إجراء منك.", 13, "#6b6459")
    )
    return send(to, subject, text, html)


VERIFY_ACTION = {
    "company": "تقديم عروض على المشاريع",
    "user":    "طرح مشروعك واستقبال العروض",
}


def email_verify(to: str, verify_url: str, role: str) -> bool:
    action = VERIFY_ACTION.get(role, VERIFY_ACTION["user"])
    subject = "فعّل بريدك — بُنيان"
    text = f"""أهلاً بك في بُنيان،

يبقى تفعيل بريدك خطوةً واحدة قبل أن تستطيع {action}.

فعّل بريدك من هنا:
{verify_url}

الرابط صالح ٢٤ ساعة.

إن لم تسجّل في بُنيان، تجاهل الرسالة ولن يُنشأ أي حساب.

—
بُنيان · حيث تلتقي المشاريع بالشركات الموثوقة"""
    html = _shell(
        _para("أهلاً بك في بُنيان،")
        + _para(f"يبقى تفعيل بريدك خطوةً واحدة قبل أن تستطيع {_esc(action)}.")
        + _button_row(verify_url, "تفعيل البريد")
        + _url_row(verify_url)
        + _para("الرابط صالح ٢٤ ساعة.", 13, "#6b6459")
        + _para("إن لم تسجّل في بُنيان، تجاهل الرسالة ولن يُنشأ أي حساب.", 13, "#6b6459")
    )
    return send(to, subject, text, html)


def email_change_confirm(to: str, confirm_url: str) -> bool:
    """تُرسَل إلى العنوان الجديد."""
    subject = "أكّد بريدك الجديد — بُنيان"
    text = f"""مرحباً،

طلبت تغيير بريد حسابك في بُنيان إلى هذا العنوان.

أكّد من هنا:
{confirm_url}

الرابط صالح ٣٠ دقيقة.

حتى تؤكّد، يبقى بريدك السابق هو المعتمد ولا يتغيّر شيء.

إن لم تطلب هذا، تجاهل الرسالة.

—
بُنيان"""
    html = _shell(
        _para("مرحباً،")
        + _para("طلبت تغيير بريد حسابك في بُنيان إلى هذا العنوان.")
        + _button_row(confirm_url, "تأكيد البريد الجديد")
        + _url_row(confirm_url)
        + _para("الرابط صالح ٣٠ دقيقة.", 13, "#6b6459")
        + _para("حتى تؤكّد، يبقى بريدك السابق هو المعتمد ولا يتغيّر شيء.", 13, "#6b6459")
        + _para("إن لم تطلب هذا، تجاهل الرسالة.", 13, "#6b6459")
    )
    return send(to, subject, text, html)


def email_change_alert(to: str) -> bool:
    """
    تُرسَل إلى العنوان القديم لحظة الطلب. لا زر فيها.

    إلزامية: من يخترق حساباً أول ما يفعله تغيير البريد ليقفل صاحبه
    خارجاً. هذا التنبيه هو الفرصة الوحيدة ليعرف ويتصرّف.
    """
    subject = "طُلب تغيير بريد حسابك — بُنيان"
    text = f"""مرحباً،

وصلنا طلب لتغيير بريد حسابك في بُنيان إلى عنوان آخر.

لم يتغيّر شيء بعد — التغيير لا يتمّ إلا بتأكيد من العنوان الجديد.

إن كنت أنت من طلب ذلك، تجاهل هذه الرسالة.

إن لم تكن أنت، فقد يكون أحدهم وصل إلى حسابك:
  ١. غيّر كلمة مرورك فوراً
  ٢. راسلنا على {SUPPORT_EMAIL}

—
بُنيان"""
    html = _shell(
        _para("مرحباً،")
        + _para("وصلنا طلب لتغيير بريد حسابك في بُنيان إلى عنوان آخر.")
        + _para("<b>لم يتغيّر شيء بعد</b> — التغيير لا يتمّ إلا بتأكيد من العنوان الجديد.")
        + _para("إن كنت أنت من طلب ذلك، تجاهل هذه الرسالة.", 13, "#6b6459")
        + _para("إن لم تكن أنت، فقد يكون أحدهم وصل إلى حسابك:<br>"
                "١. غيّر كلمة مرورك فوراً<br>"
                f'٢. راسلنا على <span dir="ltr" style="color:{BRONZE};">'
                f"{_esc(SUPPORT_EMAIL)}</span>", 13, "#6b6459")
    )
    return send(to, subject, text, html)


def account_deleted(to: str, purge_date: str) -> bool:
    """
    تأكيد حذف الحساب — آخر رسالة تصل صاحبه.

    تذكر مهلة المحو صراحةً: من حذف حسابه بالخطأ يحتاج أن يعرف
    أن أمامه وقتاً، ومن حذفه عمداً يحتاج أن يعرف متى ينتهي.
    """
    subject = "حُذف حسابك — بُنيان"
    text = f"""مرحباً،

حُذف حسابك في بُنيان بناءً على طلبك.

ما جرى الآن: لم يعد بإمكانك الدخول، وأُزيلت بياناتك الشخصية من
المنصّة.

ما يجري لاحقاً: تُمحى بياناتك نهائياً من قواعدنا في {purge_date}.

ما يبقى ولماذا:
  · سجلّ التدقيق الأمني — مجهَّلاً، اثني عشر شهراً، للحماية القانونية
  · تقييماتك التي كتبتها — مجهَّلة، لأن حذفها يشوّه سمعة قُدِّرت بها شركة
  · رسائلك — في نسخة المستلم، كما في أي محادثة

إن لم تكن أنت من طلب الحذف، راسلنا فوراً على {SUPPORT_EMAIL}.

—
بُنيان"""
    html = _shell(
        _para("مرحباً،")
        + _para("حُذف حسابك في بُنيان بناءً على طلبك.")
        + _para("<b>ما جرى الآن:</b> لم يعد بإمكانك الدخول، وأُزيلت بياناتك "
                "الشخصية من المنصّة.")
        + _para(f"<b>ما يجري لاحقاً:</b> تُمحى بياناتك نهائياً من قواعدنا في "
                f"{_esc(purge_date)}.", 15)
        + _para("<b>ما يبقى ولماذا:</b><br>"
                "· سجلّ التدقيق الأمني — مجهَّلاً، اثني عشر شهراً، للحماية القانونية<br>"
                "· تقييماتك التي كتبتها — مجهَّلة، لأن حذفها يشوّه سمعة قُدِّرت بها شركة<br>"
                "· رسائلك — في نسخة المستلم، كما في أي محادثة", 13, "#6b6459")
        + _para(f'إن لم تكن أنت من طلب الحذف، راسلنا فوراً على '
                f'<span dir="ltr" style="color:{BRONZE};">{_esc(SUPPORT_EMAIL)}</span>.',
                13, "#6b6459")
    )
    return send(to, subject, text, html)
