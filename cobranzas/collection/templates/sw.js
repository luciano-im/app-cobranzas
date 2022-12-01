{% load static %}

// VARIABLES

const VERSION = '{{ version }}';
const CACHE_NAME = 'collection-{{ version }}';
const URLS_TO_CACHE = [
  "{% url 'offline' %}",
  "{% url 'manifest' %}",
  "{% url 'create-collection' %}",
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

// UTILS

const getFromCache = async (request) => {
  const cache = await caches.open(CACHE_NAME);
  const res = await cache.match(request);
  return res;
};

const networkFirst = async (request, callback = null) => {
  // Get from network
  try {
    const responseFromNetwork = await fetch(request);
    return responseFromNetwork;
  } catch (err) {
    // If received callback then call it
    if (callback) {
      return callback()
    }
    // If error, get from cache
    const responseFromCache = await getFromCache(request);
    if (responseFromCache) {
      return responseFromCache;
    }

    // If network and cache fails, return offline page
    return caches.match("{% url 'offline' %}");
  }
};

// EVENT LISTENERS

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

// Clear cache on activate
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cache => {
      return Promise.all(
        cache
          .filter(cache => (cache.startsWith(CACHE_NAME)))
          .map(cache => {
            if (cache != 'collection-{{ version }}') {
              caches.delete(cache);
            }
          })
      );
    })
  );
});

self.addEventListener('fetch', event => {
  console.log('Fetch url:', event.request.clone().url);
  var requestUrl = new URL(event.request.url);

  if (requestUrl.pathname == "{% url 'create-collection' %}") {
    if (event.request.method == "POST") {
      // TODO: Save failed POST requests
      console.log('POST');
    }
  }

  return event.respondWith(networkFirst(event.request));
});