/**
 * بُنيان — حارس التوجيه (الواجهة)
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ قاعدتا ٢ و٣
 *
 * ⚠️ هذا الحارس للتجربة لا للأمان. «الحارس في الواجهة وحده
 *    يتجاوزه سطر في المتصفح» — الحماية الحقيقية على الخادم
 *    (require_company / require_user / require_admin في main.py،
 *    وحارس المسارات المسوَّرة أمام /app و /admin).
 *
 * الاستعمال — في <head> قبل أي رسم، وقبل ملف القائمة:
 *   <script src="/guard.js" data-require="company"></script>
 *   <script src="/guard.js" data-require="user"></script>
 *   <script src="/guard.js" data-require="admin"></script>
 *
 * القواعد:
 *   شركة        ← /app     · صاحب مشروع ← /me   · مدير ← /admin
 *   من لا جلسة له على سطح مسوَّر ← /login.html?role=…&next=…
 *   من دخل سطحاً ليس له ← يُعاد إلى سطحه هو.
 */
(function () {
  'use strict';

  var HOME = { company: '/app/index.html', user: '/me/index.html', admin: '/admin/index.html' };
  var LOGIN_ROLE = { company: 'company', user: 'client' };

  function payload(tok) {
    if (!tok || typeof tok !== 'string') return null;
    var parts = tok.split('.');
    if (parts.length < 2) return null;
    try {
      var p = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
      if (p.exp && Date.now() / 1000 >= p.exp) return null;   // منتهٍ
      return p;
    } catch (e) { return null; }
  }
  function get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

  /** الدور الفعلي من التخزين — أول رمز صالح، بترتيب أضيق الصلاحيات أولاً. */
  function currentRole() {
    var a = payload(get('admin_token') || get('token'));
    if (a && a.sub === 'admin') return 'admin';
    var c = payload(get('COMPANY_TOKEN'));
    if (c) return 'company';
    var u = payload(get('project_user_token'));
    if (u) return 'user';
    return null;
  }

  /* تُصدَّر للصفحات العامّة التي تحتاج معرفة الدور دون أن تُحرَس:
     صفحة تعرض زر «أضف مشروعك» تحتاج أن تعرف إن كان للزائر جلسة.
     لا تُغيّر سلوك الحارس نفسه. */
  window.BunyanGuard = { role: currentRole, token: get, home: HOME };

  function go(url) { location.replace(url); }

  var need = (document.currentScript && document.currentScript.dataset.require) || '';
  var role = currentRole();

  if (!need) return;                 // الصفحة لا تشترط دوراً

  if (!role) {
    /* لا جلسة — إلى الدخول، مع حفظ الوجهة للعودة إليها بعده */
    var back = location.pathname + location.search;
    var q = '/login.html';
    if (LOGIN_ROLE[need]) q += '?role=' + LOGIN_ROLE[need] + '&next=' + encodeURIComponent(back);
    go(q);
    return;
  }

  if (role !== need) {
    /* دخل سطحاً ليس له — يُعاد إلى سطحه هو، لا إلى الرئيسية */
    go(HOME[role] || '/index.html');
    return;
  }

  /* مطابق — تمرّ الصفحة. يعمل الحارس في <head> فيُنفَّذ التحويل
     قبل رسم الجسم، فلا وميض ولا حاجة لإخفاء مؤقّت. */
  window.BunyanGuard = { role: role, home: HOME[role] };
})();
