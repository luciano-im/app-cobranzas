const VERSION = '{{ version }}';
const CACHE_NAME = 'collection';
const URLS_TO_CACHE = [
  "{% url 'offline' %}",
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