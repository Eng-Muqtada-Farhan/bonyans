/**
 * بُنيان — ملفّ التنقّل الموحَّد لكل الأسطح الثلاثة
 * ═══════════════════════════════════════════════════════════════
 * يحلّ محلّ nav-public.js وme/nav-me.js وapp/nav-app.js معاً —
 * ثلاث قواعد CSS متباعدة كانت تُنتج شريطاً أعلى في صفحات وأسفل في
 * أخرى على أندرويد بلا سبب مقصود. الآن قاعدة واحدة.
 *
 * سطح المكتب: لا يتغيّر إطلاقاً عن الملفّات الثلاثة القديمة — نفس
 * الشريط العلوي (عام/صاحب مشروع) ونفس القائمة الجانبية (شركة)،
 * حرفياً. التغيير كلّه محصور في الجوّال (@media أدناه).
 *
 * الجوّال: شريط سفلي طائر زجاجي واحد على الأسطح الثلاثة — نفس
 * الشكل والموضع، تختلف أزراره فقط بحسب السطح/الدور:
 *   زائر (عام):        الرئيسية · الشركات · المشاريع · دخول
 *   صاحب مشروع:        الشركات · مشاريعي · العروض · الرسائل · حسابي
 *   شركة (/app):        لوحة القيادة · سوق المشاريع · عروضي ·
 *                       الرسائل · المزيد (لوحة منسدلة بالخمسة الباقية)
 *
 * ⚠️ قاعدة العزل تبقى غير قابلة للتفاوض لسطح الشركة وحده: لا رابط
 *    إلى / ولا إلى /companies.html في أي مكان من كود سطح الشركة
 *    (COMPANY_TABS وCOMPANY_BLOCKS أدناه) — لا في الشريط ولا في
 *    «المزيد». العزل يُرفَع عن سطح المستخدم (/me) فقط: هو مشترٍ لا
 *    بائع، فرابط دليل الشركات في USER_TABS مقصود لا تسرّباً.
 *
 * قاعدة «لا صفحة تفقد طريقها»: كل وجهة كانت في القائمة القديمة
 * (تسع وجهات لسطح الشركة) موجودة إمّا في الشريط السفلي الأساسي أو
 * داخل «المزيد» — لم تُحذف واحدة منها، فقط أُعيد ترتيب الوصول إليها
 * على الجوّال.
 *
 * التركيب: <script src="nav.js"></script> من صفحات الجذر،
 *          <script src="../nav.js"></script> من /app و/me.
 */
