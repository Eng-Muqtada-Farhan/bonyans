/**
 * بُنيان — نواة لوحة الإدارة   سطح مسوَّر
 * ═══════════════════════════════════════════════════════════════
 * المرجع: DESIGN.md §٤ §٥ §٦
 *
 * قاعدة العزل ١ — لا رابط تصفّح للموقع العام في هذا الملف.
 *   الاستثناء الوحيد المصرَّح به هو وجهة الخروج ../login.html.
 *
 * تحتوي: المصادقة و api() بتصنيف أخطاء واحد · الأيقونات ·
 *        الحالات · الرسائل اللحظية · نافذة الحوار ·
 *        وحالات الزرّ الخمس (§٦).
 */
(function () {
  'use strict';

  var API = '';

  function store(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } }
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
    grid:     '<rect x="3" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="1.2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="1.2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="1.2"/>',
    inbox:    '<path d="M3 13h4l2 3h6l2-3h4"/><path d="M5.5 5h13l2.5 8v5.5A1.5 1.5 0 0 1 19.5 20h-15A1.5 1.5 0 0 1 3 18.5V13z"/>',
    building: '<rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M9 8h2M13 8h2M9 12h2M13 12h2M9 16h2M13 16h2"/>',
    flag:     '<path d="M5 21V4"/><path d="M5 5h11l-1.6 3.5L16 12H5z"/>',
    users:    '<circle cx="9" cy="8" r="3.4"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16.5 5.2a3.4 3.4 0 0 1 0 5.6M17.5 14.4A6.5 6.5 0 0 1 21.5 20"/>',
    scroll:   '<path d="M6 3h12a1.5 1.5 0 0 1 1.5 1.5V18a3 3 0 0 1-3 3H7.5a3 3 0 0 1-3-3V4.5A1.5 1.5 0 0 1 6 3z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    check:    '<path d="M20 6L9 17l-5-5"/>',
    x:        '<path d="M18 6L6 18M6 6l12 12"/>',
    star:     '<path d="M12 3.7l2.5 5.1 5.6.8-4 3.9 1 5.6-5.1-2.7-5.1 2.7 1-5.6-4-3.9 5.6-.8z"/>',
    card:     '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    pin:      '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    tag:      '<path d="M3 12.5V4.5A1.5 1.5 0 0 1 4.5 3h8L21 11.5 13.5 19z"/><circle cx="7.5" cy="7.5" r="1.3"/>',
    clock:    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    alert:    '<path d="M12 4.5 2.5 20h19z"/><path d="M12 10v4M12 17h.01"/>',
    offline:  '<path d="M3 3l18 18"/><path d="M5.5 12.5a9 9 0 0 1 3.2-2.1M2 8.8A14 14 0 0 1 6 6.3M18.5 6.3A14 14 0 0 1 22 8.8M15.4 10.5a9 9 0 0 1 3.1 2"/><circle cx="12" cy="18" r="1"/>',
    empty:    '<rect x="3" y="5" width="18" height="15" rx="2"/><path d="M3 10h18M8 15h8"/>',
    market:   '<path d="M4 8h16l-1.2 11.2a1.5 1.5 0 0 1-1.5 1.3H6.7a1.5 1.5 0 0 1-1.5-1.3z"/><path d="M8.5 8V6a3.5 3.5 0 0 1 7 0v2"/>',
    chat:     '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-5.2A8 8 0 1 1 21 12z"/>'
  };
  function svg(d, s) {
    return '<svg viewBox="0 0 24 24" width="' + (s || 16) + '" height="' + (s || 16) +
      '" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
      'stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  }

  /* ── الشبكة ───────────────────────────────────────────────── */
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
    try { localStorage.removeItem('bn_token'); } catch (e) {}
    location.replace('../login.html?role=admin&next=' + encodeURIComponent(location.pathname));
  }

  function errText(e) {
    if (e && e.detail) return e.detail;
    if (e && e.status === 403) return 'ليس لديك صلاحية لهذا الإجراء.';
    if (e && e.status === 429) return 'محاولات كثيرة — انتظر قبل المحاولة مجدداً.';
    if (e && e.status === 503) return 'الخدمة غير متاحة مؤقتاً — حاول بعد قليل.';
    return 'تعذّر الاتصال بالخادم — أعد المحاولة.';
  }

  /* ══════════════════════════════════════════════════════════
     حالات الزرّ الخمس (DESIGN §٦)
       default → hover → active(انخفاض) → loading → success

     الثلاث الأولى في CSS، والأخيرتان هنا: الزرّ يُقفل
     (pointer-events:none) ويدور، ثم يعرض علامة نجاح ثانيتين.
     زرٌّ صامت أثناء العمل يجعل المستخدم يضغط مرتين، فيُنفَّذ
     الإجراء مرتين — أو يُحجَب بحدّ المعدّل.
     ══════════════════════════════════════════════════════════ */
  function runAction(btn, fn, opts) {
    opts = opts || {};
    if (btn.classList.contains('is-loading')) return Promise.resolve();
    var original = btn.innerHTML;
    btn.classList.add('is-loading');
    btn.setAttribute('aria-busy', 'true');
    btn.innerHTML = '<span class="bna-spin" aria-hidden="true"></span><span>' +
      esc(opts.loading || 'جارٍ...') + '</span>';

    return Promise.resolve()
      .then(fn)
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

  /* ── الحالات ───────────────────────────────────────────────── */
  function skeleton(n, h) {
    var out = '';
    for (var i = 0; i < (n || 3); i++) out += '<div class="ad-skel" style="height:' + (h || 76) + 'px"></div>';
    return out;
  }
  function emptyState(title, desc, actionHTML, icon) {
    return '<div class="ad-state">' + svg(icon || I.empty, 38) +
      '<div class="ad-state-t">' + esc(title) + '</div>' +
      (desc ? '<div class="ad-state-d">' + esc(desc) + '</div>' : '') +
      (actionHTML || '') + '</div>';
  }
  function errorState(msg) {
    return '<div class="ad-state">' + svg(I.offline, 38) +
      '<div class="ad-state-t">تعذّر تحميل البيانات</div>' +
      '<div class="ad-state-d">' + esc(msg || 'تحقّق من اتصالك ثم أعد المحاولة.') + '</div>' +
      '<button class="bn-btn" type="button" data-ad-retry>إعادة المحاولة</button></div>';
  }
  function onRetry(el, fn) {
    var b = el.querySelector('[data-ad-retry]');
    if (b) b.onclick = fn;
  }

  /* ── رسالة لحظية ───────────────────────────────────────────── */
  var toastEl = null;
  function toast(msg, kind) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.className = 'ad-toast';
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = msg;
    toastEl.className = 'ad-toast is-on' + (kind === 'err' ? ' is-err' : '');
    clearTimeout(toastEl._t);
    toastEl._t = setTimeout(function () { toastEl.className = 'ad-toast'; }, 3200);
  }

  /* ── نافذة حوار ────────────────────────────────────────────── */
  function sheet(title, bodyHTML, opts) {
    opts = opts || {};
    var ov = document.createElement('div');
    ov.className = 'ad-ov';
    ov.innerHTML =
      '<div class="ad-sheet" role="dialog" aria-modal="true">' +
        '<div class="ad-sheet-h"><h2>' + esc(title) + '</h2>' +
          '<button class="ad-x" type="button" aria-label="إغلاق">' + svg(I.x, 18) + '</button></div>' +
        '<div class="ad-sheet-b">' + bodyHTML + '</div>' +
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
    ov.querySelector('.ad-x').onclick = close;
    ov.onclick = function (e) { if (e.target === ov) close(); };
    document.addEventListener('keydown', onKey);
    var first = ov.querySelector('input,textarea,select');
    if (first) first.focus();
    return { el: ov, close: close };
  }

  function confirmSheet(title, msg, confirmLabel) {
    return new Promise(function (resolve) {
      var s = sheet(title,
        '<p class="ad-note">' + esc(msg) + '</p>' +
        '<div class="ad-row-end">' +
          '<button class="bn-btn bn-btn-ghost" type="button" data-no>إلغاء</button>' +
          '<button class="bn-btn" type="button" data-yes>' + esc(confirmLabel || 'تأكيد') + '</button>' +
        '</div>', { onClose: function () { resolve(false); } });
      s.el.querySelector('[data-no]').onclick = function () { s.close(); };
      s.el.querySelector('[data-yes]').onclick = function () { resolve(true); s.close(); };
    });
  }

  /* ── الأنماط ───────────────────────────────────────────────── */
  var CSS = `
.ad-wrap{max-width:1000px;padding:var(--bn-s6) var(--bn-s6) var(--bn-s14)}
@media(max-width:900px){.ad-wrap{padding:var(--bn-s5) var(--bn-s4) var(--bn-s14)}}
.ad-head{margin-block-end:var(--bn-s6)}
.ad-head h1{font:var(--bn-t-h1);margin:0 0 6px;letter-spacing:-.01em}
.ad-head p{font:var(--bn-t-sm);color:var(--bn-ink-3);margin:0;max-width:62ch;line-height:1.75}
.ad-head-row{display:flex;align-items:flex-start;justify-content:space-between;
  gap:var(--bn-s4);flex-wrap:wrap}
@media(max-width:560px){.ad-head h1{font-size:22px}}
.ad-sec{margin-block-end:var(--bn-s8)}
.ad-sec-t{font:var(--bn-t-h3);margin:0 0 var(--bn-s4);display:flex;align-items:center;gap:9px}
.ad-sec-t::before{content:"";width:5px;height:5px;border-radius:50%;background:var(--bn-ac);flex:none}
.ad-sec-d{font:var(--bn-t-sm);color:var(--bn-ink-3);margin:-8px 0 var(--bn-s4);max-width:62ch}

/* طابور القرارات — أرقام كبيرة وإطار محذّر (§٦) */
.ad-queue{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));
  gap:var(--bn-s3);margin-block-end:var(--bn-s8)}
.ad-q{display:block;padding:var(--bn-s6) var(--bn-s5);border-radius:var(--bn-r-lg);
  text-decoration:none;color:inherit;border:1px solid var(--bn-line);
  background:var(--bn-surface);
  transition:border-color var(--bn-fast),transform var(--bn-fast),box-shadow var(--bn-fast)}
.ad-q:hover{transform:translateY(-2px);box-shadow:var(--bn-sh-2)}
/* الطابور غير الفارغ يلبس إطاراً محذّراً — القرار ينتظر */
.ad-q.is-due{border-color:var(--bn-ac);background:var(--bn-ac-bg)}
.ad-q-l{font:var(--bn-t-sm);color:var(--bn-ink-2);display:flex;align-items:center;
  gap:7px;margin-block-end:var(--bn-s3)}
.ad-q.is-due .ad-q-l{color:var(--bn-ac)}
.ad-q-n{font:700 44px/1 var(--bn-mono);font-variant-numeric:tabular-nums;
  letter-spacing:-.03em;color:var(--bn-ink-3)}
.ad-q.is-due .ad-q-n{color:var(--bn-ac)}
.ad-q-d{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:8px}
@media(max-width:560px){.ad-q-n{font-size:36px}}

/* أرقام السياق — أصغر عمداً، فالقرار أولاً */
.ad-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:var(--bn-s2)}
.ad-stat{padding:var(--bn-s4);border-radius:var(--bn-r-lg)}
.ad-stat-l{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-end:6px}
.ad-stat-n{font:600 19px/1.1 var(--bn-mono);font-variant-numeric:tabular-nums;
  color:var(--bn-ink)}
.ad-stat-d{font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-start:5px}

/* قوائم */
.ad-list{display:flex;flex-direction:column;gap:var(--bn-s2)}
.ad-item{display:flex;align-items:center;gap:var(--bn-s4);padding:var(--bn-s4);
  border-radius:var(--bn-r-lg)}
.ad-av{width:44px;height:44px;border-radius:var(--bn-r-sm);flex:none;display:grid;
  place-items:center;background:var(--bn-ac-bg);color:var(--bn-ac);
  border:1px solid var(--bn-ac-line);font:600 14px/1 var(--bn-font);overflow:hidden}
.ad-av img{width:100%;height:100%;object-fit:cover}
.ad-item-b{flex:1;min-width:0}
.ad-item-t{font:500 14.5px/1.4 var(--bn-font);margin:0 0 4px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ad-item-m{font:var(--bn-t-cap);color:var(--bn-ink-3);display:flex;align-items:center;
  gap:var(--bn-s3);flex-wrap:wrap}
.ad-item-m i{display:inline-flex;align-items:center;gap:4px;font-style:normal}
.ad-item-act{display:flex;align-items:center;gap:var(--bn-s2);flex:none}
@media(max-width:700px){
  .ad-item{flex-wrap:wrap}
  .ad-item-act{width:100%;justify-content:flex-end}
}

/* ألسنة ترشيح */
.ad-tabs{display:flex;gap:var(--bn-s2);flex-wrap:wrap;margin-block-end:var(--bn-s5)}
.ad-tab{min-height:44px;padding-inline:var(--bn-s4);border-radius:var(--bn-r-pill);
  border:1px solid var(--bn-line);background:transparent;cursor:pointer;
  color:var(--bn-ink-2);font:400 13px/1 var(--bn-font);display:inline-flex;
  align-items:center;gap:7px;
  transition:color var(--bn-fast),border-color var(--bn-fast),background var(--bn-fast)}
.ad-tab:hover{color:var(--bn-ac);border-color:var(--bn-ac-line)}
.ad-tab.is-on{background:var(--bn-ac);color:var(--bn-ac-on);border-color:transparent}
.ad-tab-n{font:500 11px/1 var(--bn-mono);font-variant-numeric:tabular-nums;opacity:.72}

/* شارات */
.ad-tag{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;
  border-radius:var(--bn-r-pill);font:var(--bn-t-cap);white-space:nowrap}
.ad-tag-on{background:var(--bn-ac-bg);color:var(--bn-ac);border:1px solid var(--bn-ac-line)}
.ad-tag-off{background:transparent;color:var(--bn-ink-3);border:1px solid var(--bn-line)}

/* ══ حالات الزرّ الخمس ══ */
.bn-btn,.ad-btn{transition:background var(--bn-fast),color var(--bn-fast),
  border-color var(--bn-fast),transform var(--bn-fast),box-shadow var(--bn-fast)}
.bn-btn:active:not(:disabled):not(.is-loading),
.ad-btn:active:not(:disabled):not(.is-loading){transform:translateY(1px);box-shadow:none}
.bn-btn.is-loading,.ad-btn.is-loading{pointer-events:none;opacity:.82}
.bn-btn.is-success,.ad-btn.is-success{pointer-events:none}
.bn-btn.is-loading>span,.bn-btn.is-success>span,
.ad-btn.is-loading>span,.ad-btn.is-success>span{display:inline-flex;align-items:center}
.bna-spin{width:14px;height:14px;flex:none;border-radius:50%;
  border:2px solid currentColor;border-block-start-color:transparent;
  margin-inline-end:7px;animation:ad-spin .7s linear infinite}
@keyframes ad-spin{to{transform:rotate(360deg)}}
@media(prefers-reduced-motion:reduce){.bna-spin{animation-duration:2s}}

/* زرّ خطر — للرفض والحجب */
.ad-btn-danger{color:var(--bn-err);border-color:var(--bn-err-line)}
.ad-btn-danger:hover{background:var(--bn-err-bg);color:var(--bn-err)}

/* مبدّل */
.ad-switch{display:inline-flex;align-items:center;gap:9px;min-height:44px;
  border:0;background:0;cursor:pointer;color:var(--bn-ink-2);
  font:400 13px/1 var(--bn-font);padding-inline:0}
.ad-track{width:42px;height:24px;border-radius:999px;flex:none;position:relative;
  background:var(--bn-line);transition:background var(--bn-mid)}
.ad-track::after{content:"";position:absolute;inset-block-start:3px;inset-inline-start:3px;
  width:18px;height:18px;border-radius:50%;background:var(--bn-surface);
  box-shadow:var(--bn-sh-1);transition:transform var(--bn-mid)}
.ad-switch.is-on .ad-track{background:var(--bn-ac)}
.ad-switch.is-on .ad-track::after{transform:translateX(-18px)}
.ad-switch.is-loading{pointer-events:none;opacity:.7}

/* نماذج */
.ad-fr{margin-block-end:var(--bn-s4)}
.ad-fr label{display:block;font:var(--bn-t-cap);color:var(--bn-ink-3);margin-block-end:6px}
.ad-fr input,.ad-fr select,.ad-fr textarea{width:100%;min-height:44px;
  padding:11px var(--bn-s4);border:1px solid var(--bn-line);border-radius:var(--bn-r);
  background:var(--bn-bg);color:var(--bn-ink);font:400 14px/1.5 var(--bn-font)}
.ad-fr input:focus,.ad-fr select:focus,.ad-fr textarea:focus{outline:none;border-color:var(--bn-ac)}
.ad-fr textarea{resize:vertical;min-height:96px}
.ad-row-end{display:flex;align-items:center;justify-content:flex-end;gap:var(--bn-s2);
  flex-wrap:wrap;margin-block-start:var(--bn-s5)}
.ad-note{font:var(--bn-t-sm);color:var(--bn-ink-2);line-height:1.8;margin:0}

/* الحالات */
.ad-state{text-align:center;padding:var(--bn-s12) var(--bn-s5);
  border:1px dashed var(--bn-line);border-radius:var(--bn-r-lg)}
.ad-state svg{stroke:var(--bn-ink-3);fill:none;stroke-width:1.3;margin-block-end:var(--bn-s3)}
.ad-state-t{font:500 15px/1.5 var(--bn-font);color:var(--bn-ink-2)}
.ad-state-d{font:var(--bn-t-sm);color:var(--bn-ink-3);margin-block-start:6px;
  max-width:46ch;margin-inline:auto;line-height:1.7}
.ad-state .bn-btn{margin-block-start:var(--bn-s4)}
.ad-skel{border-radius:var(--bn-r-lg);background:var(--bn-glass-tint);
  border:1px solid var(--bn-line-soft);margin-block-end:var(--bn-s2);
  position:relative;overflow:hidden}
.ad-skel::after{content:"";position:absolute;inset:0;transform:translateX(-100%);
  background:linear-gradient(90deg,transparent,var(--bn-glass),transparent);
  animation:ad-sweep 1.4s infinite}
@keyframes ad-sweep{to{transform:translateX(300%)}}

/* رسالة لحظية */
.ad-toast{position:fixed;inset-block-end:var(--bn-s6);inset-inline:0;margin-inline:auto;
  width:max-content;max-width:88vw;z-index:500;padding:12px var(--bn-s5);
  border-radius:var(--bn-r-pill);background:var(--bn-ink);color:var(--bn-bg);
  font:var(--bn-t-sm);box-shadow:var(--bn-sh-3);opacity:0;transform:translateY(12px);
  pointer-events:none;transition:opacity var(--bn-mid),transform var(--bn-mid)}
.ad-toast.is-on{opacity:1;transform:none}
.ad-toast.is-err{background:var(--bn-ac);color:var(--bn-ac-on)}

/* نافذة حوار */
.ad-ov{position:fixed;inset:0;z-index:600;display:flex;align-items:flex-end;
  justify-content:center;background:var(--bn-scrim);opacity:0;transition:opacity var(--bn-mid)}
.ad-ov.is-on{opacity:1}
@media(min-width:640px){.ad-ov{align-items:center}}
.ad-sheet{width:100%;max-width:560px;max-height:90vh;overflow-y:auto;
  background:var(--bn-surface);border:1px solid var(--bn-line);
  border-radius:var(--bn-r-lg) var(--bn-r-lg) 0 0;box-shadow:var(--bn-sh-3);
  transform:translateY(16px);transition:transform var(--bn-mid)}
.ad-ov.is-on .ad-sheet{transform:none}
@media(min-width:640px){.ad-sheet{border-radius:var(--bn-r-lg)}}
.ad-sheet-h{display:flex;align-items:center;justify-content:space-between;gap:var(--bn-s3);
  padding:var(--bn-s5);border-block-end:1px solid var(--bn-line-soft)}
.ad-sheet-h h2{font:var(--bn-t-h3);margin:0}
.ad-sheet-b{padding:var(--bn-s5)}
.ad-x{width:44px;height:44px;flex:none;display:grid;place-items:center;
  border:1px solid var(--bn-line);border-radius:50%;background:transparent;
  color:var(--bn-ink-2);cursor:pointer}
.ad-x:hover{color:var(--bn-ac);border-color:var(--bn-ac-line)}
`;

  function injectCSS() {
    if (document.getElementById('ad-style')) return;
    var s = document.createElement('style');
    s.id = 'ad-style'; s.textContent = CSS;
    document.head.appendChild(s);
  }
  injectCSS();

  /* عدّادات القائمة الجانبية — تُملأ مرّة وتُبثّ للقائمة */
  async function counts() {
    try {
      var st = await api('/admin/system-status');
      return {
        'requests.html': (st.companies && st.companies.pending) || 0,
        'reports.html':  (st.reviews && st.reviews.pending) || 0
      };
    } catch (e) { return {}; }
  }

  window.AdminCore = {
    api: api, ApiError: ApiError, errText: errText, token: token,
    esc: esc, initials: initials, num: num, when: when,
    icons: I, svg: svg, runAction: runAction,
    skeleton: skeleton, emptyState: emptyState, errorState: errorState, onRetry: onRetry,
    toast: toast, sheet: sheet, confirm: confirmSheet,
    counts: counts, sessionExpired: sessionExpired
  };
})();
