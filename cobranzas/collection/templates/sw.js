{% load static %}

const VERSION = '{{ version }}';
const CACHE_NAME = 'collection';
const URLS_TO_CACHE = [
  "{% url 'offline' %}",
  "{% url 'manifest' %}",
  "{% static 'css/styles.css' %}",
  "{% static 'js/utils.js' %}",
  "{% static 'js/sync.js' %}",
  "{% static 'js/create-collection.js' %}",
  'https://cdn.jsdelivr.net/npm/bootstrap@5.2.0-beta1/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.3/font/bootstrap-icons.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.2.0-beta1/dist/js/bootstrap.bundle.min.js',
  "{% static 'img/icon/icon-92x92.png' %}",
  "{% static 'img/icon/icon-192x192.png' %}",
  "{% static 'img/icon/icon-256x256.png' %}",
  "{% static 'img/icon/icon-384x384.png' %}",
  "{% static 'img/icon/icon-512x512.png' %}",
];

// install files needed offline
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(URLS_TO_CACHE);
      })
  );
});

// Every request from our site passes through the fetch handler
self.addEventListener('fetch', event => {
  console.log('I am a request with url:', event.request.clone().url)
  event.respondWith(
    // check all the caches in the browser and find
    // out whether our request is in any of them
    caches.match(event.request)
      .then(response => {
        return response || fetch(event.request);
      })
      .catch(() => {
        return caches.match("{% url 'offline' %}");
      })
  );
});

// Clear cache on activate
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cache => {
      return Promise.all(
        cache
          .filter(cache => (cache.startsWith(CACHE_NAME)))
          .map(cache => caches.delete(cache))
      );
    })
  );
});