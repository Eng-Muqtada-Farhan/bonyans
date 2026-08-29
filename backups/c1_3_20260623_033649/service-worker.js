/**
 * بُنيان Service Worker — Phase 10 PWA
 * Strategy: Cache-first for static assets, network-first for API
 */

const CACHE_NAME  = 'bunyan-v4';
const CACHE_ASSETS = [
  '/index.html',
  '/projects.html',
  '/project_details.html',
  '/company_profile.html',
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

  /* Static assets → cache-first */
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(res => {
        if (!res || res.status !== 200 || res.type !== 'basic') return res;
        const clone = res.clone();
        caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        return res;
      }).catch(() => caches.match('/index.html'));
    })
  );
});
