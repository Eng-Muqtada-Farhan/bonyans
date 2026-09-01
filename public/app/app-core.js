/**
 * بُنيان — نواة لوحة الشركة  سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * قاعدة العزل ١ — لا رابط تصفّح للموقع العام في هذا الملف.
 *    الاستثناء الوحيد المصرَّح به هو «معاينة ملفي العام» الذي
 *    تبنيه profile.html بنفسها بجوار زر الحفظ، لا هذه النواة.
 *
 * سبب وجودها: تسع شاشات تحتاج المصادقة نفسها ونداء الشبكة نفسه
 * وحالات الفراغ والخطأ نفسها. تسع نسخ تفترق حتماً.
 *
 * تحتوي: الرمز والمصادقة · api() بمعالجة الأخطاء موحّدة ·
 *        الأيقونات · الحالات · الرسائل اللحظية · نافذة الحوار ·
 *        رفع الصور إلى ImageKit عبر /company/upload
 */
(function () {
  'use strict';

  var API = '';

  function store(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } }
  /* رمز الشركة القديم أو رمز مستخدم عضو في شركة — الخادم يقبلهما */
  function token() { return store('bn_token'); }

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
    building: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2"/>',
    image:    '<rect x="3" y="4.5" width="18" height="15" rx="1.5"/><circle cx="8.5" cy="10" r="1.6"/><path d="M21 16l-5-5-9 8.5"/>',
    market:   '<path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3z"/><path d="M8.5 8V6a3.5 3.5 0 0 1 7 0v2"/>',
    tag:      '<path d="M3 12.5V4.5A1.5 1.5 0 0 1 4.5 3h8L21 11.5 13.5 19z"/><circle cx="7.5" cy="7.5" r="1.3"/>',
    chat:     '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>',
    star:     '<path d="M12 3.7l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z"/>',
    card:     '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    eye:      '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    wa:       '<path d="M21 11.5a8.4 8.4 0 0 1-12.3 7.5L3.5 20.5l1.6-5A8.5 8.5 0 1 1 21 11.5z"/>',
    bid:      '<path d="M4 20h16"/><path d="M6 16V9M10 16V5M14 16v-8M18 16v-4"/>',
    check:    '<path d="M20 6L9 17l-5-5"/>',
    x:        '<path d="M18 6L6 18M6 6l12 12"/>',
    plus:     '<path d="M12 5v14M5 12h14"/>',
    trash:    '<path d="M4 7h16M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7"/><path d="M6 7l1 12.5A1.5 1.5 0 0 0 8.5 21h7a1.5 1.5 0 0 0 1.5-1.5L18 7"/>',
    upload:   '<path d="M12 16V4M8 8l4-4 4 4"/><path d="M4 16v2.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V16"/>',
    clock:    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    pin:      '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    offline:  '<path d="M3 3l18 18"/><path d="M5.5 12.5a9 9 0 0 1 3.2-2.1M2 8.8A14 14 0 0 1 6 6.3M18.5 6.3A14 14 0 0 1 22 8.8M15.4 10.5a9 9 0 0 1 3.1 2"/><circle cx="12" cy="18" r="1"/>',
    empty:    '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18M8 15h8"/>',
    lock:     '<rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    send:     '<path d="M21 3L3 10.5l7 3 3 7z"/><path d="M21 3l-11 11"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 16) + '" height="' + (s || 16) +
      '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* ── الشبكة ─────────────────────────────────────────────────
     خطأ واحد مصنَّف بدل تسع معالجات تفترق. 401 يعني انتهاء
     الجلسة فيُعاد إلى الدخول — لا رسالة غامضة. */
  function ApiError(status, detail) {
    this.status = status;
    this.detail = detail || '';
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
      method: opts.method || 'GET',
      headers: headers,
      body: opts.body,
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
      localStorage.removeItem('bn_token');
    } catch (e) {}
    /* ../login.html — الاستثناء المصرَّح به: العزل يحكم الجلسة
       لا نهايتها. من انتهت جلسته لم يعد شركة. */
    location.replace('../login.html?role=company&next=' +
      encodeURIComponent(location.pathname));
  }

  /** رسالة الخطأ التي تُعرض للمستخدم — من الخادم إن أرسل نصاً. */
  function errText(e) {
    if (e && e.detail) return e.detail;
    if (e && e.status === 403) return 'ليس لديك صلاحية لهذا الإجراء.';
    if (e && e.status === 429) return 'محاولات كثيرة — انتظر قبل المحاولة مجدداً.';
    if (e && e.status === 503) return 'الخدمة غير متاحة مؤقتاً — حاول بعد قليل.';
    return 'تعذّر الاتصال بالخادم — أعد المحاولة.';
  }

  /* ── الحالات ───────────────────────────────────────────────── */
  function skeleton(n, h) {
    var out = '';
    for (var i = 0; i < (n || 3); i++) {
      out += '<div class="ac-skel" style="height:' + (h || 76) + 'px"></div>';
    }
    return out;
  }
  function emptyState(title, desc, actionHTML, icon) {
    return '<div class="ac-state">' + svg(icon || I.empty, 38) +
      '<div class="ac-state-t">' + esc(title) + '</div>' +
      (desc ? '<div class="ac-state-d">' + esc(desc) + '</div>' : '') +
      (actionHTML || '') + '</div>';
  }
  function errorState(msg) {
    return '<div class="ac-state">' + svg(I.offline, 38) +
      '<div class="ac-state-t">تعذّر تحميل البيانات</div>' +
      '<div class="ac-state-d">' + esc(msg || 'تحقّق من اتصالك ثم أعد المحاولة.') + '</div>' +
      '<button class="bn-btn" type="button" data-ac-retry>إعادة المحاولة</button></div>';
  }
  /** يربط زر إعادة المحاولة داخل حاوية بدالة إعادة التحميل. */
  function onRetry(el, fn) {
    var b = el.querySelector('[data-ac-retry]');
    if (b) b.onclick = fn;
  }

  /* ── رسالة لحظية ───────────────────────────────────────────── */
  var toastEl = null;
  function toast(msg, kind) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'ac-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.className = 'ac-toast is-on' + (kind === 'err' ? ' is-err' : '');
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.className = 'ac-toast'; }, 3200);
  }

  /* ── نافذة حوار ────────────────────────────────────────────── */
  function sheet(title, bodyHTML, opts) {
    opts = opts || {};
    var ov = document.createElement('div');
    ov.className = 'ac-ov';
    ov.innerHTML =
      '<div class="ac-sheet" role="dialog" aria-modal="true">' +
        '<div class="ac-sheet-h"><h2>' + esc(title) + '</h2>' +
          '<button class="ac-x" type="button" aria-label="إغلاق">' + svg(I.x, 18) + '</button></div>' +
        '<div class="ac-sheet-b">' + bodyHTML + '</div>' +
      '</div>';
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add('is-on'); });

    function close() {
      ov.classList.remove('is-on');
      setTimeout(function () { ov.remove(); }, 200);
      document.removeEventListener('keydown', onKey);
      if (opts.onClose) opts.onClose();
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    ov.querySelector('.ac-x').onclick = close;
    ov.onclick = function (e) { if (e.target === ov) close(); };
    document.addEventListener('keydown', onKey);
    var first = ov.querySelector('input,textarea,select');
    if (first) first.focus();
    return { el: ov, close: close };
  }

  function confirmSheet(title, msg, confirmLabel) {
    return new Promise(function (resolve) {
      var s = sheet(title,
        '<p class="ac-note">' + esc(msg) + '</p>' +
        '<div class="ac-row-end">' +
          '<button class="bn-btn bn-btn-ghost" type="button" data-no>إلغاء</button>' +
          '<button class="bn-btn" type="button" data-yes>' + esc(confirmLabel || 'تأكيد') + '</button>' +
        '</div>',
        { onClose: function () { resolve(false); } });
      s.el.querySelector('[data-no]').onclick = function () { s.close(); };
      s.el.querySelector('[data-yes]').onclick = function () {
        s.el.querySelector('[data-yes]').disabled = true;
        resolve(true);
        s.close();
      };
    });
  }

  /* ── رفع صورة إلى ImageKit عبر الخادم ───────────────────────
     المفتاح الخاص لا يغادر الخادم — الرفع يمرّ بـ /company/upload
     لا مباشرةً من المتصفّح. */
  var MAX_BYTES = 5 * 1024 * 1024;
  var OK_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

  async function uploadImage(file) {
    if (OK_TYPES.indexOf(file.type) === -1) {
      throw new ApiError(400, 'صيغة غير مدعومة — JPG أو PNG أو WEBP أو GIF.');
    }
    if (file.size > MAX_BYTES) {
      throw new ApiError(400, 'الصورة أكبر من ٥ ميغابايت.');
    }
    var fd = new FormData();
    fd.append('file', file);
    var d = await api('/company/upload', { method: 'POST', body: fd, timeout: 60000 });
    if (!d || !d.url) throw new ApiError(500, 'لم يُرجع الخادم رابط الصورة.');
    return d.url;
  }

  /* ── أنماط مشتركة لكل الشاشات ──────────────────────────────── */
  var CSS = `
.ac-wrap{max-width:940px;padding:var(--bn-s6) var(--bn-s6) var(--bn-s14)}
@media(max-width:900px){.ac-wrap{padding:var(--bn-s5) var(--bn-s4) var(--bn-s14)}}
.ac-head{margin-block-end:var(--bn-s6)}
.ac-head h1{font:var(--bn-t-h1);margin:0 0 6px;letter-spacing:-.01em}
.ac-head p{font:var(--bn-t-sm);color:var(--bn-ink-3);margin:0;max-width:60ch;line-height:1.75}
.ac-head-row{display:flex;align-items:flex-start;justify-content:space-between;
  gap:var(--bn-s4);flex-wrap:wrap}
@media(max-width:560px){.ac-head h1{font-size:22px}}

.ac-sec{margin-block-end:var(--bn-s8)}
.ac-sec-t{font:var(--bn-t-h3);margin:0 0 var(--bn-s4);display:flex;align-items:center;gap:9px}
.ac-sec-t::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--bn-ac);flex:none}
.ac-sec-t .n{font:var(--bn-t-cap);color:var(--bn-ink-3)}

/* بطاقات الأرقام */
.ac-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:var(--bn-s3)}
.ac-stat{padding:var(--bn-s5);border-radius:var(--bn-r-lg)}
.ac-stat-l{font:var(--bn-t-cap);color:var(--bn-ink-3);display:flex;align-items:center;
  gap:6px;margin-block-end:8px}
.ac-stat-n{font:700 26px/1.1 var(--bn-mono);color:var(--bn-ac);
  font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.ac-stat-d{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:6px}

/* قوائم */
.ac-list{display:flex;flex-direction:column;gap:var(--bn-s2)}
.ac-item{display:flex;align-items:center;gap:var(--bn-s4);padding:var(--bn-s4);
  border-radius:var(--bn-r-lg)}
.ac-item-b{flex:1;min-width:0}
.ac-item-t{font:500 14.5px/1.4 var(--bn-font);margin:0 0 4px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ac-item-m{font:var(--bn-t-cap);color:var(--bn-ink-3);display:flex;align-items:center;
  gap:var(--bn-s3);flex-wrap:wrap}
.ac-item-m i{display:inline-flex;align-items:center;gap:4px;font-style:normal}
.ac-item-act{display:flex;align-items:center;gap:var(--bn-s2);flex:none}
@media(max-width:640px){
  .ac-item{flex-wrap:wrap}
  .ac-item-act{width:100%;justify-content:flex-end}
}

/* نماذج */
.ac-form{max-width:620px}
.ac-fr{margin-block-end:var(--bn-s4)}
.ac-fr label{display:block;font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-end:6px}
.ac-fr input,.ac-fr select,.ac-fr textarea{width:100%;min-height:44px;
  padding:11px var(--bn-s4);border:1px solid var(--bn-line);border-radius:var(--bn-r);
  background:var(--bn-bg);color:var(--bn-ink);font:400 14px/1.5 var(--bn-font)}
.ac-fr input:focus,.ac-fr select:focus,.ac-fr textarea:focus{outline:none;border-color:var(--bn-ac)}
.ac-fr textarea{resize:vertical;min-height:96px}
.ac-fr-hint{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:5px}
.ac-f2{display:grid;grid-template-columns:1fr 1fr;gap:var(--bn-s3)}
@media(max-width:560px){.ac-f2{grid-template-columns:1fr}}
.ac-row-end{display:flex;align-items:center;justify-content:flex-end;gap:var(--bn-s2);
  flex-wrap:wrap;margin-block-start:var(--bn-s5)}
.ac-note{font:var(--bn-t-sm);color:var(--bn-ink-2);line-height:1.8;margin:0}

/* شارات */
.ac-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;
  border-radius:var(--bn-r-pill);font:var(--bn-t-cap);white-space:nowrap}
.ac-tag-on{background:var(--bn-ac-bg);color:var(--bn-ac);border:1px solid var(--bn-ac-line)}
.ac-tag-off{background:transparent;color:var(--bn-ink-3);border:1px solid var(--bn-line)}

/* الحالات */
.ac-state{text-align:center;padding:var(--bn-s12) var(--bn-s5);
  border:1px dashed var(--bn-line);border-radius:var(--bn-r-lg)}
.ac-state svg{stroke:var(--bn-ink-3);fill:none;stroke-width:1.3;margin-block-end:var(--bn-s3)}
.ac-state-t{font:500 15px/1.5 var(--bn-font);color:var(--bn-ink-2)}
.ac-state-d{font:var(--bn-t-sm);color:var(--bn-ink-3);margin-block-start:6px;
  max-width:46ch;margin-inline:auto;line-height:1.7}
.ac-state .bn-btn{margin-block-start:var(--bn-s4)}
.ac-skel{border-radius:var(--bn-r-lg);background:var(--bn-glass-tint);
  border:1px solid var(--bn-line-soft);margin-block-end:var(--bn-s2);
  position:relative;overflow:hidden}
.ac-skel::after{content:"";position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,var(--bn-glass),transparent);
  animation:ac-sweep 1.4s infinite}
@keyframes ac-sweep{to{transform:translateX(300%)}}

/* رسالة لحظية */
.ac-toast{position:fixed;inset-block-end:var(--bn-s6);inset-inline:0;margin-inline:auto;
  width:max-content;max-width:88vw;z-index:500;padding:12px var(--bn-s5);
  border-radius:var(--bn-r-pill);background:var(--bn-ink);color:var(--bn-bg);
  font:var(--bn-t-sm);box-shadow:var(--bn-sh-3);opacity:0;transform:translateY(12px);
  pointer-events:none;transition:opacity var(--bn-mid),transform var(--bn-mid)}
.ac-toast.is-on{opacity:1;transform:none}
.ac-toast.is-err{background:var(--bn-ac);color:var(--bn-ac-on)}

/* نافذة حوار */
.ac-ov{position:fixed;inset:0;z-index:600;display:flex;align-items:flex-end;
  justify-content:center;background:var(--bn-scrim);opacity:0;
  transition:opacity var(--bn-mid)}
.ac-ov.is-on{opacity:1}
@media(min-width:640px){.ac-ov{align-items:center}}
.ac-sheet{width:100%;max-width:560px;max-height:90vh;overflow-y:auto;
  background:var(--bn-surface);border:1px solid var(--bn-line);
  border-radius:var(--bn-r-lg) var(--bn-r-lg) 0 0;box-shadow:var(--bn-sh-3);
  transform:translateY(16px);transition:transform var(--bn-mid)}
.ac-ov.is-on .ac-sheet{transform:none}
@media(min-width:640px){.ac-sheet{border-radius:var(--bn-r-lg)}}
.ac-sheet-h{display:flex;align-items:center;justify-content:space-between;gap:var(--bn-s3);
  padding:var(--bn-s5);border-block-end:1px solid var(--bn-line-soft)}
.ac-sheet-h h2{font:var(--bn-t-h3);margin:0}
.ac-sheet-b{padding:var(--bn-s5)}
.ac-x{width:44px;height:44px;flex:none;display:grid;place-items:center;
  border:1px solid var(--bn-line);border-radius:50%;background:transparent;
  color:var(--bn-ink-2);cursor:pointer}
.ac-x:hover{color:var(--bn-ac);border-color:var(--bn-ac-line)}
`;

  function injectCSS() {
    if (document.getElementById('ac-style')) return;
    var s = document.createElement('style');
    s.id = 'ac-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }
  injectCSS();

  window.AppCore = {
    api: api, ApiError: ApiError, errText: errText, token: token,
    esc: esc, initials: initials, num: num, when: when,
    icons: I, svg: svg,
    skeleton: skeleton, emptyState: emptyState, errorState: errorState, onRetry: onRetry,
    toast: toast, sheet: sheet, confirm: confirmSheet,
    uploadImage: uploadImage, sessionExpired: sessionExpired
  };
})();
