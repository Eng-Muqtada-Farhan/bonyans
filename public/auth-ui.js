/**
 * بُنيان — Auth UI Bridge v1.1
 * UI layer only — listens to auth events and handles DOM responses.
 * No auth logic. No token access. No JWT parsing.
 * Load order: auth-core.js → auth-ui.js → bunyan-nav.js
 *
 * v1.1: injects a universal login modal on pages that have no native one.
 */
(function () {
  'use strict';

  /* ── Inject universal login modal (once) ────────────────── */
  function _ensureModal() {
    if (document.getElementById('bn-login-modal-overlay')) return;

    var style = document.createElement('style');
    style.textContent = [
      '#bn-login-modal-overlay{position:fixed;inset:0;z-index:500;',
        'background:rgba(10,22,40,0.55);backdrop-filter:blur(6px);',
        '-webkit-backdrop-filter:blur(6px);',
        'display:none;align-items:flex-end;justify-content:center;}',
      '#bn-login-modal-overlay.open{display:flex}',
      '#bn-lm-box{position:relative;background:rgba(255,255,255,0.94);',
        'backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);',
        'border-radius:24px 24px 0 0;border:1.5px solid rgba(255,255,255,0.85);',
        'border-bottom:none;padding:20px 20px 44px;',
        'width:100%;max-width:480px;max-height:90vh;overflow-y:auto;',
        'animation:_bnSlideUp 0.3s ease;font-family:"Cairo",sans-serif;}',
      '[data-theme="dark"] #bn-lm-box{background:rgba(8,14,28,0.94);',
        'border-color:rgba(255,255,255,0.12);}',
      '@keyframes _bnSlideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}',
      '.bn-lm-handle{width:36px;height:4px;background:rgba(27,58,107,0.20);',
        'border-radius:2px;margin:0 auto 14px;}',
      '.bn-lm-close{position:absolute;top:14px;left:14px;width:30px;height:30px;',
        'background:rgba(27,58,107,0.08);border:none;border-radius:8px;',
        'font-size:16px;cursor:pointer;color:#5A7090;display:flex;',
        'align-items:center;justify-content:center;}',
      '.bn-lm-title{font-size:18px;font-weight:900;color:#1B3A6B;',
        'text-align:center;margin-bottom:4px;}',
      '[data-theme="dark"] .bn-lm-title{color:#D4A017}',
      '.bn-lm-sub{font-size:12px;color:#8899AA;text-align:center;margin-bottom:16px;}',
      '.bn-lm-tabs{display:flex;gap:4px;margin-bottom:14px;}',
      '.bn-lm-tab{flex:1;padding:8px;border:1.5px solid rgba(27,58,107,0.15);',
        'border-radius:8px;background:rgba(255,255,255,0.5);color:#5A7090;',
        'font-family:"Cairo",sans-serif;font-size:13px;cursor:pointer;transition:all 0.18s;}',
      '.bn-lm-tab.active{background:#1B3A6B;color:#fff;font-weight:700;border-color:#1B3A6B;}',
      '[data-theme="dark"] .bn-lm-tab{background:rgba(255,255,255,0.06);',
        'border-color:rgba(255,255,255,0.10);color:#8899AA;}',
      '[data-theme="dark"] .bn-lm-tab.active{background:#D4A017;border-color:#D4A017;color:#0A1220;}',
      '.bn-lm-inp{width:100%;padding:11px 14px;',
        'border:1.5px solid rgba(27,58,107,0.15);border-radius:10px;',
        'background:rgba(255,255,255,0.8);color:#0F2347;',
        'font-family:"Cairo",sans-serif;font-size:14px;margin-bottom:10px;',
        'direction:ltr;outline:none;box-sizing:border-box;}',
      '[data-theme="dark"] .bn-lm-inp{background:rgba(255,255,255,0.07);',
        'border-color:rgba(255,255,255,0.12);color:#E8EAF6;}',
      '.bn-lm-inp:focus{border-color:#1B3A6B;}',
      '.bn-lm-btn{width:100%;padding:12px;background:#1B3A6B;color:#fff;border:none;',
        'border-radius:10px;font-family:"Cairo",sans-serif;font-size:15px;',
        'font-weight:700;cursor:pointer;transition:opacity 0.2s;}',
      '.bn-lm-btn:hover{opacity:0.85;}',
      '.bn-lm-btn:disabled{opacity:0.5;cursor:default;}',
      '.bn-lm-msg{font-size:13px;min-height:18px;margin-top:10px;text-align:center;}',
      '.bn-lm-ok{color:#16a34a;}.bn-lm-err{color:#dc2626;}',
    ].join('');
    document.head.appendChild(style);

    var overlay = document.createElement('div');
    overlay.id = 'bn-login-modal-overlay';
    overlay.innerHTML =
      '<div id="bn-lm-box">' +
        '<div class="bn-lm-handle"></div>' +
        '<button class="bn-lm-close" id="bn-lm-close-btn">✕</button>' +
        '<div class="bn-lm-title">بُنيان</div>' +
        '<div class="bn-lm-sub">تسجيل الدخول أو إنشاء حساب</div>' +
        '<div class="bn-lm-tabs">' +
          '<button class="bn-lm-tab active" id="bn-lm-t-login">دخول</button>' +
          '<button class="bn-lm-tab"        id="bn-lm-t-reg">حساب جديد</button>' +
        '</div>' +
        '<div id="bn-lm-f-login">' +
          '<input class="bn-lm-inp" id="bn-lm-email" type="email"    placeholder="البريد الإلكتروني">' +
          '<input class="bn-lm-inp" id="bn-lm-pass"  type="password" placeholder="كلمة المرور">' +
          '<button class="bn-lm-btn" id="bn-lm-btn-login">دخول</button>' +
        '</div>' +
        '<div id="bn-lm-f-reg" style="display:none">' +
          '<input class="bn-lm-inp" id="bn-lm-rname"  type="text"     placeholder="الاسم الكامل" dir="rtl">' +
          '<input class="bn-lm-inp" id="bn-lm-remail" type="email"    placeholder="البريد الإلكتروني">' +
          '<input class="bn-lm-inp" id="bn-lm-rpass"  type="password" placeholder="كلمة المرور (8 أحرف على الأقل)">' +
          '<button class="bn-lm-btn" id="bn-lm-btn-reg">إنشاء حساب</button>' +
        '</div>' +
        '<div class="bn-lm-msg" id="bn-lm-msg"></div>' +
      '</div>';

    document.body.appendChild(overlay);

    /* Wire up events — no inline onclick, safe approach */
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) _bnLmClose();
    });
    document.getElementById('bn-lm-close-btn').addEventListener('click', _bnLmClose);
    document.getElementById('bn-lm-t-login').addEventListener('click', function () { _bnLmSwitch('login'); });
    document.getElementById('bn-lm-t-reg').addEventListener('click',   function () { _bnLmSwitch('reg'); });
    document.getElementById('bn-lm-btn-login').addEventListener('click', function () { _bnLmDoAuth('login'); });
    document.getElementById('bn-lm-btn-reg').addEventListener('click',   function () { _bnLmDoAuth('reg'); });
  }

  function _bnLmClose() {
    var o = document.getElementById('bn-login-modal-overlay');
    if (o) o.classList.remove('open');
  }

  function _bnLmSwitch(tab) {
    var fLogin = document.getElementById('bn-lm-f-login');
    var fReg   = document.getElementById('bn-lm-f-reg');
    var tLogin = document.getElementById('bn-lm-t-login');
    var tReg   = document.getElementById('bn-lm-t-reg');
    if (!fLogin) return;
    fLogin.style.display = tab === 'login' ? 'block' : 'none';
    fReg.style.display   = tab === 'reg'   ? 'block' : 'none';
    tLogin.classList.toggle('active', tab === 'login');
    tReg.classList.toggle('active',   tab === 'reg');
    document.getElementById('bn-lm-msg').textContent = '';
  }

  function _bnLmDoAuth(mode) {
    var msg   = document.getElementById('bn-lm-msg');
    var btn   = document.getElementById(mode === 'login' ? 'bn-lm-btn-login' : 'bn-lm-btn-reg');
    var body, url;

    if (mode === 'login') {
      var email = (document.getElementById('bn-lm-email').value || '').trim();
      var pass  = document.getElementById('bn-lm-pass').value || '';
      if (!email || !pass) { _bnLmMsg('يرجى ملء جميع الحقول', 'err'); return; }
      body = { email: email, password: pass };
      url  = '/auth/login';
    } else {
      var rname  = (document.getElementById('bn-lm-rname').value  || '').trim();
      var remail = (document.getElementById('bn-lm-remail').value || '').trim();
      var rpass  = document.getElementById('bn-lm-rpass').value || '';
      if (!remail || !rpass) { _bnLmMsg('يرجى ملء جميع الحقول', 'err'); return; }
      body = { email: remail, password: rpass, display_name: rname };
      url  = '/auth/register';
    }

    _bnLmMsg('جارٍ التحقق...', '');
    if (btn) btn.disabled = true;

    fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok, d: d }; });
    }).then(function (res) {
      if (btn) btn.disabled = false;
      if (!res.ok) {
        _bnLmMsg(res.d.detail || 'بريد إلكتروني أو كلمة مرور غير صحيحة', 'err');
        return;
      }
      var d = res.d;
      localStorage.setItem('project_user_token', d.token || '');
      localStorage.setItem('project_user_id',    String(d.user_id || ''));
      localStorage.setItem('project_user_name',  d.display_name || '');
      /* If this login also returned a company_id, save it so auth-core detects company role */
      if (d.company_id) {
        localStorage.setItem('company_id', String(d.company_id));
      }
      _bnLmMsg(mode === 'login' ? 'تم الدخول بنجاح ✓' : 'تم إنشاء الحساب بنجاح ✓', 'ok');
      setTimeout(function () {
        _bnLmClose();
        window.dispatchEvent(new Event('auth:login:success'));
        /* Refresh nav to reflect new auth state */
        if (window.BunyanNav && typeof BunyanNav.init === 'function') {
          var nav = document.getElementById('bn-nav');
          if (nav) nav.remove();
          var footer = document.getElementById('bn-footer');
          if (footer) footer.remove();
          var pill = document.getElementById('bn-pill-nav');
          if (pill) pill.remove();
          BunyanNav.init();
          BunyanNav.injectFooter();
        }
      }, 700);
    }).catch(function () {
      if (btn) btn.disabled = false;
      _bnLmMsg('تعذّر الاتصال بالسيرفر', 'err');
    });
  }

  function _bnLmMsg(txt, type) {
    var el = document.getElementById('bn-lm-msg');
    if (!el) return;
    el.textContent = txt;
    el.className = 'bn-lm-msg' + (type ? ' bn-lm-' + type : '');
  }

  /* ── Login modal handler ─────────────────────────────────── */
  window.addEventListener('auth:login:open', function () {
    var modal = document.getElementById('loginOverlay') ||
                document.getElementById('overlayPost');
    if (modal) {
      modal.classList.add('open');
      return;
    }
    /* No native modal on this page — use universal injected modal */
    _ensureModal();
    var injected = document.getElementById('bn-login-modal-overlay');
    if (injected) {
      _bnLmSwitch('login');
      document.getElementById('bn-lm-msg').textContent = '';
      injected.classList.add('open');
    }
  });

  /* ── Logout redirect handler ─────────────────────────────── */
  window.addEventListener('auth:logout', function () {
    window.location.href = 'index.html';
  });

})();
