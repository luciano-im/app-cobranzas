/** @class Wrapper around IndexedDB database */

export class IndexedDB {
  'use strict';
  /**
  * Creates an instance of an IndexedDB database
  *
  * @param {String} name The name of the database
  * @param {Number} version The database version number
  * @param {Array} stores Stores (with name and options) to be created
  */
  constructor(name, version, stores) {
    this.db;
    this.name = name;
    this.version = version;
    this.stores = stores;
  }

  /**
  * Checks support for IndexedDB
  */
  static idbSupported() {
    if (!('indexedDB' in window)) {
      throw new IndexedDBNotSupportedError('IndexedDB not supported');
    } else {
      return true;
    }
  }

  /**
  * Validate indexedDB support and create a new instance of IndexedDB
  *
  * @param {String} name The name of the database
  * @param {Number} version The database version number
  * @param {Array} stores An array of store objects with name and options
  *                       [{name: xx, options: {keyPath: xx, ...}}, ...]
  */
  static create(name, version, stores) {
    return new Promise((res, rej) => {
      if (this.idbSupported() == true) {
        if (name.length > 0 && version > 0 && stores.length > 0) {
          res(new IndexedDB(name, version, stores));
        } else {
          rej('Object could not be created');
        }
      }
    });
  }

  /**
  * Open an indexedDB database connection
  */
  open() {
    return new Promise((res, rej) => {
      const request = window.indexedDB.open(this.name, this.version);

      request.onerror = e => {
        rej(`IndexedDB error: ${e.target.error}`);
      };

      request.onsuccess = e => {
        this.db = e.target.result;
        res();
      };

      request.onupgradeneeded = e => {
        this.db = request.result;
        this.stores.map(store => {
          this.db.createObjectStore(store.name, { ...store.options });
        });
        res();
      };
    });
  }

  /**
  * Add an item to an Object Store
  *
  * @param {Object} item The item to add
  * @param {String} store The store where the item will be added
  */
  add(item, store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store, 'readwrite').objectStore(store).add(item);

      request.onsuccess = e => {
        console.log(`New item added with key: ${e.target.result}`);
        res();
      }

      request.onerror = e => {
        rej(`Error to add new item: ${e.target.error}`);
      };
    });
  }

  /**
  * Add more than one item to an Object Store
  *
  * @param {Array} items The items to add
  * @param {String} store The store where the items will be added
  */
  addMany(items, store) {
    return new Promise((res, rej) => {
      const transaction = this.db.transaction(store, 'readwrite');

      transaction.oncomplete = e => {
        console.log('All items were added successfully');
        res();
      };

      transaction.onerror = e => {
        rej(`Error adding new items: ${e.target.error}`);
      };

      const objectStore = transaction.objectStore(store);

      for (const item of items) {
        const request = objectStore.add(item);

        request.onsuccess = e => {
          console.log(`New item added with key: ${e.target.result}`);
        }

        request.onerror = e => {
          console.error(`Error to add new item: ${e.target.error}`);
        }
      }
    });
  }

  /**
  * Get an item from an Object Store
  *
  * @param {Object} key The item to get
  * @param {String} store The store where the item will be searched
  */
  get(key, store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store).objectStore(store).get(key);

      request.onsuccess = e => {
        const items = e.target.result;
        res(items);
      };

      request.onerror = e => {
        rej(`Error to get item: ${e.target.error}`);
      };
    });
  }

  /**
  * Get all items from an Object Store
  *
  * @param {String} store The store to get all items
  */
  getAll(store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store).objectStore(store).getAll();

      request.onsuccess = (e) => {
        const items = e.target.result;
        res(items);
      };

      request.onerror = (e) => {
        rej(`Error to get all items: ${e.target.error}`);
      };
    });
  }

  /**
  * Get all keys from an Object Store
  *
  * @param {String} store The store to get all keys
  */
  getAllKeys(store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store).objectStore(store).getAllKeys();

      request.onsuccess = e => {
        const keys = e.target.result;
        res(keys);
      };

      request.onerror = e => {
        rej(`Error to get all keys: ${e.target.error}`);
      };
    });
  }

  /**
  * Update an item from an Object Store
  *
  * @param {Object} key The item to update
  * @param {String} store The store where the item will be updated
  */
  update(key, store) {
    return new Promise((res, rej) => {
      const objectStore = this.db.transaction(store).objectStore(store);
      const request = objectStore.get(key);

      request.onerror = e => {
        rej(`Item not found: ${e.target.error}`);
      };

      request.onsuccess = e => {
        const item = e.target.result;
        const updateRequest = objectStore.update(item);

        updateRequest.onsuccess = ue => {
          console.log(`Item updated with key: ${ue.target.result}`);
          res();
        }

        updateRequest.onerror = ue => {
          rej(`Error updating item: ${ue.target.error}`);
        }
      }
    });
  }

  /**
  * Remove an item from an Object Store
  *
  * @param {Object} key The item to remove
  * @param {String} store The store where the item will be removed
  */
  remove(key, store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store, 'readwrite').objectStore(store).delete(key);

      request.onsuccess = e => {
        console.log(`Removed item with key: ${key}`);
        res();
      }

      request.onerror = e => {
        rej(`Error to remove item: ${e.target.error}`);
      }
    });
  }

  /**
  * Delete all items from an Object Store
  *
  * @param {String} store The store to empty
  */
  emptyStore(store) {
    return new Promise((res, rej) => {
      const request = this.db.transaction(store, 'readwrite').objectStore(store).clear();

      request.onsuccess = e => {
        console.log(`Store "${store}" emptied`);
        res();
      }

      request.onerror = e => {
        rej(`Error to empty Store: ${e.target.error}`);
      }
    });
  }
}


/** @class Exception to return if IndexedDB is not supported */

export class IndexedDBNotSupportedError extends Error {
  /**
  * Instantiate a new IndexedDBNotSupportedError exception
  *
  * @param {String} message The message of the exception
  */
  constructor(message) {
    super(message)
    this.name = 'IndexedDBNotSupportedError'
  }
}