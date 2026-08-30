/**
 * بُنيان — قائمة الموقع العام
 * ═══════════════════════════════════════════════════════════════
 * السطح: الواجهة العامة (زائر · صاحب مشروع)
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * هذه القائمة الوحيدة التي يجوز أن تحمل روابط عامة.
 * لوحتا الشركة والإدارة لهما ملفّاهما، ولا رابط عام في كودهما.
 *
 * التركيب: <script src="nav-public.js"></script>
 * يُركَّب تلقائياً في #bn-nav أو #bn-nav-mount، أو في أول الجسم.
 */
(function () {
  'use strict';

  /* ── الخط ──────────────────────────────────────────────────── */
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
    logout:   '<path d="M9 21H5.5A1.5 1.5 0 0 1 4 19.5v-15A1.5 1.5 0 0 1 5.5 3H9"/><path d="M16 16l4-4-4-4M20 12H9"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 17) + '" height="' + (s || 17) +
           '" fill="none" stroke="currentColor" stroke-width="1.6" ' +
           'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* ── حالة الدخول ───────────────────────────────────────────
     الموقع العام يعرف حالتين فقط: زائر، أو صاحب مشروع داخل.
     الشركة والمدير لا يصلان إلى هنا (الحرّاس — الخطوة ٤). */
  function jwtValid(tok) {
    if (!tok) return null;
    try {
      var p = JSON.parse(atob(tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return (!p.exp || Date.now() / 1000 < p.exp) ? p : null;
    } catch (e) { return null; }
  }
  function readRole() {
    var t = localStorage.getItem('project_user_token');
    if (jwtValid(t)) {
      return { role: 'client', name: localStorage.getItem('project_user_name') || 'حسابي' };
    }
    return { role: 'guest', name: '' };
  }

  /* ── الأنماط ───────────────────────────────────────────────── */
  var CSS = `
.bnv{position:fixed;inset-block-start:0;inset-inline:0;z-index:300;height:60px;
  display:flex;align-items:center;gap:var(--bn-s4);padding-inline:var(--bn-s5);
  font-family:var(--bn-font);border-block-end:1px solid var(--bn-glass-line)}
.bnv-logo{display:inline-flex;align-items:center;gap:8px;text-decoration:none;
  color:var(--bn-ink);font:700 19px/1 var(--bn-font);flex:none}
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

/* الشريط السفلي — الجوّال */
.bnv-tabs{display:none}
@media(max-width:820px){
  .bnv-links{display:none}
  .bnv{padding-inline:var(--bn-s4)}
  .bnv-cta span{display:none}
  .bnv-tabs{position:fixed;inset-block-end:0;inset-inline:0;z-index:300;
    display:grid;grid-template-columns:repeat(5,1fr);
    border-block-start:1px solid var(--bn-glass-line);
    padding-block-end:env(safe-area-inset-bottom)}
  .bnv-tab{display:flex;flex-direction:column;align-items:center;justify-content:center;
    gap:3px;min-height:56px;text-decoration:none;color:var(--bn-ink-3);
    font:400 10.5px/1.2 var(--bn-font)}
  .bnv-tab[aria-current="page"]{color:var(--bn-ac)}
  body{padding-block-end:64px}
}
`;

  /* ── البناء ────────────────────────────────────────────────── */
  var PAGE = (location.pathname.split('/').pop() || 'index.html').toLowerCase();
  function cur(f) { return PAGE === f.split('/').pop() ? ' aria-current="page"' : ''; }

  var LINKS = [
    { href: '/index.html',     label: 'الرئيسية', icon: I.home },
    { href: '/companies.html', label: 'الشركات',  icon: I.building },
    { href: '/projects.html',  label: 'المشاريع', icon: I.folder }
  ];

  function build() {
    var st = readRole();

    var links = LINKS.map(function (l) {
      return '<a class="bnv-link" href="' + l.href + '"' + cur(l.href) + '>' +
             svg(l.icon, 16) + l.label + '</a>';
    }).join('');

    // زائر ← دعوة للدخول · صاحب مشروع ← بطاقة هوية مفرَّغة
    var right = st.role === 'client'
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
          '<button class="bnv-icon" type="button" data-bnv-theme aria-label="تبديل السمة"></button>' +
          right +
        '</div>' +
      '</nav>';

    var tabs = [
      { href: '/index.html',     label: 'الرئيسية', icon: I.home },
      { href: '/companies.html', label: 'الشركات',  icon: I.building },
      { href: '/projects.html',  label: 'المشاريع', icon: I.folder },
      { href: '/me/messages.html', label: 'الرسائل', icon: I.chat },
      { href: st.role === 'client' ? 'me/index.html' : 'login.html', label: 'حسابي', icon: I.user }
    ].map(function (t) {
      return '<a class="bnv-tab" href="' + t.href + '"' + cur(t.href) + '>' +
             svg(t.icon, 20) + '<span>' + t.label + '</span></a>';
    }).join('');

    return bar + '<nav class="bnv-tabs bn-glass" aria-label="تنقّل الجوّال">' + tabs + '</nav>';
  }

  /* ── السمة ─────────────────────────────────────────────────── */
  function paintTheme() {
    var dark = document.documentElement.getAttribute('data-theme') === 'dark';
    document.querySelectorAll('[data-bnv-theme]').forEach(function (b) {
      b.innerHTML = svg(dark ? I.sun : I.moon);
    });
  }

  function wire(root) {
    var t = root.querySelector('[data-bnv-theme]');
    if (t) t.addEventListener('click', function () {
      var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('bn-theme', next); } catch (e) {}
      paintTheme();
    });
    var o = root.querySelector('[data-bnv-out]');
    if (o) o.addEventListener('click', function () {
      ['project_user_token', 'project_user_id', 'project_user_name'].forEach(function (k) {
        try { localStorage.removeItem(k); } catch (e) {}
      });
      /* الكعكة HttpOnly فلا تمسحها الصفحة — يمسحها الخادم.
         keepalive حتى يكتمل الطلب رغم مغادرة الصفحة. */
      try { fetch('/logout', { method: 'POST', keepalive: true }); } catch (e) {}
      location.href = '/index.html';
    });
  }

  function mount() {
    if (!document.getElementById('bnv-style')) {
      var s = document.createElement('style');
      s.id = 'bnv-style';
      s.textContent = CSS;
      document.head.appendChild(s);
    }
    var host = document.getElementById('bn-nav') ||
               document.getElementById('bn-nav-mount');
    if (!host) {
      host = document.createElement('div');
      document.body.insertBefore(host, document.body.firstChild);
    }
    host.innerHTML = build();
    // شريط علوي ثابت — احجز ارتفاعه (DESIGN.md §٦)
    if (!document.body.style.paddingTop) document.body.style.paddingTop = '60px';
    paintTheme();
    wire(host);
  }

  window.BunyanNavPublic = { mount: mount, surface: 'public' };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
