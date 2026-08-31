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

const CACHE_NAME  = 'bunyan-v5';
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
  '/bunyan.css',
  '/bunyan-nav.js',
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
