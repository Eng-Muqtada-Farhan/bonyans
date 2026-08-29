/**
 * بُنيان — قائمة لوحة الشركة  ⛔ سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * ⛔ قاعدة العزل ١ — لا رابط تصفّح للموقع العام في هذا الملف:
 *    لا دليل الشركات ولا سوق المشاريع ولا الصفحة الرئيسية،
 *    و«الشعار يؤدي إلى /app لا إلى /» (§٤ قاعدة ٤).
 *    العزل بنيوي: الرابط غير موجود أصلاً، لا مخفيّ بشرط.
 *
 *    الاستثناء الوحيد — مُصرَّح به من صاحب المشروع ٣٠ آب ٢٠٢٦ —
 *    هو وجهة زر الخروج: ../login.html. العزل يحكم الجلسة لا
 *    نهايتها؛ من خرج لم يعد شركة بل زائراً.
 *
 * الاستثناء المعتمد الوحيد — «معاينة ملفي العام» — يعيش في
 * app/profile.html بجوار زر الحفظ، لا في هذه القائمة (§٤).
 *
 * التركيب: <script src="nav-app.js"></script>
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
    building: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2"/>',
    image:    '<rect x="3" y="4.5" width="18" height="15" rx="1.5"/><circle cx="8.5" cy="10" r="1.6"/><path d="M21 16l-5-5-9 8.5"/>',
    market:   '<path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3z"/><path d="M8.5 8V6a3.5 3.5 0 0 1 7 0v2"/>',
    tag:      '<path d="M3.5 11.2V4.5a1 1 0 0 1 1-1h6.7a1 1 0 0 1 .7.3l8.3 8.3a1 1 0 0 1 0 1.4l-6.7 6.7a1 1 0 0 1-1.4 0L3.8 11.9a1 1 0 0 1-.3-.7z"/><circle cx="7.8" cy="7.8" r="1.3"/>',
    chat:     '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>',
    star:     '<path d="M12 3.6l2.6 5.3 5.8.85-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.2-4.1 5.8-.85z"/>',
    card:     '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    gear:     '<circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
    sun:      '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M19.1 4.9l-1.4 1.4M6.3 17.7l-1.4 1.4"/>',
    moon:     '<path d="M20 13.5A8.5 8.5 0 1 1 10.5 4a6.7 6.7 0 0 0 9.5 9.5z"/>',
    logout:   '<path d="M9 21H5.5A1.5 1.5 0 0 1 4 19.5v-15A1.5 1.5 0 0 1 5.5 3H9"/><path d="M16 16l4-4-4-4M20 12H9"/>',
    menu:     '<path d="M4 7h16M4 12h16M4 17h16"/>',
    close:    '<path d="M6 6l12 12M18 6L6 18"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 17) + '" height="' + (s || 17) +
           '" fill="none" stroke="currentColor" stroke-width="1.6" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* ── الكتل الثلاث (DESIGN.md §٦) ────────────────────────────
     كل الوجهات نسبية داخل /app — لا مسار يغادر السطح. */
  var BLOCKS = [
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

  var CSS = `
.bna-bar{position:fixed;inset-block-start:0;inset-inline:0;z-index:290;height:56px;
  display:none;align-items:center;gap:var(--bn-s3);padding-inline:var(--bn-s4);
  font-family:var(--bn-font);border-block-end:1px solid var(--bn-glass-line)}
.bna-side{position:fixed;inset-block:0;inset-inline-start:0;z-index:300;width:244px;
  display:flex;flex-direction:column;font-family:var(--bn-font);
  border-inline-end:1px solid var(--bn-glass-line);transition:transform var(--bn-mid)}
.bna-head{padding:var(--bn-s5) var(--bn-s5) var(--bn-s4)}
.bna-logo{display:inline-flex;align-items:center;gap:8px;text-decoration:none;
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
.bna-scrim{position:fixed;inset:0;z-index:295;background:rgba(0,0,0,.42);
  opacity:0;pointer-events:none;transition:opacity var(--bn-mid)}

body{padding-inline-start:244px}

@media(max-width:900px){
  body{padding-inline-start:0;padding-block-start:56px}
  .bna-bar{display:flex}
  .bna-side{transform:translateX(100%);box-shadow:var(--bn-sh-3)}
  [dir="ltr"] .bna-side{transform:translateX(-100%)}
  .bna-side.is-open{transform:none}
  .bna-scrim.is-open{opacity:1;pointer-events:auto}
}
`;

  var PAGE = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function cur(f) { return PAGE === f ? ' aria-current="page"' : ''; }

  function build() {
    var nav = BLOCKS.map(function (b) {
      var items = b.items.map(function (it) {
        return '<a class="bna-link" href="' + it.href + '"' + cur(it.href) + '>' +
               svg(it.icon, 17) + '<span>' + it.label + '</span></a>';
      }).join('');
      return '<div class="bna-block">' +
             (b.title ? '<div class="bna-title">' + b.title + '</div>' : '') +
             items + '</div>';
    }).join('');

    var name = '';
    try { name = localStorage.getItem('company_name') || ''; } catch (e) {}

    return '' +
      '<div class="bna-scrim" data-bna-scrim></div>' +
      '<header class="bna-bar bn-glass">' +
        '<button class="bna-icon" type="button" data-bna-open aria-label="فتح القائمة">' + svg(I.menu, 20) + '</button>' +
        /* الشعار في اللوحة يؤدي إلى لوحة القيادة — لا إلى الموقع العام (§٤ قاعدة ٤) */
        '<a class="bna-logo" href="index.html" style="font-size:17px">بُ<b>نيان</b></a>' +
      '</header>' +
      '<aside class="bna-side bn-glass" data-bna-side aria-label="تنقّل لوحة الشركة">' +
        '<div class="bna-head">' +
          '<a class="bna-logo" href="index.html">بُ<b>نيان</b></a>' +
          '<div class="bna-id">' +
            '<span class="bn-id bn-id-company">' + svg(I.building, 13) +
              (name ? name : 'حساب شركة') +
            '</span>' +
          '</div>' +
        '</div>' +
        '<nav class="bna-nav">' + nav + '</nav>' +
        '<div class="bna-foot">' +
          '<button class="bna-icon" type="button" data-bna-theme aria-label="تبديل السمة"></button>' +
          '<button class="bna-icon" type="button" data-bna-out aria-label="خروج">' + svg(I.logout) + '</button>' +
        '</div>' +
      '</aside>';
  }

  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bna-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wire(root) {
    var side  = root.querySelector('[data-bna-side]');
    var scrim = root.querySelector('[data-bna-scrim]');
    function close() { side.classList.remove('is-open'); scrim.classList.remove('is-open'); }

    root.querySelector('[data-bna-open]').addEventListener('click', function () {
      side.classList.add('is-open'); scrim.classList.add('is-open');
    });
    scrim.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });

    root.querySelector('[data-bna-theme]').addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintTheme();
    });

    root.querySelector('[data-bna-out]').addEventListener('click', function () {
      ['COMPANY_TOKEN', 'company_id', 'company_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      /* امسح كعكة جلسة الخادم أيضاً وإلا بقي الحارس يسمح بالمرور */
      document.cookie = 'bn_sess=; path=/; max-age=0; SameSite=Lax';
      /* استثناء مُصرَّح به من صاحب المشروع: العزل يحكم الجلسة لا
         نهايتها. من خرج لم يعد شركة بل زائراً، وصفحة الدخول وجهته.
         البقاء على /app بلا جلسة يترك المستخدم لحظةً قبل قذف الحارس. */
      location.replace('../login.html');
    });
  }

  function mount() {
    if (!document.getElementById('bna-style')) {
      var s = document.createElement('style');
      s.id = 'bna-style';
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
  }

  window.BunyanNavApp = { mount: mount, surface: 'app' };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
