//// IMPORTS ////

import { fetchAPI, getCookie } from "./utils.js";


//// CONSTANTS & HELPERS ////

const URL = `/collections/data/`;
const COLLECTIONS_STORE_NAME = 'collections';
// Database connection (IDBDatabase)
let db;

// initialize tooltips
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

//// DOM ACCESS ////

const syncContainer = document.querySelector('.synchronization');
const syncLastUpdate = document.querySelector('.synchronization .last-sync');
const syncButton = document.querySelector('.synchronization button');
const pendingRequests = document.querySelector('.synchronization #pending-requests');
const offline = document.querySelector('.offline');


//// FUNCTIONS ////

const openDatabase = () => {
  const request = window.indexedDB.open('cobranzas', 1);

  request.onerror = (e) => {
    console.error(`IndexedDB error: ${request.errorCode}`);
  };

  request.onsuccess = (e) => {
    console.info('Successful database connection');
    db = request.result;

    // Show badge if there are pending requests stored
    showPendingRequestsBadge();
  };

  request.onupgradeneeded = (e) => {
    // Create database if needed
    console.info('Database created');
    const db = request.result;

    const salesStore = db.createObjectStore('sales', { keyPath: 'customer' });
    const installmentsStore = db.createObjectStore('installments', { keyPath: 'customer' });
    const customersStore = db.createObjectStore('customers', { keyPath: 'pk' });
    const postRequests = db.createObjectStore('collections', { autoIncrement: true });
  };
}

const addItem = (item, storeName) => {
  const request = db.transaction(storeName, 'readwrite')
    .objectStore(storeName)
    .add(item);

  request.onsuccess = () => {
    console.log(`New item added with key: ${request.result}`);
  }

  request.onerror = (err) => {
    console.error(`Error to add new item: ${err}`)
  }
}

const addItems = (items, storeName) => {
  const transaction = db.transaction(storeName, 'readwrite');

  transaction.oncomplete = function (event) {
    console.log('All the items added successfully')
  };

  transaction.onerror = function (event) {
    console.error('Error to add items');
  };

  const objectStore = transaction.objectStore(storeName);

  for (const item of items) {
    const request = objectStore.add(item);

    request.onsuccess = () => {
      console.log(`New item added with key: ${request.result}`);
    }

    request.onerror = (err) => {
      console.error(`Error to add new item: ${err}`)
    }
  }
}

const removeItem = (key, storeName) => {
  const request = db.transaction(storeName, 'readwrite')
    .objectStore(storeName)
    .delete(key);

  request.onsuccess = () => {
    console.log(`Item deleted with key: ${key}`);
  }

  request.onerror = (err) => {
    console.error(`Error to delete item: ${err}`)
  }
}

const emptyStore = storeName => {
  const request = db.transaction(storeName, 'readwrite')
    .objectStore(storeName)
    .clear();

  request.onsuccess = () => {
    console.log(`Object Store "${storeName}" emptied`);
  }

  request.onerror = (err) => {
    console.error(`Error to empty Object Store: ${storeName}`)
  }
}

const getItem = (key, storeName) => {
  return new Promise((res, rej) => {
    const request = db.transaction(storeName)
      .objectStore(storeName)
      .get(key);

    request.onsuccess = (event) => {
      const items = request.result;
      res(items);
    };

    request.onerror = (err) => {
      rej(`Error to get item information: ${err}`);
    };
  });
}

const getAllItems = storeName => {
  return new Promise((res, rej) => {
    const request = db.transaction(storeName)
      .objectStore(storeName)
      .getAll();

    request.onsuccess = (event) => {
      const items = request.result;
      res(items);
    };

    request.onerror = (err) => {
      rej(`Error to get all items: ${err}`);
    };
  });
}

const getAllKeys = storeName => {
  return new Promise((res, rej) => {
    const request = db.transaction(storeName)
      .objectStore(storeName)
      .getAllKeys();

    request.onsuccess = (event) => {
      const keys = request.result;
      res(keys);
    };

    request.onerror = (err) => {
      rej(`Error to get all keys: ${err}`);
    };
  });
}

const updateItem = (key, storeName) => {
  const objectStore = db.transaction(storeName)
    .objectStore(storeName);

  const request = objectStore.get(key);

  request.onsuccess = () => {
    const item = request.result;

    // Create a request to update
    const updateRequest = objectStore.update(item);

    updateRequest.onsuccess = () => {
      console.log(`Item updated with key: ${key}`)
    }
  }
}

