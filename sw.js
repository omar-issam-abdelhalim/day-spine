/*
 * Day Spine service worker.
 *
 * First visit (online): stores the app shell in the Cache so the app opens
 * with no connection afterwards.
 * Every later open: answers instantly from the Cache, then quietly fetches a
 * fresh copy in the background so updates pushed to the repo still arrive.
 *
 * Bump VERSION whenever the shell files change, so old caches are cleared.
 */
const VERSION = 'day-spine-v1';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/icon-maskable-512.png',
  './icons/apple-touch-icon.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;

  // Pages: serve the cached app, refresh it in the background.
  const key = req.mode === 'navigate' ? './index.html' : req;

  event.respondWith(
    caches.open(VERSION).then(async (cache) => {
      const cached = await cache.match(key);
      const network = fetch(req)
        .then((res) => {
          if (res && res.ok) cache.put(key, res.clone());
          return res;
        })
        .catch(() => undefined);
      return cached || (await network) || new Response('Offline', { status: 503 });
    })
  );
});
