/**
 * بُنيان — Unified Navigation Component
 * Phase 10b — Royal Glass Design
 *
 * Usage: <script src="bunyan-nav.js"></script>
 * Auth detection:
 *   Admin:   localStorage.admin_token
 *   Company: localStorage.COMPANY_TOKEN
 *   User:    localStorage.project_user_token
 */

window.BunyanNav = (function () {

  /* ── Inject CSS for nav-specific styles not in bunyan.css ── */
  function _injectStyles() {
    if (document.getElementById('bn-nav-styles')) return;
    const style = document.createElement('style');
    style.id = 'bn-nav-styles';
    style.textContent = `
/* Nav link styles */
#bn-nav a, #bn-nav .bn-nav-link-item {
  text-decoration: none;
  font-family: 'Cairo', sans-serif;
}
.bn-nav-links-row {
  display: flex; align-items: center; gap: 4px; flex: 1;
  justify-content: flex-start; padding-right: 16px;
}
.bn-nav-links-row a {
  padding: 7px 14px; border-radius: 10px;
  font-size: 13px; font-weight: 600; color: var(--text-2);
  transition: all 0.18s; white-space: nowrap;
}
.bn-nav-links-row a:hover  { color: var(--clay); background: rgba(27,58,107,0.08); }
.bn-nav-links-row a.active { color: var(--clay); background: rgba(27,58,107,0.10); font-weight:700; }
[data-theme="dark"] .bn-nav-links-row a:hover { background: rgba(255,255,255,0.08); color: var(--clay-light); }
@media (max-width: 680px) { .bn-nav-links-row { display: none; } }

/* Notification badge */
.notif-badge {
  position: absolute; top: -2px; right: -2px;
  width: 8px; height: 8px; border-radius: 50%;
  background: #EF5350; display: none;
  border: 1.5px solid white;
}
.notif-badge.show { display: block; }

/* Hamburger */
.bn-hamburger {
  display: none; flex-direction: column; gap: 5px;
  background: none; border: none; cursor: pointer;
  padding: 4px; border-radius: 8px;
}
.bn-hamburger span {
  display: block; width: 20px; height: 2px;
  background: var(--text-2); border-radius: 2px; transition: all 0.2s;
}
.bn-hamburger:hover span { background: var(--clay); }
@media (max-width: 680px) { .bn-hamburger { display: flex; } }

/* Mobile drawer */
#bn-mobile-drawer {
  position: fixed; inset: 0; z-index: 350;
  background: rgba(8,14,28,0.55); backdrop-filter: blur(4px);
  display: none; justify-content: flex-end;
  transition: opacity 0.25s;
}
#bn-mobile-drawer.open { display: flex; }
.bn-drawer-inner {
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
  border-right: none; border-left: 1.5px solid rgba(255,255,255,0.85);
  width: 260px; max-width: 80vw; height: 100%;
  display: flex; flex-direction: column;
  padding: 20px 0; overflow-y: auto;
  animation: drawerIn 0.25s ease;
}
[data-theme="dark"] .bn-drawer-inner {
  background: rgba(8,14,28,0.92);
  border-left-color: rgba(255,255,255,0.10);
}
@keyframes drawerIn { from{transform:translateX(100%)} to{transform:translateX(0)} }
.bn-drawer-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px 16px; border-bottom: 1px solid rgba(27,58,107,0.1);
  margin-bottom: 8px;
}
.bn-drawer-brand { font-size: 18px; font-weight: 900; color: var(--clay-deep); }
[data-theme="dark"] .bn-drawer-brand { color: var(--clay-light); }
.bn-drawer-close {
  width: 32px; height: 32px; border-radius: 8px;
  background: rgba(27,58,107,0.08); border: none;
  color: var(--text-2); font-size: 16px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.bn-drawer-item {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px; font-size: 14px; font-weight: 600;
  color: var(--text-1); text-decoration: none;
  transition: background 0.18s; border: none;
  background: none; font-family: 'Cairo', sans-serif;
  cursor: pointer; width: 100%; text-align: right;
}
.bn-drawer-item:hover { background: rgba(27,58,107,0.07); color: var(--clay); }
.bn-drawer-item.danger { color: var(--red-light); }
.bn-drawer-item.danger:hover { background: rgba(198,40,40,0.07); }
.bn-drawer-sep { height: 1px; background: rgba(27,58,107,0.08); margin: 6px 12px; }

/* notif link relative wrapper */
.bn-notif-wrap { position: relative; display: inline-flex; align-items: center; }
`;
    document.head.appendChild(style);
  }

  /* ── Detect current page ────────────────────────── */
  function currentPage() {
    return location.pathname.replace(/\/$/, '').split('/').pop() || 'index.html';
  }

  /* ── Auth state — delegated to auth-core.js ─────── */
  function getAuth() {
    return window.authCore ? window.authCore.getAuthState() : { role: 'guest', token: null, name: '', userId: null, companyId: null };
  }

  /* ── Dropdown items ─────────────────────────────── */
  function dropdownHTML(auth) {
    if (auth.role === 'guest') return `
      <div class="bn-dd-label">الدخول</div>
      <a class="bn-dd-item" href="company_dashboard.html">🔑 دخول الشركات</a>
      <a class="bn-dd-item" href="#" onclick="BunyanNav.openRegModal();return false">🏢 سجّل شركتك</a>
      <div class="bn-dd-sep"></div>
      <a class="bn-dd-item" href="#" onclick="BunyanNav.openUserLogin();return false">👤 دخول المستخدم</a>
      ${_settingsHTML()}`;

    if (auth.role === 'admin') return `
      <div class="bn-dd-label">مدير النظام</div>
      <a class="bn-dd-item active" href="admin.html">⚙️ لوحة الإدارة</a>
      <div class="bn-dd-sep"></div>
      <button class="bn-dd-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>
      ${_settingsHTML()}`;

    if (auth.role === 'company') return `
      <div class="bn-dd-label">حساب الشركة</div>
      <a class="bn-dd-item" href="company_dashboard.html">📊 لوحة الشركة</a>
      <a class="bn-dd-item" href="company_dashboard.html#profile">🏢 إدارة الملف</a>
      <a class="bn-dd-item" href="company_dashboard.html#subscription">⭐ الاشتراك الحالي</a>
      <a class="bn-dd-item" href="company_dashboard.html#messages">📬 الرسائل</a>
      <a class="bn-dd-item" href="company_dashboard.html#overview">📈 الإحصائيات</a>
      <div class="bn-dd-sep"></div>
      <button class="bn-dd-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>
      ${_settingsHTML()}`;

    if (auth.role === 'user') return `
      <div class="bn-dd-label">مرحباً، ${auth.name || 'مستخدم'}</div>
      <a class="bn-dd-item" href="#">👤 حسابي</a>
      <a class="bn-dd-item" href="#">❤️ المفضلة</a>
      <a class="bn-dd-item" href="#">📬 رسائلي</a>
      <a class="bn-dd-item" href="projects.html#my">📂 مشاريعي</a>
      <div class="bn-dd-sep"></div>
      <button class="bn-dd-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>
      ${_settingsHTML()}`;

    return _settingsHTML();
  }

  /* ── Avatar icon/label ──────────────────────────── */
  function avatarIcon(auth) {
    if (auth.role === 'admin')   return '⚙️';
    if (auth.role === 'company') return '🏢';
    if (auth.role === 'user')    return '👤';
    return '👤';
  }

  /* ── Build main nav HTML ────────────────────────── */
  function buildNav() {
    const auth = getAuth();
    const pg   = currentPage();

    const navLinks = [
      { href: 'index.html',          label: '🏠 الرئيسية',  match: ['index.html',''] },
      { href: 'companies.html', label: '🏢 الشركات', match: ['companies.html'] },
      { href: 'projects.html',       label: '📂 المشاريع', match: ['projects.html'] },
    ];

    const linkHTML = navLinks.map(l => {
      const active = l.match.includes(pg) ? 'active' : '';
      return `<a href="${l.href}" class="${active}">${l.label}</a>`;
    }).join('');

    const notifHref = auth.role === 'company' ? 'company_dashboard.html#notifications' : '#';
    const notifItem = auth.role !== 'guest'
      ? `<div class="bn-notif-wrap">
           <a href="${notifHref}" id="bn-notif-link">🔔</a>
           <span class="notif-badge" id="bn-notif-dot"></span>
         </div>`
      : '';

    /* Drawer items */
    const drawerLinks = navLinks.map(l =>
      `<a class="bn-drawer-item" href="${l.href}">${l.label}</a>`
    ).join('');

    const drawerAuth = auth.role === 'guest' ? `
      <div class="bn-drawer-sep"></div>
      <a class="bn-drawer-item" href="company_dashboard.html">🔑 دخول الشركات</a>
      <a class="bn-drawer-item" href="#" onclick="BunyanNav.openRegModal();BunyanNav._closeMobile();return false">🏢 سجّل شركتك</a>
      <a class="bn-drawer-item" href="#" onclick="BunyanNav.openUserLogin();BunyanNav._closeMobile();return false">👤 دخول المستخدم</a>` :
    auth.role === 'admin' ? `
      <div class="bn-drawer-sep"></div>
      <a class="bn-drawer-item" href="admin.html">⚙️ لوحة الإدارة</a>
      <button class="bn-drawer-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>` :
    auth.role === 'company' ? `
      <div class="bn-drawer-sep"></div>
      <a class="bn-drawer-item" href="company_dashboard.html">📊 لوحة الشركة</a>
      <a class="bn-drawer-item" href="company_dashboard.html#profile">🏢 إدارة الملف</a>
      <a class="bn-drawer-item" href="company_dashboard.html#subscription">⭐ الاشتراك</a>
      <a class="bn-drawer-item" href="company_dashboard.html#messages">📬 الرسائل</a>
      <button class="bn-drawer-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>` :
    `
      <div class="bn-drawer-sep"></div>
      <div style="padding:10px 20px;font-size:13px;color:var(--text-3)">مرحباً، ${auth.name||'مستخدم'}</div>
      <a class="bn-drawer-item" href="#">👤 حسابي</a>
      <a class="bn-drawer-item" href="#">❤️ المفضلة</a>
      <a class="bn-drawer-item" href="#">📬 رسائلي</a>
      <button class="bn-drawer-item danger" onclick="BunyanNav.logout()">🚪 تسجيل الخروج</button>`;

    return `
<nav id="bn-nav">
  <div class="bn-nav-inner">
    <!-- Logo -->
    <a class="bn-logo" href="index.html">
      <div class="bn-logo-bricks">
        <span class="bn-brick bn-b1"></span>
        <span class="bn-brick bn-b2"></span>
        <span class="bn-brick bn-b3"></span>
      </div>
      بُنيان
    </a>

    <!-- Desktop links -->
    <div class="bn-nav-links-row">
      ${linkHTML}
      ${notifItem}
    </div>

    <!-- Mobile inline search (hidden on desktop) -->
    <div class="bn-mobile-search-row">
      <input type="text" id="searchInputNav" placeholder="شركة، تخصص، محافظة..."
        oninput="if(typeof filterCompanies==='function'){document.getElementById('searchInput')&&(document.getElementById('searchInput').value=this.value);filterCompanies();}"
        onkeydown="if(event.key==='Enter'&&typeof filterCompanies==='function')filterCompanies()">
    </div>

    <!-- Right: account + dots + hamburger -->
    <div class="bn-nav-right">
      <div class="bn-menu-btn" id="bn-acct-btn" onclick="BunyanNav._toggleDrop()" style="position:relative;gap:6px;padding:8px 12px;min-width:auto;font-size:13px;font-weight:700;color:var(--text-2)">
        <span>${avatarIcon(auth)}</span>
        <span style="max-width:90px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">
          ${auth.role === 'guest' ? 'حسابي' : auth.role === 'admin' ? 'أدمن' : auth.role === 'company' ? 'الشركة' : (auth.name||'حسابي')}
        </span>
        <span>▾</span>
        <div class="bn-dropdown" id="bn-dropdown">
          ${dropdownHTML(auth)}
        </div>
      </div>
      <button class="bn-mobile-dots" onclick="BunyanNav._openMobile()" aria-label="القائمة">⋮</button>
      <button class="bn-hamburger" id="bn-hamburger" onclick="BunyanNav._openMobile()" aria-label="القائمة">
        <span></span><span></span><span></span>
      </button>
    </div>
  </div>
</nav>

<!-- Mobile Drawer Overlay -->
<div id="bn-mobile-drawer" onclick="BunyanNav._closeMobileIfOverlay(event)">
  <div class="bn-drawer-inner">
    <div class="bn-drawer-head">
      <span class="bn-drawer-brand">بُنيان</span>
      <button class="bn-drawer-close" onclick="BunyanNav._closeMobile()">✕</button>
    </div>
    ${drawerLinks}
    ${drawerAuth}
  </div>
</div>
`;
  }

  /* ── Theme toggle ──────────────────────────────── */
  function _toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme') ||
                localStorage.getItem('bn-theme') || 'light';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    document.body.setAttribute('data-theme', next);
    localStorage.setItem('bn-theme', next);
    const btn = document.getElementById('bn-theme-btn');
    if (btn) btn.textContent = next === 'dark' ? '☀️ النهاري' : '🌙 الليلي';
  }

  /* ── Language toggle (placeholder) ─────────────── */
  function _toggleLang() {
    alert('قريباً — دعم اللغة الإنجليزية');
  }

  /* ── Settings dropdown items ─────────────────── */
  function _settingsHTML() {
    const theme = localStorage.getItem('bn-theme') || 'light';
    return `
      <div class="bn-dd-sep"></div>
      <div class="bn-dd-label">إعدادات</div>
      <button class="bn-dd-item" id="bn-theme-btn" onclick="BunyanNav._toggleTheme()">
        ${theme === 'dark' ? '☀️ النهاري' : '🌙 الليلي'}
      </button>
      <button class="bn-dd-item" onclick="BunyanNav._toggleLang()">🌐 اللغة</button>
      <div class="bn-dd-sep"></div>
      <a class="bn-dd-item" href="mailto:info@bunyan.iq">📞 تواصل معنا</a>
      <a class="bn-dd-item" href="#privacy">🔒 الخصوصية</a>
      <a class="bn-dd-item" href="#terms">📋 الشروط</a>`;
  }

  /* ── Inject bottom pill nav ─────────────────────── */
  function _injectPillNav() {
    if (document.getElementById('bn-pill-nav')) return;
    if (document.body.hasAttribute('data-no-pill-nav')) return;
    const auth = getAuth();
    const pg   = currentPage();

    const isHome    = pg === 'index.html' || pg === '';
    const isAccount = pg === 'company_dashboard.html';
    const isMsgs    = false;

    const pill = document.createElement('div');
    pill.id = 'bn-pill-nav';

    if (auth.role === 'company') {
      /* Company bottom nav: الرئيسية | بحث | +إضافة مشروع | الرسائل | لوحة الشركة */
      pill.innerHTML = `
        <a class="bn-ni ${isHome ? 'active' : ''}" href="index.html">
          <span class="bn-ni-ico">🏠</span>
          <span class="bn-ni-lbl">الرئيسية</span>
        </a>
        <button class="bn-ni" onclick="BunyanNav._focusSearch()" style="cursor:pointer">
          <span class="bn-ni-ico">🔍</span>
          <span class="bn-ni-lbl">بحث</span>
        </button>
        <div class="bn-ni-add" onclick="window.location.href='company_dashboard.html#projects'" title="إضافة مشروع">+</div>
        <a class="bn-ni" href="company_dashboard.html#messages">
          <span class="bn-ni-ico">📬</span>
          <span class="bn-ni-lbl">الرسائل</span>
        </a>
        <a class="bn-ni ${isAccount ? 'active' : ''}" href="company_dashboard.html">
          <span class="bn-ni-ico">📊</span>
          <span class="bn-ni-lbl">لوحتي</span>
        </a>`;
    } else {
      /* Guest / User bottom nav: الرئيسية | بحث | +طلب مشروع | مفضلة | حسابي */
      const acctHref = auth.role === 'admin' ? 'admin.html' : auth.role === 'user' ? '#' : 'company_dashboard.html';
      pill.innerHTML = `
        <a class="bn-ni ${isHome ? 'active' : ''}" href="index.html">
          <span class="bn-ni-ico">🏠</span>
          <span class="bn-ni-lbl">الرئيسية</span>
        </a>
        <button class="bn-ni" onclick="BunyanNav._focusSearch()" style="cursor:pointer">
          <span class="bn-ni-ico">🔍</span>
          <span class="bn-ni-lbl">بحث</span>
        </button>
        <div class="bn-ni-add" onclick="window.location.href='projects.html'" title="اطلب مشروع">+</div>
        <a class="bn-ni" href="#">
          <span class="bn-ni-ico">❤️</span>
          <span class="bn-ni-lbl">المفضلة</span>
        </a>
        <a class="bn-ni ${isAccount ? 'active' : ''}" href="${acctHref}">
          <span class="bn-ni-ico">${avatarIcon(auth)}</span>
          <span class="bn-ni-lbl">حسابي</span>
        </a>`;
    }

    document.body.appendChild(pill);
  }

  /* ── Inject nav ─────────────────────────────────── */
  function init() {
    _injectStyles();
    if (window.authCore) window.getAuthState = window.authCore.getAuthState;
    const html  = buildNav();
    const mount = document.getElementById('bn-nav-mount');
    if (mount) {
      mount.outerHTML = html;
    } else {
      document.body.insertAdjacentHTML('afterbegin', html);
    }

    /* Close dropdown on outside click */
    document.addEventListener('click', e => {
      const btn = document.getElementById('bn-acct-btn');
      const dd  = document.getElementById('bn-dropdown');
      if (btn && dd && !btn.contains(e.target)) dd.classList.remove('open');
    });

    /* Inject bottom pill nav */
    _injectPillNav();

    /* Poll notifications */
    const auth = getAuth();
    if (auth.role !== 'guest') {
      _pollNotifications(auth);
      setInterval(() => _pollNotifications(auth), 60000);
    }
  }

  /* ── Dropdown toggle ────────────────────────────── */
  function _toggleDrop() {
    const dd = document.getElementById('bn-dropdown');
    if (dd) dd.classList.toggle('open');
  }

  /* ── Mobile drawer ──────────────────────────────── */
  function _openMobile() {
    const d = document.getElementById('bn-mobile-drawer');
    if (d) d.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function _closeMobile() {
    const d = document.getElementById('bn-mobile-drawer');
    if (d) d.classList.remove('open');
    document.body.style.overflow = '';
  }
  function _closeMobileIfOverlay(e) {
    if (e.target.id === 'bn-mobile-drawer') _closeMobile();
  }

  /* ── Notification poll ──────────────────────────── */
  async function _pollNotifications(auth) {
    try {
      const r = await fetch('/notifications', { headers: { Authorization: auth.token } });
      if (!r.ok) return;
      const notifs = await r.json();
      const unread = notifs.filter(n => !n.is_read).length;
      [document.getElementById('bn-notif-dot'), document.getElementById('bn-pill-notif-dot')]
        .forEach(dot => { if (dot) dot.classList.toggle('show', unread > 0); });
    } catch (_) {}
  }

  /* ── Logout — delegated to auth-core.js ─────────── */
  function logout() {
    if (window.authCore) { window.authCore.logout(); return; }
    ['admin_token','token','COMPANY_TOKEN','project_user_token',
     'project_user_id','project_user_name','company_id',
     'project_company_id'].forEach(function(k) { localStorage.removeItem(k); });
    window.location.href = 'index.html';
  }

  /* ── Open register modal ────────────────────────── */
  function openRegModal() {
    if (typeof window.openRegModal === 'function') window.openRegModal();
    else console.warn('[bunyan-nav] openRegModal: no modal on this page');
  }

  /* ── Open user login — delegated to auth-core.js ── */
  function openUserLogin() {
    if (window.authCore) { window.authCore.openLoginModal(); return; }
    console.warn('[bunyan-nav] auth-core.js not loaded');
  }

  /* ── Inject footer ──────────────────────────────── */
  function injectFooter() {
    const el  = document.getElementById('bn-footer-mount');
    const html = `
<footer id="bn-footer">
  <div class="bn-footer-inner">
    <div class="bn-footer-grid">
      <div>
        <div class="bn-footer-brand-title">بُنيان</div>
        <div class="bn-footer-brand-desc">منصة المقاولات الذكية في العراق — نربط أصحاب المشاريع بأفضل شركات البناء والمقاولات الموثوقة.</div>
      </div>
      <div>
        <div class="bn-footer-col-title">الخدمات</div>
        <div class="bn-footer-links">
          <a href="companies.html">دليل الشركات</a>
          <a href="projects.html">سوق المشاريع</a>
          <a href="index.html#plans-section">باقات الاشتراك</a>
        </div>
      </div>
      <div>
        <div class="bn-footer-col-title">للشركات</div>
        <div class="bn-footer-links">
          <a href="company_dashboard.html">لوحة التحكم</a>
          <a href="index.html">تسجيل شركة</a>
          <a href="company_dashboard.html#subscription">ترقية الباقة</a>
        </div>
      </div>
      <div>
        <div class="bn-footer-col-title">تواصل معنا</div>
        <div class="bn-footer-links">
          <a href="mailto:info@bunyan.iq">info@bunyan.iq</a>
          <a href="https://wa.me/9647700000000">واتساب</a>
          <a href="https://t.me/bunyaniq">تيليغرام</a>
        </div>
      </div>
    </div>
    <div class="bn-footer-bottom">
      <div class="bn-footer-copy">© ${new Date().getFullYear()} بُنيان — جميع الحقوق محفوظة</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.40)">صُنع في العراق 🇮🇶</div>
    </div>
  </div>
</footer>`;
    if (el) el.outerHTML = html;
    else    document.body.insertAdjacentHTML('beforeend', html);
  }

  /* ── Focus search ───────────────────────────────── */
  function _focusSearch() {
    const inp = document.querySelector('.bn-hero-search input') ||
                document.querySelector('.bn-search-pill input') ||
                document.querySelector('.bn-search-input');
    if (inp) { inp.focus(); inp.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    else window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  /* ── Public API ─────────────────────────────────── */
  return {
    init, injectFooter, logout, openRegModal, openUserLogin, getAuth,
    _toggleDrop, _openMobile, _closeMobile, _closeMobileIfOverlay, _focusSearch,
    _toggleTheme, _toggleLang,
  };

})();

/* Auto-init on DOM ready */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { BunyanNav.init(); BunyanNav.injectFooter(); bnInitPillsScroll(); });
} else {
  BunyanNav.init();
  BunyanNav.injectFooter();
  bnInitPillsScroll();
}

