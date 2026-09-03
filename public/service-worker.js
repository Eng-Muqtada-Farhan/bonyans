/**
 * بُنيان Service Worker — PWA
 *
 * الاستراتيجية:
 *   الواجهات البرمجية  → الشبكة أولاً، بلا تخزين
 *   الأصول الثابتة     → stale-while-revalidate
 *
 * لماذا لا cache-first: كانت الأصول تُخزَّن بلا إعادة تحقّق، فمن
 * حمّل bn-filters.js مرة يبقى على تلك النسخة أبداً — والتخزين لا
 * يُمسح إلا بتغيير CACHE_NAME يدوياً. أي نشر لاحق كان سيصل
 * الزوّار الجدد وحدهم. الآن يُخدَم المخزَّن فوراً وتُجلب النسخة
 * الجديدة في الخلفية فتظهر في التحميل التالي.
 */

const CACHE_NAME  = 'bunyan-v6';
const CACHE_ASSETS = [
  '/index.html',
  '/companies.html',
  '/projects.html',
  '/project_details.html',
  '/company_profile.html',
  '/tokens.css',
  '/bn-filters.js',
  '/nav-public.js',
  '/guard.js',
  '/app/app-core.js',
  '/admin/admin-core.js',
  '/manifest.json',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
];

/* ── Install: cache static assets ─────────────────── */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CACHE_ASSETS.filter(u => !u.includes('icon'))))
      .then(() => self.skipWaiting())
  );
});

/* ── Activate: clean old caches ───────────────────── */
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

/* ── الأسطح المسوَّرة: صفحاتها لا تُخزَّن ولا تُستبدَل ──────────
   /app /admin /me محمية بحارس على الخادم يفحص كل تنقّل (main.py:
   surface_guard). لو خُزِّنت صفحاتها أو أُعيد أي بديل مخزَّن عند
   انقطاع الشبكة، لتجاوز الحارسَ طلبٌ لم يصل الخادم أصلاً — وقد
   أعاد الموقعَ العام (index.html) داخل لوحة شركة/إدارة فعلياً.
   فتنقّل هذه الأسطح: شبكة فقط، بلا قراءة من المخزون ولا كتابة
   فيه، وعند الانقطاع صفحة بديلة صغيرة محايدة لا الموقع العام. */
function isSurfaceNav(request, pathname) {
  return request.mode === 'navigate' &&
    (pathname.startsWith('/app/') || pathname.startsWith('/admin/') || pathname.startsWith('/me/'));
}

function surfaceOfflinePage(pathname) {
  const surface = pathname.startsWith('/admin/') ? 'admin' : pathname.startsWith('/me/') ? 'me' : 'app';
  const title = surface === 'admin' ? 'لوحة الإدارة' : surface === 'me' ? 'منطقة صاحب المشروع' : 'لوحة الشركة';
  const html = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">' +
    '<meta name="viewport" content="width=device-width, initial-scale=1">' +
    '<title>لا يوجد اتصال — ' + title + '</title></head>' +
    '<body style="font-family:system-ui,-apple-system,Tajawal,sans-serif;text-align:center;' +
    'padding:80px 24px;color:#5b5347;background:#F4F2ED">' +
    '<h1 style="font-size:19px;margin:0 0 8px">لا يوجد اتصال بالإنترنت</h1>' +
    '<p style="margin:0 0 20px">' + title + ' تحتاج اتصالاً للتحقّق من جلستك.</p>' +
    '<button onclick="location.reload()" style="border:0;border-radius:10px;padding:12px 22px;' +
    'font:inherit;background:#96703C;color:#fff;min-height:44px">إعادة المحاولة</button>' +
    '</body></html>';
  return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

/* ── Fetch: strategy by request type ──────────────── */
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  /* API calls → network-first, no caching */
  const isAPI = url.pathname.startsWith('/api/') ||
    ['/companies', '/projects', '/health', '/conversations',
     '/notifications', '/reviews', '/login', '/auth/',
     '/stats', '/categories', '/subscription/', '/company/', '/bids', '/upload'].some(p => url.pathname.startsWith(p));

  if (isAPI) {
    event.respondWith(fetch(event.request).catch(() => new Response('{"error":"offline"}', {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    })));
    return;
  }

  /* تنقّل داخل /app أو /admin أو /me → شبكة فقط، بلا مخزون */
  if (isSurfaceNav(event.request, url.pathname)) {
    event.respondWith(
      fetch(event.request).catch(() => surfaceOfflinePage(url.pathname))
    );
    return;
  }

  /* الأصول الثابتة → stale-while-revalidate:
     يُخدَم المخزَّن فوراً (فالصفحة سريعة وتعمل بلا شبكة)، وتُجلب
     النسخة الحيّة في الخلفية وتحلّ محلّه للتحميل التالي. */
  event.respondWith(
    caches.match(event.request).then(cached => {
      const fresh = fetch(event.request).then(res => {
        if (res && res.status === 200 && res.type === 'basic') {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return res;
      }).catch(() => cached || caches.match('/index.html'));
      return cached || fresh;
    })
  );
});