(function () {
  'use strict';

  /* ── الخط (مرّة واحدة) ─────────────────────────────────────── */
  if (!document.querySelector('link[data-bn-font]')) {
    var f = document.createElement('link');
    f.rel = 'stylesheet';
    f.dataset.bnFont = '1';
    f.href = 'https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap';
    document.head.appendChild(f);
  }

  /* ── الأيقونات ─────────────────────────────────────────────── */
  var I = {
    home:     '<path d="M3 10.5 12 3l9 7.5"/><path d="M5.5 9.5V21h13V9.5"/>',
    building: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2"/>',
    folder:   '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2.5h9A1.5 1.5 0 0 1 21 10v8a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18z"/>',
    chat:     '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>',
    user:     '<circle cx="12" cy="8" r="3.5"/><path d="M4.5 20a7.5 7.5 0 0 1 15 0"/>',
    sun:      '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    moon:     '<path d="M20 13.5A8.5 8.5 0 1 1 10.5 4a6.7 6.7 0 0 0 9.5 9.5z"/>',
    logout:   '<path d="M9 21H5.5A1.5 1.5 0 0 1 4 19.5v-15A1.5 1.5 0 0 1 5.5 3H9"/><path d="M16 16l4-4-4-4M20 12H9"/>',
    install:  '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 19.5h16"/>',
    grid:     '<rect x="3" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.2"/>',
    image:    '<rect x="3" y="4.5" width="18" height="15" rx="1.5"/><circle cx="8.5" cy="10" r="1.6"/><path d="M21 16l-5-5-9 8.5"/>',
    market:   '<path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3z"/><path d="M8.5 8V6a3.5 3.5 0 0 1 7 0v2"/>',
    tag:      '<path d="M3.5 11.2V4.5a1 1 0 0 1 1-1h6.7a1 1 0 0 1 .7.3l8.3 8.3a1 1 0 0 1 0 1.4l-6.7 6.7a1 1 0 0 1-1.4 0L3.8 11.9a1 1 0 0 1-.3-.7z"/><circle cx="7.8" cy="7.8" r="1.3"/>',
    star:     '<path d="M12 3.6l2.6 5.3 5.8.85-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.2-4.1 5.8-.85z"/>',
    card:     '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    gear:     '<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
    menu:     '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close:    '<path d="M6 6l12 12M18 6L6 18"/>',
    more:     '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 17) + '" height="' + (s || 17) +
           '" fill="none" stroke="currentColor" stroke-width="1.6" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ── تحديد السطح ───────────────────────────────────────────────
     السطحان المسوَّران (/app /me) محميان على الخادم (حارس الأسطح،
     main.py) — الوصول إليهما أصلاً يعني الدور المطابق، فلا حاجة
     لفحص رمز هنا. الموقع العام وحده يحمل حالتَي زائر/صاحب مشروع. */
  var PATH = location.pathname;
  var SURFACE = (PATH === '/app' || PATH.indexOf('/app/') === 0) ? 'company'
    : (PATH === '/me' || PATH.indexOf('/me/') === 0) ? 'user'
    : 'public';

  /* ── حالة الدخول (الموقع العام فقط) ───────────────────────── */
  function jwtValid(tok) {
    if (!tok) return null;
    try {
      var p = JSON.parse(atob(tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return (!p.exp || Date.now() / 1000 < p.exp) ? p : null;
    } catch (e) { return null; }
  }
  function readClientLoggedIn() {
    return !!jwtValid(localStorage.getItem('bn_token'));
  }

  /* ── التثبيت (PWA) — الموقع العام فقط ─────────────────────────
     iOS لا يُطلق beforeinstallprompt إطلاقاً (سفاري لا يدعم التثبيت
     البرمجي) — الزرّ هناك يقود إلى تعليمات install.html. */
  var isStandalone = matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  var isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  var deferredPrompt = null;

  function paintInstallBtn() {
    document.querySelectorAll('[data-bnv-install]').forEach(function (b) {
      b.hidden = isStandalone || !(isIOS || deferredPrompt);
    });
  }
  if (SURFACE === 'public' && !isStandalone) {
    window.addEventListener('beforeinstallprompt', function (e) {
      e.preventDefault();
      deferredPrompt = e;
      paintInstallBtn();
    });
    window.addEventListener('appinstalled', function () {
      deferredPrompt = null;
      isStandalone = true;
      paintInstallBtn();
    });
  }

  /* ── الشريط السفلي الطائر المشترك (الجوّال فقط) ─────────────
     المواصفات حرفية — لا خيارات أنماط هنا، الطائر فقط. */
  var FAB_CSS = `
.bn-fab-bar{position:fixed;inset-block-end:calc(14px + env(safe-area-inset-bottom));
  inset-inline:16px;z-index:340;height:64px;border-radius:22px;display:none;
  align-items:center;justify-content:space-around;
  background:rgba(255,255,255,.62);
  -webkit-backdrop-filter:blur(18px) saturate(1.6);
  backdrop-filter:blur(18px) saturate(1.6);
  box-shadow:0 10px 34px rgba(20,16,8,.16),0 2px 10px rgba(20,16,8,.08)}
@supports not (backdrop-filter: blur(1px)) {
  .bn-fab-bar{background:rgba(250,249,246,.97)}
}
@media(max-width:820px){
  .bn-fab-bar{display:flex}
  body{padding-block-end:calc(64px + 28px + env(safe-area-inset-bottom))}
}
.bn-fab-item{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:2px;height:100%;text-decoration:none;border:0;background:0;cursor:pointer;
  color:#6b675f;font:400 10px/1.15 var(--bn-font,inherit);border-radius:16px}
.bn-fab-item[aria-current="page"],.bn-fab-item.is-active{color:#96703C;background:rgba(150,112,60,.10)}

/* لوحة «المزيد» — منسدلة من الأسفل، زجاجية كالشريط */
.bn-fab-sheet-scrim{position:fixed;inset:0;z-index:345;background:rgba(10,8,4,.32);
  opacity:0;pointer-events:none;transition:opacity .22s}
.bn-fab-sheet-scrim.is-open{opacity:1;pointer-events:auto}
`;

  function buildFab(items) {
    var html = items.map(function (it) {
      if (it.more) {
        return '<button class="bn-fab-item" type="button" data-bn-fab-more aria-label="' + esc(it.label) + '">' +
               svg(it.icon, 20) + '<span>' + esc(it.label) + '</span></button>';
      }
      var current = (PATH === it.href) ? ' aria-current="page"' : '';
      return '<a class="bn-fab-item" href="' + it.href + '"' + current + '>' +
             svg(it.icon, 20) + '<span>' + esc(it.label) + '</span></a>';
    }).join('');
    return '<nav class="bn-fab-bar bn-glass" aria-label="تنقّل الجوّال">' + html + '</nav>';
  }

  /* ══════════════════════════════════════════════════════════════
     سطح الشركة (/app) — قاعدة العزل ١ لا تزال سارية بحرفيّتها:
     لا رابط إلى / ولا إلى /companies.html في أي سطر أدناه.
     ══════════════════════════════════════════════════════════════ */

  /* الكتل التسع كما كانت في nav-app.js تماماً — لا صفحة حُذفت،
     فقط أُعيد تبويب الوصول إليها على الجوّال (البند أدناه). */
  var COMPANY_BLOCKS = [
    { items: [
      { href: 'index.html', label: 'لوحة القيادة', icon: I.grid }
    ]},
    { title: 'الهوية', items: [
      { href: 'profile.html', label: 'ملف شركتي',   icon: I.building },
      { href: 'gallery.html', label: 'معرض الأعمال', icon: I.image }
    ]},
    { title: 'العمل', items: [
      { href: 'market.html',   label: 'سوق المشاريع', icon: I.market },
      { href: 'bids.html',     label: 'عروضي',        icon: I.tag },
      { href: 'messages.html', label: 'الرسائل',      icon: I.chat },
      { href: 'reviews.html',  label: 'التقييمات',    icon: I.star }
    ]},
    { title: 'الحساب', items: [
      { href: 'plan.html',     label: 'الاشتراك',  icon: I.card },
      { href: 'settings.html', label: 'الإعدادات', icon: I.gear }
    ]}
  ];

  /* أربعة أزرار مباشرة + «المزيد» يفتح نفس القائمة الجانبية
     (COMPANY_BLOCKS كاملة، التسع كلّها) كلوحة منسدلة من الأسفل على
     الجوّال — لا رابط عام هنا أيضاً. */
  var COMPANY_TABS = [
    { href: '/app/index.html',    label: 'لوحة القيادة', icon: I.grid },
    { href: '/app/market.html',   label: 'سوق المشاريع', icon: I.market },
    { href: '/app/bids.html',     label: 'عروضي',        icon: I.tag },
    { href: '/app/messages.html', label: 'الرسائل',      icon: I.chat },
    { more: true,                 label: 'المزيد',       icon: I.more }
  ];

  var COMPANY_CSS = `
.bna-bar{position:fixed;inset-block-start:0;inset-inline:0;z-index:290;height:56px;
  display:none;align-items:center;gap:var(--bn-s3);padding-inline:var(--bn-s4);
  font-family:var(--bn-font);border-block-end:1px solid var(--bn-glass-line)}
.bna-side{position:fixed;inset-block:0;inset-inline-start:0;z-index:300;width:244px;
  display:flex;flex-direction:column;font-family:var(--bn-font);
  border-inline-end:1px solid var(--bn-glass-line);transition:transform var(--bn-mid)}
.bna-head{padding:var(--bn-s5) var(--bn-s5) var(--bn-s4)}
.bna-logo{display:inline-flex;align-items:center;gap:8px;text-decoration:none;
  min-height:44px;
  color:var(--bn-ink);font:700 19px/1 var(--bn-font)}
.bna-logo b{color:var(--bn-ac)}
.bna-id{margin-block-start:var(--bn-s3)}
.bna-nav{flex:1;overflow-y:auto;padding:0 var(--bn-s3) var(--bn-s4)}
.bna-block{padding-block:var(--bn-s3)}
.bna-block+.bna-block{border-block-start:1px solid var(--bn-line-soft)}
.bna-title{font:var(--bn-t-cap);color:var(--bn-ink-3);letter-spacing:.04em;
  padding-inline:var(--bn-s3);margin-block-end:6px}
.bna-link{display:flex;align-items:center;gap:10px;min-height:44px;
  padding-inline:var(--bn-s3);border-radius:var(--bn-r-sm);text-decoration:none;
  color:var(--bn-ink-2);font:400 13.5px/1 var(--bn-font);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bna-link:hover{color:var(--bn-ink);background:var(--bn-glass-tint)}
.bna-link[aria-current="page"]{color:var(--bn-ac);background:var(--bn-ac-bg);font-weight:500}
.bna-link svg{flex:none}
.bna-foot{display:flex;align-items:center;gap:var(--bn-s2);
  padding:var(--bn-s3) var(--bn-s4);border-block-start:1px solid var(--bn-line-soft)}
.bna-icon{width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;
  border:0;background:0;color:var(--bn-ink-2);cursor:pointer;border-radius:var(--bn-r-sm);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bna-icon:hover{color:var(--bn-ac);background:var(--bn-ac-bg)}
.bna-scrim{position:fixed;inset:0;z-index:295;background:var(--bn-scrim);
  opacity:0;pointer-events:none;transition:opacity var(--bn-mid)}

body{padding-inline-start:244px}

/* سطح المكتب لا يتغيّر إطلاقاً أعلاه. الجوّال فقط أدناه: الشريط
   العلوي القديم (.bna-bar) يبقى مخفياً — الشريط السفلي الطائر حلّ
   محلّ وظيفته، و«المزيد» يفتح .bna-side نفسها كلوحة منسدلة من
   الأسفل بدل درجٍ ينزلق من الجانب. لا صفحة حُذفت — كل التسع باقية
   داخل .bna-side كما كانت، فقط طريقة العرض على الجوّال تغيّرت. */
@media(max-width:900px){
  body{padding-inline-start:0;padding-block-end:calc(64px + 28px + env(safe-area-inset-bottom))}
  .bna-side{inset-inline:0;inset-block-start:auto;inset-block-end:0;width:auto;
    max-height:75vh;border-radius:20px 20px 0 0;border-inline-end:0;
    border-block-start:1px solid var(--bn-glass-line);
    transform:translateY(100%);box-shadow:var(--bn-sh-3)}
  .bna-side.is-open{transform:none}
  .bna-scrim.is-open{opacity:1;pointer-events:auto}
}
`;

  function buildCompany() {
    var nav = COMPANY_BLOCKS.map(function (b) {
      var items = b.items.map(function (it) {
        return '<a class="bna-link" href="' + it.href + '"' + curRel(it.href) + '>' +
               svg(it.icon, 17) + '<span>' + it.label + '</span></a>';
      }).join('');
      return '<div class="bna-block">' +
             (b.title ? '<div class="bna-title">' + b.title + '</div>' : '') +
             items + '</div>';
    }).join('');

    var name = '';
    try { name = localStorage.getItem('company_name') || ''; } catch (e) {}

    var sideAndBar = '' +
      '<div class="bna-scrim" data-bna-scrim></div>' +
      '<header class="bna-bar bn-glass">' +
        '<button class="bna-icon" type="button" data-bna-open aria-label="فتح القائمة">' + svg(I.menu, 20) + '</button>' +
        '<a class="bna-logo" href="index.html" style="font-size:17px">بُ<b>نيان</b></a>' +
      '</header>' +
      '<aside class="bna-side bn-glass" data-bna-side aria-label="تنقّل لوحة الشركة">' +
        '<div class="bna-head">' +
          '<a class="bna-logo" href="index.html">بُ<b>نيان</b></a>' +
          '<div class="bna-id">' +
            '<span class="bn-id bn-id-company">' + svg(I.building, 13) +
              (name ? esc(name) : 'حساب شركة') +
            '</span>' +
          '</div>' +
        '</div>' +
        '<nav class="bna-nav">' + nav + '</nav>' +
        '<div class="bna-foot">' +
          '<button class="bna-icon" type="button" data-bna-theme aria-label="تبديل السمة"></button>' +
          '<button class="bna-icon" type="button" data-bna-out aria-label="خروج">' + svg(I.logout) + '</button>' +
        '</div>' +
      '</aside>';

    return sideAndBar + buildFab(COMPANY_TABS);
  }

  function paintThemeCompany() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bna-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wireCompany(root) {
    var side  = root.querySelector('[data-bna-side]');
    var scrim = root.querySelector('[data-bna-scrim]');
    function open()  { side.classList.add('is-open');    scrim.classList.add('is-open'); }
    function close() { side.classList.remove('is-open'); scrim.classList.remove('is-open'); }

    var openBtn = root.querySelector('[data-bna-open]');
    if (openBtn) openBtn.addEventListener('click', open);
    var moreBtn = root.querySelector('[data-bn-fab-more]');
    if (moreBtn) moreBtn.addEventListener('click', function () {
      if (side.classList.contains('is-open')) close(); else open();
    });
    scrim.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

    root.querySelector('[data-bna-theme]').addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintThemeCompany();
    });

    root.querySelector('[data-bna-out]').addEventListener('click', function () {
      ['bn_token', 'company_id', 'company_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      /* استثناء مُصرَّح به من صاحب المشروع (٣٠ آب ٢٠٢٦): العزل يحكم
         الجلسة لا نهايتها. من خرج لم يعد شركة بل زائراً. */
      location.replace('../login.html');
    });
  }

  /* ══════════════════════════════════════════════════════════════
     سطح المستخدم (/me) — العزل مرفوع هنا فقط: صاحب المشروع مشترٍ
     لا بائع، فرابط دليل الشركات مقصود.
     ══════════════════════════════════════════════════════════════ */

  var USER_LINKS = [
    { href: 'index.html',    label: 'مشاريعي',       icon: I.folder },
    { href: 'bids.html',     label: 'العروض الواردة', icon: I.tag },
    { href: 'messages.html', label: 'الرسائل',        icon: I.chat },
    { href: 'settings.html', label: 'الإعدادات',      icon: I.gear }
  ];

  /* الشريط السفلي — خمسة، وفيها دليل الشركات (العزل مرفوع). */
  var USER_TABS = [
    { href: '/companies.html',  label: 'الشركات',  icon: I.building },
    { href: '/me/index.html',   label: 'مشاريعي',  icon: I.folder },
    { href: '/me/bids.html',    label: 'العروض',   icon: I.tag },
    { href: '/me/messages.html',label: 'الرسائل',  icon: I.chat },
    { href: '/me/settings.html',label: 'حسابي',    icon: I.user }
  ];

  var USER_CSS = `
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
/* الجوّال فقط: صفّ الروابط الأفقي القديم يختفي — الشريط السفلي
   الطائر المشترك (ومعه رابط دليل الشركات) يحلّ محلّه. سطح المكتب
   أعلاه بلا أي @media يمسّه، فيبقى كما كان تماماً. */
@media(max-width:820px){
  .bnm-nav{display:none}
}
`;

  function buildUser() {
    var name = '';
    try { name = localStorage.getItem('project_user_name') || ''; } catch (e) {}
    var bar = '<header class="bnm-bar bn-glass">' +
      '<div class="bnm-top">' +
        '<a class="bnm-logo" href="index.html">بُ<b>نيان</b></a>' +
        '<span class="bnm-id">' + svg(I.user, 13) +
          (name ? esc(name) : 'صاحب مشروع') + '</span>' +
        '<span class="bnm-sp"></span>' +
        '<button class="bnm-icon" type="button" data-bnm-theme aria-label="تبديل السمة"></button>' +
        '<button class="bnm-icon" type="button" data-bnm-out aria-label="خروج">' + svg(I.logout) + '</button>' +
      '</div>' +
      '<nav class="bnm-nav">' + USER_LINKS.map(function (l) {
        return '<a class="bnm-link" href="' + l.href + '"' + curRel(l.href) + '>' +
          svg(l.icon, 16) + '<span>' + l.label + '</span></a>';
      }).join('') + '</nav>' +
    '</header>';
    return bar + buildFab(USER_TABS);
  }

  function paintThemeUser() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bnm-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wireUser(root) {
    root.querySelector('[data-bnm-theme]').addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintThemeUser();
    });
    root.querySelector('[data-bnm-out]').addEventListener('click', function () {
      ['bn_token', 'project_user_id', 'project_user_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      location.replace('../login.html');
    });
  }

  /* ══════════════════════════════════════════════════════════════
     الموقع العام — زائر أو صاحب مشروع
     ══════════════════════════════════════════════════════════════ */

  var PUBLIC_LINKS = [
    { href: '/index.html',     label: 'الرئيسية', icon: I.home },
    { href: '/companies.html', label: 'الشركات',  icon: I.building },
    { href: '/projects.html',  label: 'المشاريع', icon: I.folder }
  ];

  var GUEST_TABS = [
    { href: '/index.html',     label: 'الرئيسية', icon: I.home },
    { href: '/companies.html', label: 'الشركات',  icon: I.building },
    { href: '/projects.html',  label: 'المشاريع', icon: I.folder },
    { href: '/login.html',     label: 'دخول',     icon: I.user }
  ];

  /* نفس USER_TABS بالضبط — صاحب مشروع يرى الشريط الخماسي نفسه سواء
     كان على صفحة عامة أو داخل /me. */
  var CLIENT_TABS = USER_TABS;

  var PUBLIC_CSS = `
.bnv{position:fixed;inset-block-start:0;inset-inline:0;z-index:300;height:60px;
  display:flex;align-items:center;gap:var(--bn-s4);padding-inline:var(--bn-s5);
  font-family:var(--bn-font);border-block-end:1px solid var(--bn-glass-line)}
.bnv-logo{display:inline-flex;align-items:center;gap:8px;text-decoration:none;
  color:var(--bn-ink);font:700 19px/1 var(--bn-font);flex:none;min-height:44px}
.bnv-logo b{color:var(--bn-ac);font-weight:700}
.bnv-links{display:flex;align-items:center;gap:2px;flex:1}
.bnv-link{display:inline-flex;align-items:center;gap:7px;min-height:44px;
  padding:0 var(--bn-s3);border-radius:var(--bn-r-sm);text-decoration:none;
  color:var(--bn-ink-2);font:400 13.5px/1 var(--bn-font);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bnv-link:hover{color:var(--bn-ink);background:var(--bn-glass-tint)}
.bnv-link[aria-current="page"]{color:var(--bn-ac);background:var(--bn-ac-bg);font-weight:500}
.bnv-right{display:flex;align-items:center;gap:var(--bn-s2);flex:none}
.bnv-icon{width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;
  border:0;background:0;color:var(--bn-ink-2);cursor:pointer;border-radius:var(--bn-r-sm);
  transition:color var(--bn-fast),background var(--bn-fast)}
.bnv-icon:hover{color:var(--bn-ac);background:var(--bn-ac-bg)}
.bnv-cta{display:inline-flex;align-items:center;min-height:44px;padding:0 var(--bn-s4);
  border-radius:var(--bn-r);text-decoration:none;font:500 13px/1 var(--bn-font);
  color:var(--bn-ac-on);background:linear-gradient(150deg,var(--bn-ac-2),var(--bn-ac));
  box-shadow:var(--bn-sh-ac)}
.bnv-cta:hover{filter:brightness(1.07)}
.bnv-acct{display:inline-flex;align-items:center;gap:7px;min-height:44px;
  padding:0 var(--bn-s3);border-radius:var(--bn-r-sm);text-decoration:none;
  color:var(--bn-ink-2);font:400 13px/1 var(--bn-font)}
.bnv-acct:hover{background:var(--bn-glass-tint);color:var(--bn-ink)}
@media(max-width:820px){
  .bnv-links{display:none}
  .bnv{padding-inline:var(--bn-s4)}
  .bnv-cta span{display:none}
}
`;

  function buildPublic() {
    var loggedIn = readClientLoggedIn();

    var links = PUBLIC_LINKS.map(function (l) {
      return '<a class="bnv-link" href="' + l.href + '"' + curAbs(l.href) + '>' +
             svg(l.icon, 16) + l.label + '</a>';
    }).join('');

    var right = loggedIn
      ? '<a class="bnv-acct" href="/me/index.html">' +
          '<span class="bn-id bn-id-client">' + svg(I.user, 13) + 'صاحب مشروع</span>' +
        '</a>' +
        '<button class="bnv-icon" type="button" data-bnv-out aria-label="خروج">' + svg(I.logout) + '</button>'
      : '<a class="bnv-cta" href="/login.html">' + svg(I.user, 15) + '<span>دخول</span></a>';

    var bar =
      '<nav class="bnv bn-glass" aria-label="التنقّل الرئيسي">' +
        '<a class="bnv-logo" href="/index.html">بُ<b>نيان</b></a>' +
        '<div class="bnv-links">' + links + '</div>' +
        '<div class="bnv-right">' +
          '<button class="bnv-icon" type="button" data-bnv-install hidden aria-label="تثبيت التطبيق">' +
            svg(I.install, 17) + '</button>' +
          '<button class="bnv-icon" type="button" data-bnv-theme aria-label="تبديل السمة"></button>' +
          right +
        '</div>' +
      '</nav>';

    return bar + buildFab(loggedIn ? CLIENT_TABS : GUEST_TABS);
  }

  function paintThemePublic() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bnv-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wirePublic(root) {
    var inst = root.querySelector('[data-bnv-install]');
    if (inst) inst.addEventListener('click', function () {
      if (isIOS) { location.href = '/install.html'; return; }
      if (!deferredPrompt) return;
      var p = deferredPrompt;
      deferredPrompt = null;
      paintInstallBtn();
      p.prompt();
    });
    var t = root.querySelector('[data-bnv-theme]');
    if (t) t.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintThemePublic();
    });
    var o = root.querySelector('[data-bnv-out]');
    if (o) o.addEventListener('click', function () {
      ['bn_token', 'project_user_id', 'project_user_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      location.href = '/index.html';
    });
  }

  /* ── أدوات مشتركة للتحديد الحالي ─────────────────────────────
     curRel: أسماء ملفّات نسبية (داخل /app أو /me نفسها).
     curAbs: مسارات مطلقة (الشريط الطائر، والصفوف العامة). */
  var PAGE = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function curRel(f) { return PAGE === f.split('/').pop() ? ' aria-current="page"' : ''; }
  function curAbs(href) { return PATH === href ? ' aria-current="page"' : ''; }

  /* ── الإقلاع ───────────────────────────────────────────────── */
  function mount() {
    var style = document.getElementById('bn-nav-style');
    if (!style) {
      style = document.createElement('style');
      style.id = 'bn-nav-style';
      document.head.appendChild(style);
    }
    var surfaceCss = SURFACE === 'company' ? COMPANY_CSS
      : SURFACE === 'user' ? USER_CSS
      : PUBLIC_CSS;
    style.textContent = FAB_CSS + surfaceCss;

    var host = document.getElementById('bn-nav') || document.getElementById('bn-nav-mount');
    if (!host) {
      host = document.createElement('div');
      document.body.insertBefore(host, document.body.firstChild);
    }

    if (SURFACE === 'company') {
      host.innerHTML = buildCompany();
      paintThemeCompany();
      wireCompany(host);
    } else if (SURFACE === 'user') {
      host.innerHTML = buildUser();
      paintThemeUser();
      wireUser(host);
    } else {
      host.innerHTML = buildPublic();
      if (!document.body.style.paddingTop) document.body.style.paddingTop = '60px';
      paintThemePublic();
      paintInstallBtn();
      wirePublic(host);
    }
  }

  window.BunyanNav = { mount: mount, surface: SURFACE };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
