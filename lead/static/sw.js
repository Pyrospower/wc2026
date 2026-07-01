const CACHE_NAME = 'wc2026-card-cache-v1';

self.addEventListener('fetch', (event) => {
  const url = event.request.url;

  // Intercept any requests sent to your Render card generator
  if (url.includes('baburu-wc2026-cards.hf.space/card')) {
    event.respondWith(
      caches.open(CACHE_NAME).then((cache) => {
        return cache.match(event.request).then((cachedResponse) => {
          
          // 1. If it's already in the cache, serve it immediately (very fast)
          if (cachedResponse) {
            return cachedResponse;
          }

          // 2. Otherwise, fetch it from the network and save a copy in the cache
          return fetch(event.request).then((networkResponse) => {
            // Standard success is 200. Opaque responses (cross-origin with blocked CORS) have status 0.
            // We allow caching both so standard <img> tags can render them.
            if (networkResponse.status === 200 || networkResponse.status === 0) {
              cache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => {
            // Silently absorb request errors (e.g., if user is offline)
          });
        });
      })
    );
  }
});