/* ════════════════════════════════════════════════════
   Pills Scroll UX — arrows + fades + hint
   Auto-initialises any element with [data-pills-scroll]
════════════════════════════════════════════════════ */
function bnInitPillsScroll() {
  document.querySelectorAll('[data-pills-scroll]').forEach(function(scroller) {
    var host = scroller.parentElement;

    /* Mark host for CSS; set position only if host is unpositioned */
    host.classList.add('bn-pills-host');
    if (getComputedStyle(host).position === 'static') {
      host.style.position = 'relative';
    }

    /* Build fades */
    var fadeEnd   = document.createElement('div');
    var fadeStart = document.createElement('div');
    fadeEnd.className   = 'bn-pills-fade bn-pills-fade-end';
    fadeStart.className = 'bn-pills-fade bn-pills-fade-start hidden';
    host.appendChild(fadeEnd);
    host.appendChild(fadeStart);

    /* Build arrows */
    var arrowEnd   = document.createElement('button');
    var arrowStart = document.createElement('button');
    arrowEnd.className   = 'bn-pills-arrow bn-pills-arrow-end';
    arrowStart.className = 'bn-pills-arrow bn-pills-arrow-start hidden';
    /* RTL layout: "end" = left arrow, "start" = right arrow */
    arrowEnd.setAttribute('aria-label', 'تمرير يساراً');
    arrowStart.setAttribute('aria-label', 'تمرير يميناً');
    arrowEnd.innerHTML   = '‹';
    arrowStart.innerHTML = '›';
    host.appendChild(arrowEnd);
    host.appendChild(arrowStart);

    var STEP = 180;

    arrowEnd.addEventListener('click', function() {
      scroller.scrollBy({ left: -STEP, behavior: 'smooth' });
    });
    arrowStart.addEventListener('click', function() {
      scroller.scrollBy({ left: STEP, behavior: 'smooth' });
    });

    function update() {
      var sl  = scroller.scrollLeft;
      var max = scroller.scrollWidth - scroller.clientWidth;
      /* RTL: scrollLeft is negative in Firefox, positive in Chrome */
      var atStart = Math.abs(sl) < 4;
      var atEnd   = Math.abs(sl) >= max - 4;
      var canScroll = max > 4;

      fadeStart.classList.toggle('hidden', atStart || !canScroll);
      arrowStart.classList.toggle('hidden', atStart || !canScroll);
      fadeEnd.classList.toggle('hidden', atEnd || !canScroll);
      arrowEnd.classList.toggle('hidden', atEnd || !canScroll);
    }

    scroller.addEventListener('scroll', update, { passive: true });
    /* Re-check after categories/pills load (ResizeObserver on content) */
    if (window.ResizeObserver) {
      new ResizeObserver(update).observe(scroller);
    }
    update();

    /* Auto-scroll hint — runs once, only if scrollable */
    var hintKey = 'bn-pills-hint-' + (host.id || host.className.split(' ')[0]);
    if (!sessionStorage.getItem(hintKey)) {
      sessionStorage.setItem(hintKey, '1');
      setTimeout(function() {
        if (scroller.scrollWidth <= scroller.clientWidth + 4) return;
        scroller.classList.add('bn-hint-animating');
        scroller.addEventListener('animationend', function() {
          scroller.classList.remove('bn-hint-animating');
        }, { once: true });
      }, 800);
    }
  });
}
