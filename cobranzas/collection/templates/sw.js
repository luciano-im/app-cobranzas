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

// This function inject the served-offline-page event into the request
// On the client side, we can catch this event to differentiate an online response from an offline response.
const offlineResponse = async (response) => {
  const contentReader = response.body.getReader();
  let content = '';
  let readResult = { done: false, value: undefined };
  while(!readResult.done) {
    readResult = await contentReader.read();
    content += readResult.value ? new TextDecoder().decode(readResult.value) : '';
  }

  // We're "cloning" response by injecting some JS code in it
  content = content.replace("</body>", `
    <script type='text/javascript'>
    document.addEventListener('DOMContentLoaded', () => document.dispatchEvent(new Event('served-offline-page')));
    </script>
    </body>
  `);
  return new Response(content, {
    headers: response.headers,
    status: response.status,
    statusText: response.statusText
  });
}

const getFromCache = async (request) => {
  const cache = await caches.open(CACHE_NAME);
  // Return request or offline page!
  const res = await cache.match(request) || cache.match("{% url 'offline' %}");
  return res;
};

const networkFirst = async (request, url, callback = null) => {
  // Get from network
  try {
    const responseFromNetwork = await fetch(request);
    return responseFromNetwork;
  } catch (err) {
    // If received callback then call it
    if (callback) {
      return callback(request);
    }
    // If error, get from cache
    const responseFromCache = await getFromCache(request);
    return offlineResponse(responseFromCache);
  }
};

const manageCreateCollection = (postRequest) => {
  console.log('POST');

  const request = self.indexedDB.open('cobranzas', 1);

  request.onerror = (e) => {
    console.error(`IndexedDB error: ${request.errorCode}`);
  };

  request.onsuccess = (e) => {
    console.info('Successful database connection');
    db = request.result;
    console.log(postRequest);
    const requestData = {
      url: postRequest.url,
      method: postRequest.method,
      mode: postRequest.mode,
      body: postRequest.body,
      headers: postRequest.headers
    }
    console.log(requestData);
    const saveRequest = db.transaction('collections', 'readwrite').objectStore('collections').add(requestData);
    saveRequest.onsuccess = () => {
      db.close();
    };
  };

  return caches.match("{% url 'create-collection' %}");
}

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
  //console.log('Fetch url:', event.request.clone().url);
  var requestUrl = new URL(event.request.url);

  if (requestUrl.pathname == "{% url 'create-collection' %}") {
    if (event.request.method == "POST") {
      return event.respondWith(networkFirst(event.request, requestUrl.pathname, manageCreateCollection));
    }
  }

  return event.respondWith(networkFirst(event.request, requestUrl.pathname));
});