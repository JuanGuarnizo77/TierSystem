/**
 * Service Worker de la PWA: TierSystem.
 * =====================================
 * Gestiona el ciclo de vida de la aplicación web progresiva y las estrategias de caché:
 *   1. Evento 'install':
 *      - Precarga en caché estática (Cache Storage) las dependencias críticas de UI:
 *        Tailwind CSS, FontAwesome, SweetAlert2, Leaflet y Dexie.js.
 *   2. Evento 'fetch':
 *      - Estrategia "Network First with Cache Fallback": intenta siempre obtener
 *        el recurso fresco de la red; si hay conectividad, actualiza la caché en segundo plano.
 *      - Si falla la conexión a internet (zonas rurales del Huila sin cobertura celular),
 *        sirve de inmediato la copia almacenada en caché para garantizar continuidad operativa.
 *   3. Evento 'activate':
 *      - Invalida y purga automáticamente versiones antiguas de la caché para evitar conflictos
 *        tras actualizaciones del código frontend.
 */

// Versión del contenedor de caché local
const CACHE_NAME = 'tiersystem-cache-v3';

// Lista de recursos estáticos críticos para precargar durante la instalación
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/js/tailwindcss.js',
  '/static/js/sweetalert2.all.min.js',
  '/static/css/styles.css',
  '/static/fontawesome/css/all.min.css',
  '/static/js/db.js',
  'https://cdn.jsdelivr.net/npm/sweetalert2@11',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.jsdelivr.net/npm/@turf/turf@6/turf.min.js'
];

/**
 * Evento de instalación del Service Worker.
 * Abre el almacén de caché y precarga los activos declarados sin bloquear la ejecución ante fallos puntuales.
 */
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Cachear activos ignorando errores individuales mediante Promise.allSettled
        return Promise.allSettled(urlsToCache.map(url => cache.add(url)));
      })
      .then(() => self.skipWaiting())
  );
});

/**
 * Interceptor de peticiones HTTP (Fetch).
 * Aplica Network-First con fallback a Cache Storage para navegación offline continua.
 */
self.addEventListener('fetch', event => {
  // Ignorar peticiones que no sean GET (como solicitudes POST de sincronización de formularios)
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        // Si la red responde exitosamente (HTTP 200), refrescar la copia en caché
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            // Guardar en caché solo peticiones a orígenes HTTP/HTTPS válidos
            if (event.request.url.startsWith('http')) {
              cache.put(event.request, responseClone);
            }
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Fallback: Si no hay acceso a internet, responder desde el almacenamiento en caché
        return caches.match(event.request).then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Si es una solicitud de navegación HTML y no se encuentra en caché, responder con la raíz
          if (event.request.headers.get('accept') && event.request.headers.get('accept').includes('text/html')) {
            return caches.match('/');
          }
        });
      })
  );
});

/**
 * Evento de activación del Service Worker.
 * Limpia versiones obsoletas de la caché y asume el control inmediato de todos los clientes activos.
 */
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (!cacheWhitelist.includes(cacheName)) {
            // Eliminar contenedores de caché correspondientes a versiones anteriores
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});
