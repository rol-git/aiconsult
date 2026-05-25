/* Service worker для PWA-обвязки (ручной, без workbox).
 *
 *   - навигация (HTML) → network-first, fallback на /offline.html
 *   - статика (assets, favicon, manifest) → cache-first
 *   - /api, /socket.io, /stt → не трогаем, всегда сеть
 *
 * Регистрируется только в production (см. src/registerSW.ts).
 */

const CACHE = 'aic-shell-v1';
const OFFLINE_URL = '/offline.html';
const PRECACHE = ['/', '/index.html', '/offline.html', '/favicon.svg', '/manifest.webmanifest'];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

function isBackend(url) {
  return (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/socket.io') ||
    url.pathname.startsWith('/stt')
  );
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (isBackend(url)) return;

  if (request.mode === 'navigate') {
    event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
        }
        return response;
      });
    })
  );
});
