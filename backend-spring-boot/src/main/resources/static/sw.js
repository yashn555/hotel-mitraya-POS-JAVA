// Hotel Mitraya POS - Service Worker for PWA Android App Installation
const CACHE_NAME = 'mitraya-pos-v1.0';
const STATIC_ASSETS = [
    '/static/pos.css',
    '/static/style.css',
    '/static/receipt.css',
    '/static/pos.js',
    '/static/display.js',
    '/static/logo.png',
    '/static/manifest.json'
];

// Install Event - Pre-cache critical assets
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch((err) => {
                console.warn('[SW] Pre-cache non-fatal warning:', err);
            });
        }).then(() => self.skipWaiting())
    );
});

// Activate Event - Clean old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch Event - Network first with cache fallback for static files
self.addEventListener('fetch', (event) => {
    const requestUrl = new URL(event.request.url);

    // Only cache GET requests for static assets, let APIs pass through to network
    if (event.request.method === 'GET' && requestUrl.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then((cachedResponse) => {
                if (cachedResponse) {
                    // Return cached asset and update in background
                    fetch(event.request).then((networkResponse) => {
                        if (networkResponse && networkResponse.status === 200) {
                            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse));
                        }
                    }).catch(() => {});
                    return cachedResponse;
                }
                return fetch(event.request);
            })
        );
    }
});
