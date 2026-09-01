/**
 * بُنيان — نواة منطقة صاحب المشروع   سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * قاعدة العزل ١ — لا رابط تصفّح للموقع العام في هذا الملف.
 *   الاستثناء الوحيد المصرَّح به هو وجهة الخروج ../login.html.
 *
 * ثلاث شاشات تحتاج المصادقة نفسها والحالات نفسها. الرمز هنا رمز
 * المستخدم لا رمز الشركة — وهذا كل الفرق عن نواة /app.
 */
(function () {
  'use strict';

  var API = '';

  function store(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } }
  function token() { return store('project_user_token'); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function initials(n) {
    return String(n || '').split(/\s+/).slice(0, 2).map(function (w) { return w[0] || ''; }).join('');
  }
  function num(n) { return Number(n || 0).toLocaleString('en-US'); }
  function when(d, opts) {
    if (!d) return '';
    try {
      return new Date(d).toLocaleDateString('ar-IQ',
        opts || { year: 'numeric', month: 'long', day: 'numeric' });
    } catch (e) { return ''; }
  }

  var I = {
    folder:  '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6h4l2 2.5h9A1.5 1.5 0 0 1 21 10v8.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/>',
    bid:     '<path d="M4 20h16"/><path d="M6 16V9M10 16V5M14 16v-8M18 16v-4"/>',
    chat:    '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>',
    pin:     '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    tag:     '<path d="M3 12.5V4.5A1.5 1.5 0 0 1 4.5 3h8L21 11.5 13.5 19z"/><circle cx="7.5" cy="7.5" r="1.3"/>',
    clock:   '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check:   '<path d="M20 6L9 17l-5-5"/>',
    x:       '<path d="M18 6L6 18M6 6l12 12"/>',
    trophy:  '<path d="M8 4h8v5a4 4 0 0 1-8 0z"/><path d="M8 5H5v2a3 3 0 0 0 3 3M16 5h3v2a3 3 0 0 1-3 3"/><path d="M10 13v3h4v-3M8 20h8"/>',
    send:    '<path d="M21 3L3 10.5l7 3 3 7z"/><path d="M21 3l-11 11"/>',
    offline: '<path d="M3 3l18 18"/><path d="M5.5 12.5a9 9 0 0 1 3.2-2.1M2 8.8A14 14 0 0 1 6 6.3M18.5 6.3A14 14 0 0 1 22 8.8M15.4 10.5a9 9 0 0 1 3.1 2"/><circle cx="12" cy="18" r="1"/>',
    empty:   '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18M8 15h8"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 16) + '" height="' + (s || 16) +
      '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  function ApiError(status, detail) {
    this.status = status; this.detail = detail || '';
    this.message = detail || ('HTTP ' + status);
  }
  ApiError.prototype = Object.create(Error.prototype);

  async function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({ Authorization: 'Bearer ' + token() }, opts.headers || {});
    if (opts.body && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      if (typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
    }
    var r = await fetch(API + path, {
      method: opts.method || 'GET', headers: headers, body: opts.body,
      signal: AbortSignal.timeout(opts.timeout || 15000)
    });
    if (r.status === 401) { sessionExpired(); throw new ApiError(401, 'انتهت الجلسة'); }
    if (!r.ok) {
      var detail = '';
      try { detail = (await r.json()).detail || ''; } catch (e) {}
      throw new ApiError(r.status, detail);
    }
    if (r.status === 204) return null;
    try { return await r.json(); } catch (e) { return null; }
  }

  function sessionExpired() {
    try {
      localStorage.removeItem('project_user_token');
      localStorage.removeItem('project_user_id');
    } catch (e) {}
    location.replace('../login.html?role=client&next=' + encodeURIComponent(location.pathname));
  }

  function errText(e) {
    if (e && e.detail) return e.detail;
    if (e && e.status === 403) return 'ليس لديك صلاحية لهذا الإجراء.';
    if (e && e.status === 429) return 'محاولات كثيرة — انتظر قبل المحاولة مجدداً.';
    if (e && e.status === 503) return 'الخدمة غير متاحة مؤقتاً — حاول بعد قليل.';
    return 'تعذّر الاتصال بالخادم — أعد المحاولة.';
  }

  /* حالات الزرّ الخمس — نفس عقد لوحة الإدارة */
  function runAction(btn, fn, opts) {
    opts = opts || {};
    if (btn.classList.contains('is-loading')) return Promise.resolve();
    var original = btn.innerHTML;
    btn.classList.add('is-loading');
    btn.setAttribute('aria-busy', 'true');
    btn.innerHTML = '<span class="me-spin" aria-hidden="true"></span><span>' +
      esc(opts.loading || 'جارٍ...') + '</span>';
    return Promise.resolve().then(fn)
      .then(function (res) {
        btn.classList.remove('is-loading');
        btn.classList.add('is-success');
        btn.innerHTML = svg(I.check, 15) + '<span>' + esc(opts.success || 'تمّ') + '</span>';
        setTimeout(function () {
          btn.classList.remove('is-success');
          btn.removeAttribute('aria-busy');
          btn.innerHTML = original;
          if (opts.then) opts.then(res);
        }, opts.hold || 1200);
        return res;
      })
      .catch(function (e) {
        btn.classList.remove('is-loading');
        btn.removeAttribute('aria-busy');
        btn.innerHTML = original;
        toast(errText(e), 'err');
        throw e;
      });
  }

  function skeleton(n, h) {
    var out = '';
    for (var i = 0; i < (n || 3); i++) out += '<div class="me-skel" style="height:' + (h || 76) + 'px"></div>';
    return out;
  }
  function emptyState(title, desc, actionHTML, icon) {
    return '<div class="me-state">' + svg(icon || I.empty, 38) +
      '<div class="me-state-t">' + esc(title) + '</div>' +
      (desc ? '<div class="me-state-d">' + esc(desc) + '</div>' : '') +
      (actionHTML || '') + '</div>';
  }
  function errorState(msg) {
    return '<div class="me-state">' + svg(I.offline, 38) +
      '<div class="me-state-t">تعذّر تحميل البيانات</div>' +
      '<div class="me-state-d">' + esc(msg || 'تحقّق من اتصالك ثم أعد المحاولة.') + '</div>' +
      '<button class="bn-btn" type="button" data-me-retry>إعادة المحاولة</button></div>';
  }
  function onRetry(el, fn) {
    var b = el.querySelector('[data-me-retry]');
    if (b) b.onclick = fn;
  }

  var toastEl = null;
  function toast(msg, kind) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'me-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.className = 'me-toast is-on' + (kind === 'err' ? ' is-err' : '');
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.className = 'me-toast'; }, 3200);
  }

  function confirmSheet(title, msg, confirmLabel) {
    return new Promise(function (resolve) {
      var ov = document.createElement('div');
      ov.className = 'me-ov';
      ov.innerHTML =
        '<div class="me-sheet" role="dialog" aria-modal="true">' +
          '<div class="me-sheet-h"><h2>' + esc(title) + '</h2></div>' +
          '<div class="me-sheet-b"><p class="me-note">' + esc(msg) + '</p>' +
            '<div class="me-row-end">' +
              '<button class="bn-btn bn-btn-ghost" type="button" data-no>إلغاء</button>' +
              '<button class="bn-btn" type="button" data-yes>' + esc(confirmLabel || 'تأكيد') + '</button>' +
            '</div></div></div>';
      document.body.appendChild(ov);
      requestAnimationFrame(function () { ov.classList.add('is-on'); });
      function done(v) {
        ov.classList.remove('is-on');
        setTimeout(function () { ov.remove(); }, 200);
        document.removeEventListener('keydown', onKey);
        resolve(v);
      }
      function onKey(e) { if (e.key === 'Escape') done(false); }
      ov.querySelector('[data-no]').onclick = function () { done(false); };
      ov.querySelector('[data-yes]').onclick = function () { done(true); };
      ov.onclick = function (e) { if (e.target === ov) done(false); };
      document.addEventListener('keydown', onKey);
    });
  }

  var CSS = `
.me-wrap{max-width:1000px;margin-inline:auto;padding:var(--bn-s6) var(--bn-s5) var(--bn-s14)}
@media(max-width:560px){.me-wrap{padding:var(--bn-s5) var(--bn-s4) var(--bn-s14)}}
.me-head{margin-block-end:var(--bn-s6)}
.me-head h1{font:var(--bn-t-h1);margin:0 0 6px;letter-spacing:-.01em}
.me-head p{font:var(--bn-t-sm);color:var(--bn-ink-3);margin:0;max-width:62ch;line-height:1.75}
@media(max-width:560px){.me-head h1{font-size:22px}}

.me-list{display:flex;flex-direction:column;gap:var(--bn-s2)}
.me-card{padding:var(--bn-s5);border-radius:var(--bn-r-lg)}
.me-card-h{display:flex;align-items:flex-start;justify-content:space-between;
  gap:var(--bn-s4);flex-wrap:wrap}
.me-t{font:600 15.5px/1.5 var(--bn-font);margin:0 0 6px}
.me-m{font:var(--bn-t-cap);color:var(--bn-ink-3);display:flex;align-items:center;
  gap:var(--bn-s3);flex-wrap:wrap}
.me-m i{display:inline-flex;align-items:center;gap:4px;font-style:normal}
.me-bud{font:700 19px/1.2 var(--bn-mono);color:var(--bn-ac);
  font-variant-numeric:tabular-nums;direction:ltr;display:block}
.me-bud-c{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:3px}
.me-f{display:flex;align-items:center;justify-content:space-between;gap:var(--bn-s3);
  flex-wrap:wrap;margin-block-start:var(--bn-s4);padding-block-start:var(--bn-s3);
  border-block-start:1px solid var(--bn-line-soft)}
.me-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;
  border-radius:var(--bn-r-pill);font:var(--bn-t-cap);white-space:nowrap}
.me-tag-on{background:var(--bn-ac-bg);color:var(--bn-ac);border:1px solid var(--bn-ac-line)}
.me-tag-off{background:transparent;color:var(--bn-ink-3);border:1px solid var(--bn-line)}
.me-av{width:40px;height:40px;border-radius:var(--bn-r);flex:none;display:grid;
  place-items:center;overflow:hidden;background:var(--bn-ac-bg);color:var(--bn-ac);
  border:1px solid var(--bn-ac-line);font:700 15px/1 var(--bn-font)}
.me-av img{width:100%;height:100%;object-fit:cover}

.me-state{text-align:center;padding:var(--bn-s12) var(--bn-s5);
  border:1px dashed var(--bn-line);border-radius:var(--bn-r-lg)}
.me-state svg{stroke:var(--bn-ink-3);fill:none;stroke-width:1.3;margin-block-end:var(--bn-s3)}
.me-state-t{font:500 15px/1.5 var(--bn-font);color:var(--bn-ink-2)}
.me-state-d{font:var(--bn-t-sm);color:var(--bn-ink-3);margin-block-start:6px;
  max-width:46ch;margin-inline:auto;line-height:1.7}
.me-state .bn-btn{margin-block-start:var(--bn-s4)}
.me-skel{border-radius:var(--bn-r-lg);background:var(--bn-glass-tint);
  border:1px solid var(--bn-line-soft);margin-block-end:var(--bn-s2);
  position:relative;overflow:hidden}
.me-skel::after{content:"";position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,var(--bn-glass),transparent);
  animation:me-sweep 1.4s infinite}
@keyframes me-sweep{to{transform:translateX(300%)}}

.bn-btn:active:not(:disabled):not(.is-loading){transform:translateY(1px);box-shadow:none}
.bn-btn.is-loading{pointer-events:none;opacity:.82}
.bn-btn.is-success{pointer-events:none}
.bn-btn.is-loading>span,.bn-btn.is-success>span{display:inline-flex;align-items:center}
.me-spin{width:14px;height:14px;flex:none;border-radius:50%;border:2px solid currentColor;
  border-block-start-color:transparent;margin-inline-end:7px;animation:me-spin .7s linear infinite}
@keyframes me-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.me-spin{animation-duration:2s}}

.me-toast{position:fixed;inset-block-end:var(--bn-s6);inset-inline:0;margin-inline:auto;
  width:max-content;max-width:88vw;z-index:500;padding:12px var(--bn-s5);
  border-radius:var(--bn-r-pill);background:var(--bn-ink);color:var(--bn-bg);
  font:var(--bn-t-sm);box-shadow:var(--bn-sh-3);opacity:0;transform:translateY(12px);
  pointer-events:none;transition:opacity var(--bn-mid),transform var(--bn-mid)}
.me-toast.is-on{opacity:1;transform:none}
.me-toast.is-err{background:var(--bn-ac);color:var(--bn-ac-on)}

.me-ov{position:fixed;inset:0;z-index:600;display:flex;align-items:center;
  justify-content:center;background:var(--bn-scrim);opacity:0;transition:opacity var(--bn-mid)}
.me-ov.is-on{opacity:1}
.me-sheet{width:100%;max-width:480px;margin:var(--bn-s5);background:var(--bn-surface);
  border:1px solid var(--bn-line);border-radius:var(--bn-r-lg);box-shadow:var(--bn-sh-3)}
.me-sheet-h{padding:var(--bn-s5);border-block-end:1px solid var(--bn-line-soft)}
.me-sheet-h h2{font:var(--bn-t-h3);margin:0}
.me-sheet-b{padding:var(--bn-s5)}
.me-note{font:var(--bn-t-sm);color:var(--bn-ink-2);line-height:1.8;margin:0}
.me-row-end{display:flex;align-items:center;justify-content:flex-end;gap:var(--bn-s2);
  flex-wrap:wrap;margin-block-start:var(--bn-s5)}
`;

  function injectCSS() {
    if (document.getElementById('me-style')) return;
    var s = document.createElement('style');
    s.id = 'me-style'; s.textContent = CSS;
    document.head.appendChild(s);
  }
  injectCSS();

  window.MeCore = {
    api: api, ApiError: ApiError, errText: errText, token: token,
    esc: esc, initials: initials, num: num, when: when,
    icons: I, svg: svg, runAction: runAction,
    skeleton: skeleton, emptyState: emptyState, errorState: errorState, onRetry: onRetry,
    toast: toast, confirm: confirmSheet, sessionExpired: sessionExpired
  };
})();
