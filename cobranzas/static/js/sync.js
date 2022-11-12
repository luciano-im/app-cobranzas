//// IMPORTS ////

import { fetchAPI } from "./utils.js";


//// CONSTANTS & HELPERS ////

const URL = `/collections/data/`;
// Database connection (IDBDatabase)
let db;


//// DOM ACCESS ////

const syncContainer = document.querySelector('.synchronization');
const syncLastUpdate = document.querySelector('.synchronization .last-sync');
const syncButton = document.querySelector('.synchronization button');


//// FUNCTIONS ////

// Check for indexedDB support
if (!('indexedDB' in window)) {
  console.log("This browser doesn't support IndexedDB");
} else {
  syncContainer.classList.add('show');
  createDatabase();
}

const createDatabase = () => {
  const request = window.indexedDB.open('cobranzas', 1);

  request.onerror = (e) => {
    console.error(`IndexedDB error: ${request.errorCode}`);
  };

  request.onsuccess = (e) => {
    console.info('Successful database connection');
    db = request.result;
  };

  request.onupgradeneeded = (e) => {
    console.info('Database created');
    const db = request.result;

    const salesStore = db.createObjectStore('sales', { keyPath: 'id' });
    const installmentsStore = db.createObjectStore('installments', { keyPath: 'id' });
    const customersStore = db.createObjectStore('customers', { keyPath: 'id' });
  };
}

const addItem = (item, storeName, operation) => {
  const request = db.transaction(storeName, operation)
    .objectStore(storeName)
    .add(item);

  request.onsuccess = () => {
    console.log(`New item added with key: ${request.result}`);
  }

  request.onsuccess = (err) => {
    console.error(`Error to add new item: ${err}`)
  }
}

const removeItem = (key, storeName, operation) => {
  const request = db.transaction(storeName, operation)
    .objectStore(storeName)
    .delete(key);

  request.onsuccess = () => {
    console.log(`Item deleted with key: ${request.result}`);
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
  const request = db.transaction(storeName)
    .objectStore(storeName)
    .get(key);

  request.onsuccess = () => {
    const item = request.result;
    return item;
  }

  request.onerror = (err) => {
    console.error(`Error to get item information: ${err}`)
  }
}

const getAllItems = storeName => {
  const request = db.transaction(storeName)
    .objectStore(storeName)
    .getAll();

  request.onsuccess = () => {
    const items = request.result;

    console.log('Got all the items');
    console.table(items)

    return items;
  }

  request.onerror = (err) => {
    console.error(`Error to get all items: ${err}`)
  }
}

const updateItem = (key, storeName) => {
  const objectStore = db.transaction(storeName)
    .objectStore(storeName);

  const request = objectStore.get(key);

  request.onsuccess = () => {
    const item = request.result;

    // Change the property
    //item.name = 'Fulanito';

    // Create a request to update
    const updateRequest = objectStore.update(item);

    updateRequest.onsuccess = () => {
      console.log(`Item updated with key: ${updateRequest.result}`)
    }
  }
}

//// EVENTS ////

syncButton.addEventListener('click', (e) => {
  fetchAPI(URL, 'GET', 'application/json').then((res) => {
    if (res) {
      console.log(res);
    }
  });
});
