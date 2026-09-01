/**
 * بُنيان — قسم أمان الحساب (بريد + كلمة مرور)
 * ═══════════════════════════════════════════════════════════════
 * المرجع: MAIL-TEXTS.md
 *
 * يُركَّب في app/settings.html و me/settings.html معاً. نسختان من
 * هذا النموذج تفترقان — وأخطر ما يفترق نموذجُ تغيير بريد.
 *
 * الاستعمال:
 *   BunyanSecurity.mount(el, { api, errText, toast, svg, icons });
 * حيث api هو نداء الشبكة المصادَق عليه في نواة السطح — فلا نواة
 * ثالثة للمصادقة.
 */
(function () {
  'use strict';

  var CSS = `
.sec-row{display:flex;align-items:center;justify-content:space-between;gap:var(--bn-s4);
  flex-wrap:wrap;padding:var(--bn-s4) var(--bn-s5);border-radius:var(--bn-r-lg);
  margin-block-end:var(--bn-s2)}
.sec-b{min-width:0}
.sec-t{font:500 14px/1.4 var(--bn-font)}
.sec-d{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:4px;
  line-height:1.7;max-width:54ch}
.sec-v{font:400 13.5px/1.4 var(--bn-mono);color:var(--bn-ink-2);direction:ltr;text-align:end}
.sec-form{padding:var(--bn-s5);border-radius:var(--bn-r-lg);
  margin-block-end:var(--bn-s2)}
.sec-form h3{font:600 14.5px/1.4 var(--bn-font);margin:0 0 var(--bn-s2)}
.sec-form p.note{font:var(--bn-t-cap);color:var(--bn-ink-3);margin:0 0 var(--bn-s4);
  line-height:1.75;max-width:56ch}
.sec-fr{margin-block-end:var(--bn-s3)}
.sec-fr label{display:block;font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-end:6px}
.sec-fr input{width:100%;min-height:44px;padding:11px var(--bn-s4);
  border:1px solid var(--bn-line);border-radius:var(--bn-r);background:var(--bn-bg);
  color:var(--bn-ink);font:400 14px/1.5 var(--bn-font)}
.sec-fr input:focus{outline:none;border-color:var(--bn-ac)}
.sec-end{display:flex;justify-content:flex-end;margin-block-start:var(--bn-s4)}
.sec-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;
  border-radius:var(--bn-r-pill);font:var(--bn-t-cap);white-space:nowrap}
.sec-tag-on{background:var(--bn-ac-bg);color:var(--bn-ac);border:1px solid var(--bn-ac-line)}
.sec-tag-off{background:transparent;color:var(--bn-ink-3);border:1px solid var(--bn-line)}
`;

  function injectCSS() {
    if (document.getElementById('bn-sec-style')) return;
    var s = document.createElement('style');
    s.id = 'bn-sec-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /**
   * @param el   الحاوية
   * @param ctx  { api, errText, toast, svg, icons, me }
   *             me: { email, is_email_verified }
   */
  function mount(el, ctx) {
    injectCSS();
    var api = ctx.api, errText = ctx.errText, toast = ctx.toast;
    var svg = ctx.svg, I = ctx.icons;

    function render(me) {
      var verified = Boolean(me.is_email_verified);
      el.innerHTML =
        /* ── البريد الحالي وحالته ── */
        '<div class="sec-row bn-solid">' +
          '<div class="sec-b"><div class="sec-t">البريد الحالي</div>' +
            '<div class="sec-d">' + (verified
              ? 'مُفعَّل — يصلك عليه رابط الاستعادة وتنبيهات الأمان.'
              : 'غير مُفعَّل. فعّله لتصلك تنبيهات الأمان ورابط الاستعادة.') +
            '</div></div>' +
          '<div style="text-align:end">' +
            '<div class="sec-v">' + esc(me.email || '—') + '</div>' +
            '<div style="margin-block-start:6px"><span class="sec-tag ' +
              (verified ? 'sec-tag-on' : 'sec-tag-off') + '">' +
              (verified ? 'مُفعَّل' : 'غير مُفعَّل') + '</span></div>' +
          '</div>' +
        '</div>' +
        (verified ? '' :
          '<div class="sec-row bn-solid">' +
            '<div class="sec-b"><div class="sec-t">إعادة إرسال رسالة التفعيل</div>' +
            '<div class="sec-d">تصل إلى بريدك الحالي، والرابط صالح ٢٤ ساعة.</div></div>' +
            '<button class="bn-btn bn-btn-ghost" type="button" data-resend>إرسال</button>' +
          '</div>') +

        /* ── تغيير كلمة المرور ── */
        '<div class="sec-form bn-solid">' +
          '<h3>تغيير كلمة المرور</h3>' +
          '<p class="note">نطلب كلمتك الحالية: رمز جلسة مسروق وحده لا يكفي لتغييرها.</p>' +
          '<form data-pw>' +
            '<div class="sec-fr"><label for="secCur">كلمة المرور الحالية</label>' +
              '<input id="secCur" type="password" required dir="ltr" autocomplete="current-password"></div>' +
            '<div class="sec-fr"><label for="secNew">الجديدة (٨ محارف على الأقل)</label>' +
              '<input id="secNew" type="password" required dir="ltr" minlength="8" autocomplete="new-password"></div>' +
            '<div class="sec-fr"><label for="secNew2">تأكيد الجديدة</label>' +
              '<input id="secNew2" type="password" required dir="ltr" autocomplete="new-password"></div>' +
            '<div class="sec-end"><button class="bn-btn" type="submit">حفظ كلمة المرور</button></div>' +
          '</form>' +
        '</div>' +

        /* ── تغيير البريد ── */
        '<div class="sec-form bn-solid">' +
          '<h3>تغيير البريد</h3>' +
          '<p class="note">يصل رابط تأكيد إلى العنوان الجديد، وتنبيه إلى العنوان الحالي. ' +
            'لا يتغيّر شيء قبل التأكيد.</p>' +
          '<form data-em>' +
            '<div class="sec-fr"><label for="secEmail">البريد الجديد</label>' +
              '<input id="secEmail" type="email" required dir="ltr" autocomplete="email"></div>' +
            '<div class="sec-fr"><label for="secEmailPw">كلمة المرور الحالية</label>' +
              '<input id="secEmailPw" type="password" required dir="ltr" autocomplete="current-password"></div>' +
            '<div class="sec-end"><button class="bn-btn" type="submit">إرسال رابط التأكيد</button></div>' +
          '</form>' +
        '</div>';

      var rs = el.querySelector('[data-resend]');
      if (rs) rs.onclick = async function () {
        var b = this;
        b.disabled = true; b.textContent = 'جارٍ الإرسال...';
        try {
          var d = await api('/auth/resend-verification', { method: 'POST' });
          toast(d && d.message ? d.message : 'أُرسلت رسالة التفعيل.');
        } catch (e) { toast(errText(e), 'err'); }
        finally { b.disabled = false; b.textContent = 'إرسال'; }
      };

      el.querySelector('[data-pw]').onsubmit = async function (e) {
        e.preventDefault();
        var cur = el.querySelector('#secCur').value;
        var nw  = el.querySelector('#secNew').value;
        var nw2 = el.querySelector('#secNew2').value;
        if (nw.length < 8) { toast('كلمة المرور ٨ محارف على الأقل.', 'err'); return; }
        if (nw !== nw2)    { toast('الكلمتان غير متطابقتين.', 'err'); return; }
        var b = this.querySelector('button');
        b.disabled = true; b.textContent = 'جارٍ الحفظ...';
        try {
          await api('/auth/change-password', {
            method: 'POST', body: { current_password: cur, new_password: nw }
          });
          this.reset();
          toast('غُيّرت كلمة المرور.');
        } catch (err) { toast(errText(err), 'err'); }
        finally { b.disabled = false; b.textContent = 'حفظ كلمة المرور'; }
      };

      el.querySelector('[data-em]').onsubmit = async function (e) {
        e.preventDefault();
        var b = this.querySelector('button');
        b.disabled = true; b.textContent = 'جارٍ الإرسال...';
        try {
          var d = await api('/auth/change-email', {
            method: 'POST', body: {
              new_email: el.querySelector('#secEmail').value.trim(),
              password:  el.querySelector('#secEmailPw').value
            }
          });
          this.reset();
          toast(d && d.message ? d.message : 'أُرسل رابط التأكيد إلى بريدك الجديد.');
        } catch (err) { toast(errText(err), 'err'); }
        finally { b.disabled = false; b.textContent = 'إرسال رابط التأكيد'; }
      };
    }

    /* الحالة من /auth/me — المصدر الوحيد لبريد المستخدم وحالته */
    api('/auth/me').then(render).catch(function (e) {
      el.innerHTML = '<div class="sec-row bn-solid"><div class="sec-b">' +
        '<div class="sec-t">تعذّر تحميل بيانات الحساب</div>' +
        '<div class="sec-d">' + esc(errText(e)) + '</div></div>' +
        '<button class="bn-btn bn-btn-ghost" type="button" data-retry>إعادة المحاولة</button></div>';
      el.querySelector('[data-retry]').onclick = function () { mount(el, ctx); };
    });
  }

  window.BunyanSecurity = { mount: mount };
})();
