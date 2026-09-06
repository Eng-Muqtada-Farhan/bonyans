/**
 * بُنيان — قائمة لوحة الإدارة  سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * قاعدة العزل ١ — لا رابط تصفّح للموقع العام في هذا الملف،
 *    والشعار يؤدي إلى /admin لا إلى /.
 *
 *    الاستثناء الوحيد — مُصرَّح به من صاحب المشروع ٣٠ آب ٢٠٢٦ —
 *    هو وجهة زر الخروج: ../login.html.
 *
 * بطاقة الهوية هنا «أسود معكوس» (.bn-id-admin) — أوضح تمييز
 * في النظام، لأن الخطأ في سطح الإدارة هو الأغلى (§٥).
 *
 * التركيب: <script src="nav-admin.js"></script>
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
    grid:     '<rect x="3" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.2"/>',
    inbox:    '<path d="M3 13.5h4l1.5 2.5h7L17 13.5h4"/><path d="M4.6 5.2 3 13.5v4A1.5 1.5 0 0 0 4.5 19h15a1.5 1.5 0 0 0 1.5-1.5v-4l-1.6-8.3A1.5 1.5 0 0 0 17.9 4H6.1a1.5 1.5 0 0 0-1.5 1.2z"/>',
    building: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2"/>',
    market:   '<path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3z"/><path d="M8.5 8V6a3.5 3.5 0 0 1 7 0v2"/>',
    card:     '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    flag:     '<path d="M5 21V4"/><path d="M5 5h10.5l-1.4 3.2L15.5 12H5"/>',
    users:    '<circle cx="9" cy="8" r="3.2"/><path d="M2.8 19.5a6.2 6.2 0 0 1 12.4 0"/><path d="M16 5.2a3.2 3.2 0 0 1 0 5.9"/><path d="M17.8 14.4a5.6 5.6 0 0 1 3.4 5.1"/>',
    shield:   '<path d="M12 3l7.5 3v5.4c0 4.5-3 8.2-7.5 9.6-4.5-1.4-7.5-5.1-7.5-9.6V6z"/>',
    scroll:   '<path d="M5 4.5h11a1.5 1.5 0 0 1 1.5 1.5v13H6.5A1.5 1.5 0 0 1 5 17.5z"/><path d="M17.5 19.5H19a1.5 1.5 0 0 0 1.5-1.5V9h-3"/><path d="M8.5 8.5h5M8.5 12h5"/>',
    sun:      '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    moon:     '<path d="M20 13.5A8.5 8.5 0 1 1 10.5 4a6.7 6.7 0 0 0 9.5 9.5z"/>',
    logout:   '<path d="M9 21H5.5A1.5 1.5 0 0 1 4 19.5v-15A1.5 1.5 0 0 1 5.5 3H9"/><path d="M16 16l4-4-4-4M20 12H9"/>',
    menu:     '<path d="M4 7h16M4 12h16M4 17h16"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 17) + '" height="' + (s || 17) +
           '" fill="none" stroke="currentColor" stroke-width="1.6" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* كل الوجهات نسبية داخل /admin — لا مسار يغادر السطح. */
  var BLOCKS = [
    { items: [
      { href: 'index.html', label: 'لوحة القيادة', icon: I.grid }
    ]},
    { title: 'المراجعة', items: [
      { href: 'requests.html',  label: 'طلبات الاعتماد', icon: I.inbox },
      { href: 'companies.html', label: 'الشركات',        icon: I.building },
      { href: 'projects.html',  label: 'المشاريع',       icon: I.market },
      { href: 'subscription-assign.html', label: 'إسناد باقة', icon: I.card }
    ]},
    { title: 'الإشراف', items: [
      { href: 'reports.html', label: 'البلاغات',   icon: I.flag },
      { href: 'users.html',   label: 'المستخدمون', icon: I.users }
    ]},
    { title: 'النظام', items: [
      { href: 'audit.html', label: 'سجل التدقيق', icon: I.scroll }
    ]}
  ];

  var CSS = `
.bnd-bar{position:fixed;inset-block-start:0;inset-inline:0;z-index:290;height:56px;
  display:none;align-items:center;gap:var(--bn-s3);padding-inline:var(--bn-s4);
  font-family:var(--bn-font);border-block-end:1px solid var(--bn-glass-line)}
.bnd-side{position:fixed;inset-block:0;inset-inline-start:0;z-index:300;width:244px;
  display:flex;flex-direction:column;font-family:var(--bn-font);
  border-inline-end:1px solid var(--bn-glass-line);transition:transform var(--bn-mid)}
.bnd-head{padding:var(--bn-s5) var(--bn-s5) var(--bn-s4)}
.bnd-logo{display:inline-flex;align-items:center;gap:8px;text-decoration:none;
  min-height:44px;
  color:var(--bn-ink);font:700 19px/1 var(--bn-font)}
.bnd-logo b{color:var(--bn-ac)}
.bnd-id{margin-block-start:var(--bn-s3)}
.bnd-nav{flex:1;overflow-y:auto;padding:0 var(--bn-s3) var(--bn-s4)}
.bnd-block{padding-block:var(--bn-s3)}
.bnd-block+.bnd-block{border-block-start:1px solid var(--bn-line-soft)}
.bnd-title{font:var(--bn-t-cap);color:var(--bn-ink-3);letter-spacing:.04em;
  padding-inline:var(--bn-s3);margin-block-end:6px}
.bnd-count{margin-inline-start:auto;min-width:22px;height:20px;padding-inline:6px;
  border-radius:999px;background:var(--bn-ac);color:var(--bn-ac-on);
  font:600 11px/20px var(--bn-mono);text-align:center;flex:none}
.bnd-link[aria-current="page"] .bnd-count{background:var(--bn-ac);color:var(--bn-ac-on)}
.bnd-link{display:flex;align-items:center;gap:10px;min-height:44px;
  padding-inline:var(--bn-s3);border-radius:var(--bn-r-sm);text-decoration:none;
  color:var(--bn-ink-2);font:400 13.5px/1 var(--bn-font);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bnd-link:hover{color:var(--bn-ink);background:var(--bn-glass-tint)}
.bnd-link[aria-current="page"]{color:var(--bn-ac);background:var(--bn-ac-bg);font-weight:500}
.bnd-link svg{flex:none}
.bnd-foot{display:flex;align-items:center;gap:var(--bn-s2);
  padding:var(--bn-s3) var(--bn-s4);border-block-start:1px solid var(--bn-line-soft)}
.bnd-icon{width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;
  border:0;background:0;color:var(--bn-ink-2);cursor:pointer;border-radius:var(--bn-r-sm);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bnd-icon:hover{color:var(--bn-ac);background:var(--bn-ac-bg)}
.bnd-scrim{position:fixed;inset:0;z-index:295;background:var(--bn-scrim);
  opacity:0;pointer-events:none;transition:opacity var(--bn-mid)}

body{padding-inline-start:244px}

@media(max-width:900px){
  body{padding-inline-start:0;padding-block-start:56px}
  .bnd-bar{display:flex}
  .bnd-side{transform:translateX(100%);box-shadow:var(--bn-sh-3)}
  [dir="ltr"] .bnd-side{transform:translateX(-100%)}
  .bnd-side.is-open{transform:none}
  .bnd-scrim.is-open{opacity:1;pointer-events:auto}
}
`;

  var PAGE = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function cur(f) { return PAGE === f ? ' aria-current="page"' : ''; }

  function build() {
    var nav = BLOCKS.map(function (b) {
      var items = b.items.map(function (it) {
        /* العدّاد يُملأ لاحقاً من /admin/system-status عبر
           AdminCore.counts() — لا رقم قبل وصول بياناته. */
        return '<a class="bnd-link" href="' + it.href + '"' + cur(it.href) + '>' +
               svg(it.icon, 17) + '<span>' + it.label + '</span>' +
               '<span class="bnd-count" data-bnd-count="' + it.href + '" hidden></span></a>';
      }).join('');
      return '<div class="bnd-block">' +
             (b.title ? '<div class="bnd-title">' + b.title + '</div>' : '') +
             items + '</div>';
    }).join('');

    return '' +
      '<div class="bnd-scrim" data-bnd-scrim></div>' +
      '<header class="bnd-bar bn-glass">' +
        '<button class="bnd-icon" type="button" data-bnd-open aria-label="فتح القائمة">' + svg(I.menu, 20) + '</button>' +
        /* الشعار يؤدي إلى لوحة الإدارة — لا إلى الموقع العام (§٤ قاعدة ٤) */
        '<a class="bnd-logo" href="index.html" style="font-size:17px">بُ<b>نيان</b></a>' +
      '</header>' +
      '<aside class="bnd-side bn-glass" data-bnd-side aria-label="تنقّل لوحة الإدارة">' +
        '<div class="bnd-head">' +
          '<a class="bnd-logo" href="index.html">بُ<b>نيان</b></a>' +
          '<div class="bnd-id">' +
            '<span class="bn-id bn-id-admin">' + svg(I.shield, 13) + 'مدير النظام</span>' +
          '</div>' +
        '</div>' +
        '<nav class="bnd-nav">' + nav + '</nav>' +
        '<div class="bnd-foot">' +
          '<button class="bnd-icon" type="button" data-bnd-theme aria-label="تبديل السمة"></button>' +
          '<button class="bnd-icon" type="button" data-bnd-out aria-label="خروج">' + svg(I.logout) + '</button>' +
        '</div>' +
      '</aside>';
  }

  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bnd-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wire(root) {
    var side  = root.querySelector('[data-bnd-side]');
    var scrim = root.querySelector('[data-bnd-scrim]');
    function close() { side.classList.remove('is-open'); scrim.classList.remove('is-open'); }

    root.querySelector('[data-bnd-open]').addEventListener('click', function () {
      side.classList.add('is-open'); scrim.classList.add('is-open');
    });
    scrim.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

    root.querySelector('[data-bnd-theme]').addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintTheme();
    });

    root.querySelector('[data-bnd-out]').addEventListener('click', function () {
      ['bn_token'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      /* الكعكة HttpOnly فلا تمسحها الصفحة — يمسحها الخادم.
         keepalive حتى يكتمل الطلب رغم مغادرة الصفحة. */
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      /* استثناء مُصرَّح به من صاحب المشروع: العزل يحكم الجلسة لا
         نهايتها. من خرج لم يعد مديراً بل زائراً، وصفحة الدخول وجهته. */
      location.replace('../login.html');
    });
  }

  function mount() {
    if (!document.getElementById('bnd-style')) {
      var s = document.createElement('style');
      s.id = 'bnd-style';
      s.textContent = CSS;
      document.head.appendChild(s);
    }
    var host = document.getElementById('bn-nav') || document.getElementById('bn-nav-mount');
    if (!host) {
      host = document.createElement('div');
      document.body.insertBefore(host, document.body.firstChild);
    }
    host.innerHTML = build();
    paintTheme();
    wire(host);
    paintCounts(host);
  }

  /* عدّادات الطوابير — رقم حقيقي من /admin/system-status، ويبقى
     مخفياً حين يكون صفراً: شارة «٠» ضجيج لا خبر. */
  function paintCounts(host) {
    if (!window.AdminCore || !window.AdminCore.counts) return;
    window.AdminCore.counts().then(function (c) {
      Object.keys(c).forEach(function (href) {
        var el = host.querySelector('[data-bnd-count="' + href + '"]');
        if (!el) return;
        if (c[href] > 0) { el.textContent = c[href]; el.hidden = false; }
        else { el.hidden = true; }
      });
    }).catch(function () {});
  }

  window.BunyanNavAdmin = { mount: mount, surface: 'admin', refreshCounts: function () {
    var host = document.getElementById('bn-nav') || document.body;
    paintCounts(host);
  }};
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