// Check indexedDB support
const idbSupport = () => {
  // Check for indexedDB support
  if (!('indexedDB' in window)) {
    syncContainer.classList.remove('show');
    console.log("This browser doesn't support IndexedDB");
    return false;
  } else {
    syncContainer.classList.add('show');
    return true;
  }
}

// Show message when app is offline
const updateOnlineStatus = (status = null) => {
  let condition = null;
  if (status) {
    condition = status;
  } else {
    condition = navigator.onLine ? 'online' : 'offline';
  }
  if (condition == 'online') {
    // Hide message when network is available and check if there is support
    // for indexedDB to show sync button
    offline.classList.remove('show');
    idbSupport();
  } else {
    // Show a message if network is not available
    offline.classList.add('show');
    syncContainer.classList.remove('show');
  }
}

// Shows a badge when there are collections pending to be sent to the server
const showPendingRequestsBadge = async () => {
  const storedRequests = await getAllItems('collections');
  if (storedRequests.length > 0) {
    pendingRequests.classList.add('show');
  }
}

// Send pending POST requests to the server
const sendPendingRequests = async () => {
  const storedRequests = await getAllItems(COLLECTIONS_STORE_NAME);
  const storedRequestsKeys = await getAllKeys(COLLECTIONS_STORE_NAME);
  if (storedRequests && storedRequestsKeys) {
    // New csrf token
    const csrftoken = getCookie('csrftoken');

    storedRequests.map(async (reqBlob, idx) => {
      // Convert blob to text
      const reqText = await new Response(reqBlob).text();
      // Convert text to Params
      const params = new URLSearchParams(reqText);
      // Update old csrf token with new csrf token
      params.set('csrfmiddlewaretoken', csrftoken);
      fetch('/collections/create/', {
        method: 'POST',
        // Convert params to text again
        body: params.toString(),
        // Send form content type and csrf token headers
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': csrftoken,
        },
        mode: 'same-origin',
      })
        .then(response => {
          if (response.status == 200) {
            removeItem(storedRequestsKeys[idx], COLLECTIONS_STORE_NAME);
          }
        })
        .catch(err => {
          alert(err)
        });
    });
  }
}

// Fetch server for updated data and update local database
const synchronizeLocalDatabase = async () => {
  fetchAPI(URL, 'GET', 'application/json').then(async (res) => {
    if (res) {
      const localStorage = window.localStorage;
      // I get the value of last-update to check if have been changes since the last update
      const lastUpdate = await localStorage.getItem('last-update');
      if (!lastUpdate || res.last_update != lastUpdate) {
        // If last-update value doesn't exists or has changed
        localStorage.setItem('last-update', res.last_update);
        // Check if there are pending request
        const checkStoredRequests = await getAllKeys(COLLECTIONS_STORE_NAME);
        if (checkStoredRequests.length > 0) {
          // If there are pending requests, then show a notification to the user
          console.log('Hay requests pendientes');
        } else {
          // If there are no pending requests, then update the database
          // Empty database
          emptyStore('sales');
          emptyStore('installments');
          emptyStore('customers');
          // Insert sales
          const sales_keys = Object.keys(res.sales);
          for (var key of sales_keys) {
            const data = {
              'customer': key,
              'sales': res.sales[key]
            }
            addItem(data, 'sales');
          }
          // Insert installments
          const installments_keys = Object.keys(res.installments);
          for (var key of installments_keys) {
            const data = {
              'customer': key,
              'installments': res.installments[key]
            }
            addItem(data, 'installments');
          }
          // Insert customers
          const customers = Object.values(res.customers);
          addItems(customers, 'customers');
        }
      }
    }
  });
}

//// EVENTS ////

syncButton.addEventListener('click', async (e) => {
  // 1 - SEND PENDING REQUESTS TO THE SERVER
  sendPendingRequests();
  // 2 - FETCH DATA FROM THE SERVER AND STORE IT IN THE DATABASE
  synchronizeLocalDatabase();
});

window.addEventListener('offline', (e) => {
  updateOnlineStatus('offline');
});

window.addEventListener('online', (e) => {
  updateOnlineStatus('online');
});

document.addEventListener('served-offline-page', (e) => {
  updateOnlineStatus('offline');
})

// Init app
const init = () => {
  if (idbSupport()) {
    openDatabase();
  }
}

init();

export { addItem, addItems, removeItem, emptyStore, getItem, getAllItems, updateItem, db };