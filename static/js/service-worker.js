const CACHE_NAME = 'tiersystem-cache-v2';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/js/tailwindcss.js',
  '/static/css/styles.css',
  '/static/fontawesome/css/all.min.css',
  '/static/js/db.js',
  'https://cdn.jsdelivr.net/npm/sweetalert2@11',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.jsdelivr.net/npm/@turf/turf@6/turf.min.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Cache assets, ignorando errores individuales para permitir funcionamiento progresivo
        return Promise.allSettled(urlsToCache.map(url => cache.add(url)));
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('fetch', event => {
  // Ignorar peticiones que no sean GET (como POST de sincronización)
  if (event.request.method !== 'GET') return;

  // Estrategia Network First con Fallback a Cache y almacenamiento dinámico
  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            // Guardar en caché solo peticiones HTTP/HTTPS estáticas o CDN
            if (event.request.url.startsWith('http')) {
              cache.put(event.request, responseClone);
            }
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Si no hay red, responder desde caché
        return caches.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Si es una petición HTML y no está en caché, intentar devolver raíz o página offline
          if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
            return caches.match('/');
          }
        });
      })
  );
});

self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});
