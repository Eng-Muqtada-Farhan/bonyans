/**
 * بُنيان — تسجيل عامل الخدمة + إشعار تحديث صريح
 * ═══════════════════════════════════════════════════════════════
 * عامل الخدمة يستعمل stale-while-revalidate: نسخة جديدة من ملفّه
 * تُنصَّب في الخلفية بعد كل نشر يغيّر service-worker.js (مع تدوير
 * CACHE_NAME)، ولا تظهر للمستخدم العائد بلا إشعار — بما فيه إصلاح
 * أمني. هذا الملف يُسجِّل عامل الخدمة ويُظهر شريطاً صريحاً حين
 * تُنصَّب نسخة جديدة بجوار نسخة تعمل فعلاً، فيختار المستخدم
 * التحديث بدل إعادة تحميل صامتة تُضيع ما يكتبه.
 *
 * التركيب: <script src="sw-update.js"></script> بدل نداء
 * navigator.serviceWorker.register المباشر.
 */
(function () {
  'use strict';
  if (!('serviceWorker' in navigator)) return;

  function showUpdateBar() {
    if (document.getElementById('bn-sw-update')) return;
    var css = document.createElement('style');
    css.textContent =
      '#bn-sw-update{position:fixed;inset-inline:0;inset-block-end:0;z-index:900;' +
      'display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;' +
      'padding:var(--bn-s3) var(--bn-s4);background:var(--bn-surface);' +
      'border-block-start:1px solid var(--bn-line);box-shadow:var(--bn-sh-3);' +
      'font:var(--bn-t-sm);color:var(--bn-ink);font-family:var(--bn-font)}';
    document.head.appendChild(css);

    var bar = document.createElement('div');
    bar.id = 'bn-sw-update';
    bar.setAttribute('role', 'status');
    bar.innerHTML =
      '<span>نسخة جديدة من بُنيان متاحة.</span>' +
      '<button class="bn-btn bn-btn-sm" type="button" id="bnSwReload">تحديث الآن</button>';
    document.body.appendChild(bar);
    document.getElementById('bnSwReload').onclick = function () {
      location.reload();
    };
  }

  navigator.serviceWorker.register('/service-worker.js').then(function (reg) {
    reg.addEventListener('updatefound', function () {
      var nw = reg.installing;
      if (!nw) return;
      nw.addEventListener('statechange', function () {
        /* controller موجود يعني هذه ليست أول زيارة — نسخة تعمل
           فعلاً، وأخرى صارت جاهزة بجوارها */
        if (nw.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateBar();
        }
      });
    });
    /* نادر مع skipWaiting، لكن يحدث إن ثبَّت تبويب آخر نسخة جديدة
       بينما هذا التبويب مفتوح من قبل */
    if (reg.waiting && navigator.serviceWorker.controller) showUpdateBar();
  }).catch(function () {});
})();
