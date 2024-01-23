'use strict';

//// IMPORTS ////

import { getCookie, formatDate } from "./utils.js";
import { IndexedDB, IndexedDBNotSupportedError } from './IndexedDB.js'


//// CONSTANTS & HELPERS ////

const URL = `/collections/data/`;
const COLLECTIONS_STORE_NAME = 'collections';
// Database connection (IDBDatabase)
let db;
const stores = [
  { name: 'sales', options: { keyPath: 'customer' } },
  { name: 'installments', options: { keyPath: 'customer' } },
  { name: 'customers', options: { keyPath: 'pk' } },
  { name: COLLECTIONS_STORE_NAME, options: { keyPath: 'customer' } }
];
const localStorage = window.localStorage;

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
    syncContainer.classList.add('show');
  } else {
    // Show a message if network is not available
    offline.classList.add('show');
    syncContainer.classList.remove('show');
  }
}

// Shows a badge when there are collections pending to be sent to the server
const showPendingRequestsBadge = async () => {
  const storedRequests = await db.getAll(COLLECTIONS_STORE_NAME);
  if (storedRequests.length > 0) {
    pendingRequests.classList.add('show');
  }
}

// Send pending POST requests to the server
const sendPendingRequests = async () => {
  syncContainer.classList.add('in-progress');

  const storedRequests = await db.getAll(COLLECTIONS_STORE_NAME);
  if (storedRequests.length > 0) {
    // Revoke local database app-last-update
    localStorage.removeItem('app-last-update');

    // New csrf token
    const csrftoken = getCookie('csrftoken');

    await storedRequests.map(async requestsByCustomer => {
      // Stores failed requests to update indexedDB record
      let failedRequests = [];
      // Iterate over each request
      for (const request of requestsByCustomer.data) {
        // Convert blob request to text
        const reqText = await new Response(request.request).text();
        // Convert text to Params
        const params = new URLSearchParams(reqText);
        // Update old csrf token with new csrf token
        params.set('csrfmiddlewaretoken', csrftoken);

        const response = await fetch('/collections/create/', {
          method: 'POST',
          // Convert params to text again
          body: params.toString(),
          // Send form content type and csrf token headers
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrftoken,
          },
          mode: 'same-origin',
        });

        if (!response || response.status !== 200) {
          console.error('Request error!', request);
          failedRequests.push(request);
        }
      }

      // If there are failed requests update indexedDB record
      // If requests were successful then delete indexedDB record
      if (failedRequests.length > 0) {
        let collectionData = {
          customer: requestsByCustomer.customer,
          data: failedRequests
        }
        db.replace(requestsByCustomer.customer, collectionData, COLLECTIONS_STORE_NAME);
      } else {
        db.remove(requestsByCustomer.customer, COLLECTIONS_STORE_NAME);
      }
    });
  }
}

// Fetch server for updated data and update local database
const synchronizeLocalDatabase = async () => {
  const response = await fetch(URL, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (response.ok) {
    // Parse json response
    const result = await response.json();

    if (result) {
      // I get the value of app-last-update to check if have been changes since the last update
      const lastUpdate = await localStorage.getItem('app-last-update');
      if (!lastUpdate || result.last_update != lastUpdate) {
        // If app-last-update value doesn't exists or has changed
        localStorage.setItem('app-last-update', result.last_update);
        // Check if there are pending request
        const checkStoredRequests = await db.getAllKeys(COLLECTIONS_STORE_NAME);
        if (checkStoredRequests.length > 0) {
          // If there are pending requests, then show a notification to the user
          console.log('Hay requests pendientes');
        } else {
          // If there are no pending requests, then update the database
          // Empty database
          db.emptyStore('sales');
          db.emptyStore('installments');
          db.emptyStore('customers');
          // Insert sales
          for (var s of result.sales) {
            const data = {
              'customer': s.pk,
              'sales': s.sale_set
            }
            db.add(data, 'sales');
          }
          // Insert customers
          const customers = Object.values(result.customers);
          db.addMany(customers, 'customers');
        }
      }

      // TODO: Use relative time (10 minutes ago, 2 hours ago)
      // Update last fetch date/time
      const lastSyncDate = formatDate(new Date());
      localStorage.setItem('client-last-update', lastSyncDate);
      // Update last sync in view
      syncLastUpdate.innerText = lastSyncDate;
    }
  }

  syncContainer.classList.remove('in-progress');
}

// TODO: Move this code to the class Sale
const storedCollectionsByCustomer = async customer => {
  let collections = {};
  const storedCollections = await db.get(customer, COLLECTIONS_STORE_NAME);
  if (storedCollections) {
    storedCollections.data.map(collection => {
      const keys = Object.keys(collection.installments);
      keys.map(key => {
        // Installment data
        const { sale, installment, amount } = { ...collection.installments[key] };

        // Check if sale already exists in pendingCollectionsBySale
        if (!collections.hasOwnProperty(sale)) {
          collections[sale] = {};
        }
        // Store installments in the sale ID position
        collections[sale][installment] = { amount: amount };
      });
    });
  }

  return collections;
}

//// EVENTS ////

syncButton.addEventListener('click', async (e) => {
  // 1 - SEND PENDING REQUESTS TO THE SERVER
  await sendPendingRequests();
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
const init = async () => {
  try {
    db = await IndexedDB.create('cobranzas', 1, stores);
    await db.open();
    // Show badge if there are pending requests stored
    showPendingRequestsBadge();

    syncContainer.classList.add('show');
  } catch (err) {
    if (err instanceof IndexedDBNotSupportedError) {
      console.error(err.message);
      syncContainer.classList.remove('show');
    }
  }

  // Update last sync in view
  const clientLastUpdate = localStorage.getItem('client-last-update');
  syncLastUpdate.innerText = clientLastUpdate ? clientLastUpdate : '-';
}

init();

export { db, COLLECTIONS_STORE_NAME, synchronizeLocalDatabase, sendPendingRequests, storedCollectionsByCustomer };