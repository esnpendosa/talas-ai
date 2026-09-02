/**
 * TALAS AI — Service Worker (Phase 17 PWA)
 * Cache static assets for offline use.
 * PENTING: Jangan cache dokumen pemerintah (data regulasi).
 * Hanya cache shell statis: HTML, CSS, JS, manifest.
 */

const CACHE_NAME = 'talas-ai-v1';

// Hanya cache asset statis — TIDAK ada dokumen regulasi
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
];

// Install event — cache static assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      // Cache assets yang tersedia, abaikan yang gagal
      return Promise.allSettled(
        STATIC_ASSETS.map(url => cache.add(url).catch(() => null))
      );
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

// Activate event — bersihkan cache lama
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(name) {
          return name !== CACHE_NAME;
        }).map(function(name) {
          return caches.delete(name);
        })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// Fetch event — Network first, cache fallback untuk static assets
self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  // API calls: selalu network, jangan cache (data regulasi adalah data live)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(function() {
        return new Response(
          JSON.stringify({
            success: false,
            message: 'Tidak ada koneksi. Fitur analisis memerlukan koneksi ke server.',
            offline: true
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          }
        );
      })
    );
    return;
  }

  // Static assets: network first, fallback ke cache
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      fetch(event.request).then(function(response) {
        if (response && response.status === 200) {
          var responseClone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  // Page requests: network first, fallback offline page
  event.respondWith(
    fetch(event.request).catch(function() {
      return caches.match('/').then(function(cached) {
        if (cached) return cached;
        // Minimal offline fallback
        return new Response(
          '<!DOCTYPE html><html lang="id"><head><meta charset="UTF-8">' +
          '<title>TALAS AI - Offline</title></head><body>' +
          '<h1>TALAS AI</h1>' +
          '<p>Aplikasi sedang offline. Hubungkan ke server TALAS AI untuk menggunakan fitur analisis regulasi.</p>' +
          '<p><strong>TINJAUAN AWAL AI — WAJIB VERIFIKASI MANUSIA.</strong></p>' +
          '</body></html>',
          { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
        );
      });
    })
  );
});
