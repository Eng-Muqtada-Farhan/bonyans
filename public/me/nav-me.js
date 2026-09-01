/**
 * بُنيان — قائمة منطقة صاحب المشروع   سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * قاعدة العزل ١ — لا رابط تصفّح للموقع العام هنا: لا دليل شركات
 *   ولا رئيسية، والشعار يؤدي إلى /me لا إلى /.
 *   الاستثناء الوحيد المصرَّح به هو وجهة الخروج ../login.html.
 *
 * شريط علوي لا قائمة جانبية: ثلاث وجهات لا تحتاج درجاً، وتتّسع
 * في صفّ واحد حتى على ٣٧٥ بكسل. اللوحتان (app و admin) لهما درج
 * لأن لهما تسع وست وجهات.
 */
(function () {
  'use strict';

  if (!document.querySelector('link[data-bn-font]')) {
    var f = document.createElement('link');
    f.rel = 'stylesheet';
    f.dataset.bnFont = '1';
    f.href = 'https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap';
    document.head.appendChild(f);
  }

  var I = {
    folder: '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2.5h9A1.5 1.5 0 0 1 21 10v8.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/>',
    bid:    '<path d="M4 20h16"/><path d="M6 16V9M10 16V5M14 16v-8M18 16v-4"/>',
    chat:   '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>',
    user:   '<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    sun:    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    moon:   '<path d="M20 13.5A8.5 8.5 0 1 1 10.5 4a6.7 6.7 0 0 0 9.5 9.5z"/>',
    logout: '<path d="M9 21H5.5A1.5 1.5 0 0 1 4 19.5v-15A1.5 1.5 0 0 1 5.5 3H9"/><path d="M16 16l4-4-4-4M20 12H9"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 17) + '" height="' + (s || 17) +
      '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* كل الوجهات نسبية داخل /me — لا مسار يغادر السطح */
  var LINKS = [
    { href: 'index.html',    label: 'مشاريعي',       icon: I.folder },
    { href: 'bids.html',     label: 'العروض الواردة', icon: I.bid },
    { href: 'messages.html', label: 'الرسائل',        icon: I.chat }
  ];

  var CSS = `
.bnm-bar{position:sticky;inset-block-start:0;z-index:290;
  border-block-end:1px solid var(--bn-glass-line);font-family:var(--bn-font)}
.bnm-top{max-width:1000px;margin-inline:auto;padding:var(--bn-s3) var(--bn-s5);
  display:flex;align-items:center;gap:var(--bn-s3)}
.bnm-logo{display:inline-flex;align-items:center;gap:8px;min-height:44px;
  text-decoration:none;color:var(--bn-ink);font:700 19px/1 var(--bn-font)}
.bnm-logo b{color:var(--bn-ac)}
.bnm-id{display:inline-flex;align-items:center;gap:7px;min-height:32px;
  padding-inline:12px;border-radius:var(--bn-r-pill);
  background:var(--bn-ac-bg);border:1px solid var(--bn-ac-line);
  color:var(--bn-ac);font:var(--bn-t-cap);white-space:nowrap}
.bnm-sp{flex:1}
.bnm-icon{width:44px;height:44px;display:inline-flex;align-items:center;
  justify-content:center;border:0;background:0;color:var(--bn-ink-2);cursor:pointer;
  border-radius:var(--bn-r-sm);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bnm-icon:hover{color:var(--bn-ac);background:var(--bn-ac-bg)}
.bnm-nav{max-width:1000px;margin-inline:auto;padding:0 var(--bn-s5) var(--bn-s2);
  display:flex;gap:var(--bn-s2);overflow-x:auto;scrollbar-width:none}
.bnm-nav::-webkit-scrollbar{display:none}
.bnm-link{flex:none;display:inline-flex;align-items:center;gap:8px;min-height:44px;
  padding-inline:var(--bn-s4);border-radius:var(--bn-r-pill);text-decoration:none;
  border:1px solid transparent;color:var(--bn-ink-2);font:400 13.5px/1 var(--bn-font);
  white-space:nowrap;
  transition:color var(--bn-fast),background var(--bn-fast),border-color var(--bn-fast)}
.bnm-link:hover{color:var(--bn-ink);background:var(--bn-glass-tint)}
.bnm-link[aria-current="page"]{color:var(--bn-ac);background:var(--bn-ac-bg);
  border-color:var(--bn-ac-line);font-weight:500}
.bnm-link svg{flex:none}
@media(max-width:560px){
  .bnm-top{padding-inline:var(--bn-s4)}
  .bnm-nav{padding-inline:var(--bn-s4)}
  .bnm-logo{font-size:17px}
}
`;

  var PAGE = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function cur(f) { return PAGE === f ? ' aria-current="page"' : ''; }

  function build() {
    var name = '';
    try { name = localStorage.getItem('project_user_name') || ''; } catch (e) {}
    return '<header class="bnm-bar bn-glass">' +
      '<div class="bnm-top">' +
        /* الشعار يؤدي إلى /me لا إلى الموقع العام (§٤ قاعدة ٤) */
        '<a class="bnm-logo" href="index.html">بُ<b>نيان</b></a>' +
        '<span class="bnm-id">' + svg(I.user, 13) +
          (name ? name : 'صاحب مشروع') + '</span>' +
        '<span class="bnm-sp"></span>' +
        '<button class="bnm-icon" type="button" data-bnm-theme aria-label="تبديل السمة"></button>' +
        '<button class="bnm-icon" type="button" data-bnm-out aria-label="خروج">' + svg(I.logout) + '</button>' +
      '</div>' +
      '<nav class="bnm-nav">' + LINKS.map(function (l) {
        return '<a class="bnm-link" href="' + l.href + '"' + cur(l.href) + '>' +
          svg(l.icon, 16) + '<span>' + l.label + '</span></a>';
      }).join('') + '</nav>' +
    '</header>';
  }

  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bnm-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wire(root) {
    root.querySelector('[data-bnm-theme]').addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintTheme();
    });
    root.querySelector('[data-bnm-out]').addEventListener('click', function () {
      ['bn_token', 'project_user_id', 'project_user_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      /* الكعكة HttpOnly فيمسحها الخادم؛ keepalive حتى يكتمل
         الطلب رغم مغادرة الصفحة. */
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      /* استثناء مُصرَّح به: العزل يحكم الجلسة لا نهايتها. */
      location.replace('../login.html');
    });
  }

  function mount() {
    if (!document.getElementById('bnm-style')) {
      var s = document.createElement('style');
      s.id = 'bnm-style';
      s.textContent = CSS;
      document.head.appendChild(s);
    }
    var host = document.getElementById('bn-nav');
    if (!host) {
      host = document.createElement('div');
      host.id = 'bn-nav';
      document.body.insertBefore(host, document.body.firstChild);
    }
    host.innerHTML = build();
    paintTheme();
    wire(host);
  }

  window.BunyanNavMe = { mount: mount, surface: 'me' };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
