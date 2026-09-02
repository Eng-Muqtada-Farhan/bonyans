/**
 * بُنيان — الإبلاغ والحجب
 * ═══════════════════════════════════════════════════════════════
 * شرط Apple ١٫٢: كل محتوى ينشره مستخدم يحتاج طريقاً للإبلاغ
 * عنه وحجب صاحبه من داخل التطبيق.
 *
 * وحدة واحدة تخدم الملف والمشروع والتقييم والرسالة — أربع نسخ
 * من نموذج بلاغ تفترق، وبلاغ لا يصل أسوأ من غياب الزرّ.
 *
 * الاستعمال:
 *   BunyanReport.button('company', 47)        → HTML زرّ
 *   BunyanReport.wire(root)                   → يربط كل الأزرار
 */
(function () {
  'use strict';

  var REASONS = [
    ['fake_info',   'بيانات كاذبة'],
    ['not_owner',   'صور أو أعمال ليست له'],
    ['fake_review', 'تقييم مزيّف'],
    ['offensive',   'محتوى مسيء'],
    ['harassment',  'مضايقة'],
    ['spam',        'إزعاج متكرّر'],
    ['other',       'سبب آخر']
  ];

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function tok() { try { return localStorage.getItem('bn_token') || ''; } catch (e) { return ''; } }

  var CSS = `
.bn-report-btn{display:inline-flex;align-items:center;justify-content:center;gap:6px;
  min-height:44px;padding-inline:var(--bn-s3);border:0;background:0;cursor:pointer;
  color:var(--bn-ink-3);font:var(--bn-t-cap);font-family:var(--bn-font);
  border-radius:var(--bn-r-sm);transition:color var(--bn-fast)}
.bn-report-btn:hover{color:var(--bn-err)}
.bn-rp-ov{position:fixed;inset:0;z-index:700;display:flex;align-items:flex-end;
  justify-content:center;background:var(--bn-scrim);opacity:0;
  transition:opacity var(--bn-mid)}
.bn-rp-ov.is-on{opacity:1}
@media(min-width:640px){.bn-rp-ov{align-items:center}}
.bn-rp{width:100%;max-width:460px;max-height:90vh;overflow-y:auto;
  padding:var(--bn-s6);background:var(--bn-surface);border:1px solid var(--bn-line);
  border-radius:var(--bn-r-lg) var(--bn-r-lg) 0 0;box-shadow:var(--bn-sh-3)}
@media(min-width:640px){.bn-rp{border-radius:var(--bn-r-lg);margin:var(--bn-s5)}}
.bn-rp h2{font:var(--bn-t-h3);margin:0 0 var(--bn-s2)}
.bn-rp .note{font:var(--bn-t-cap);color:var(--bn-ink-3);line-height:1.8;
  margin:0 0 var(--bn-s5)}
.bn-rp-r{display:flex;flex-direction:column;gap:2px;margin-block-end:var(--bn-s4)}
.bn-rp-r label{display:flex;align-items:center;gap:10px;min-height:44px;
  padding-inline:var(--bn-s3);border-radius:var(--bn-r-sm);cursor:pointer;
  font:var(--bn-t-sm);color:var(--bn-ink-2);transition:background var(--bn-fast)}
.bn-rp-r label:hover{background:var(--bn-glass-tint)}
.bn-rp-r input{width:18px;height:18px;flex:none;accent-color:var(--bn-ac);cursor:pointer}
.bn-rp textarea{width:100%;min-height:80px;padding:11px var(--bn-s4);
  border:1px solid var(--bn-line);border-radius:var(--bn-r);background:var(--bn-bg);
  color:var(--bn-ink);font:400 14px/1.5 var(--bn-font);resize:vertical}
.bn-rp textarea:focus{outline:none;border-color:var(--bn-ac)}
.bn-rp-end{display:flex;justify-content:flex-end;gap:var(--bn-s2);
  flex-wrap:wrap;margin-block-start:var(--bn-s5)}
`;

  function injectCSS() {
    if (document.getElementById('bn-rp-style')) return;
    var s = document.createElement('style');
    s.id = 'bn-rp-style';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  var FLAG = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" ' +
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true"><path d="M5 21V4"/>' +
    '<path d="M5 5h11l-1.6 3.5L16 12H5z"/></svg>';

  function button(type, id, label) {
    return '<button class="bn-report-btn" type="button" data-bn-report="' + esc(type) +
      '" data-bn-target="' + esc(id) + '">' + FLAG +
      '<span>' + esc(label || 'إبلاغ') + '</span></button>';
  }

  function open(type, id) {
    injectCSS();
    /* الإبلاغ يحتاج حساباً: بلاغ مجهول لا يُحاسَب عليه أحد
       ويُغرق الطابور. الزائر يُرسَل إلى الدخول ويعود. */
    if (!tok()) {
      var back = location.pathname + location.search;
      location.href = '/login.html?next=' + encodeURIComponent(back);
      return;
    }

    var ov = document.createElement('div');
    ov.className = 'bn-rp-ov';
    ov.innerHTML =
      '<div class="bn-rp" role="dialog" aria-modal="true" aria-labelledby="bnRpT">' +
        '<h2 id="bnRpT">الإبلاغ عن مخالفة</h2>' +
        '<p class="note">نراجع البلاغ خلال ٢٤ ساعة. اختيار السبب يساعدنا على ترتيب المراجعة.</p>' +
        '<div class="bn-rp-r">' +
          REASONS.map(function (r, i) {
            return '<label><input type="radio" name="bnRpReason" value="' + r[0] + '"' +
              (i === 0 ? ' checked' : '') + '><span>' + esc(r[1]) + '</span></label>';
          }).join('') +
        '</div>' +
        '<textarea id="bnRpDetails" maxlength="2000" ' +
          'placeholder="تفاصيل تساعدنا (اختياري)"></textarea>' +
        '<div class="bn-rp-end">' +
          '<button class="bn-btn bn-btn-ghost" type="button" data-no>إلغاء</button>' +
          '<button class="bn-btn" type="button" data-yes>إرسال البلاغ</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(ov);
    requestAnimationFrame(function () { ov.classList.add('is-on'); });

    function close() {
      ov.classList.remove('is-on');
      setTimeout(function () { ov.remove(); }, 200);
      document.removeEventListener('keydown', onKey);
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    document.addEventListener('keydown', onKey);
    ov.querySelector('[data-no]').onclick = close;
    ov.onclick = function (e) { if (e.target === ov) close(); };

    ov.querySelector('[data-yes]').onclick = async function () {
      var b = this;
      b.disabled = true; b.textContent = 'جارٍ الإرسال...';
      var reason = (ov.querySelector('input[name="bnRpReason"]:checked') || {}).value;
      try {
        var r = await fetch('/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + tok() },
          body: JSON.stringify({
            target_type: type, target_id: Number(id), reason: reason,
            details: ov.querySelector('#bnRpDetails').value.trim() || null
          })
        });
        var d = await r.json().catch(function () { return {}; });
        if (!r.ok) {
          b.disabled = false; b.textContent = 'إرسال البلاغ';
          alert(d.detail || 'تعذّر إرسال البلاغ — أعد المحاولة.');
          return;
        }
        ov.querySelector('.bn-rp').innerHTML =
          '<h2>وصلنا بلاغك</h2><p class="note">' +
          esc(d.message || 'نراجعه خلال ٢٤ ساعة.') + '</p>' +
          '<div class="bn-rp-end"><button class="bn-btn" type="button" data-close>حسناً</button></div>';
        ov.querySelector('[data-close]').onclick = close;
      } catch (e) {
        b.disabled = false; b.textContent = 'إرسال البلاغ';
        alert('تعذّر الاتصال بالخادم — أعد المحاولة.');
      }
    };
  }

  function wire(root) {
    (root || document).querySelectorAll('[data-bn-report]').forEach(function (b) {
      if (b._bnWired) return;
      b._bnWired = true;
      b.onclick = function () { open(b.dataset.bnReport, b.dataset.bnTarget); };
    });
  }

  /* يربط ما وُجد الآن وما يُضاف لاحقاً بعد كل رسم */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { wire(); });
  } else { wire(); }

  window.BunyanReport = { button: button, open: open, wire: wire, reasons: REASONS };
})();
