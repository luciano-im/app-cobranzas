'use strict';

//// IMPORTS ////

import { db, storedCollectionsByCustomer, sendPendingRequests, synchronizeLocalDatabase, COLLECTIONS_STORE_NAME } from "./sync.js";
import { Collection, Sale } from './Collection.js';
import { CollectionView } from './CollectionView.js';
import { appendAlert } from "./utils.js";

//// CONSTANTS & HELPERS ////

let collection;


//// DOM ACCESS ////

// Filter customer form
const filterCustomerForm = document.getElementById('filter-customer');
const selectCustomer = filterCustomerForm.querySelector('#select-customer');
// Hidden input to store the selected customer
const selectedCustomerInput = document.querySelector('.create-collection input.selected-customer');
// Create collection form
const createCollectionForm = document.getElementById('create-collection');
const collectionContainer = document.querySelector(".collection-container");
const alertErrors = document.querySelector('.alert-errors');


//// FUNCTIONS ////

const clearForm = () => {
  // Empty current collection view
  collectionContainer.innerHTML = '';
  // Delete collection
  collection = undefined;
  // Reset customer select element
  selectCustomer.selectedIndex = 0;
}

// Return the difference between two objects containing stored collections
function getStoredCollectionsDifference(oldStoredCollections, newStoredCollections) {
  // Check if array contains an object with key and value
  function searchKeyValue(key, value, array) {
    for (let i = 0; i < array.length; i++) {
      if (array[i][key] == value) {
        return array[i];
      }
    }
    return false;
  }

  // The array to return
  let result = [];

  newStoredCollections.map(newCollection => {
    // Check for customer ID in the key "customer" in oldStoredCollections array
    let customerSearched = searchKeyValue('customer', newCollection.customer, oldStoredCollections);
    // If customer is found
    if (customerSearched !== false) {
      newCollection.data.map(collection => {
        // Check if current date is found in the key "date" of customerSearched array
        let collectionSearched = searchKeyValue('date', collection.date, customerSearched.data);
        if (collectionSearched === false) {
          // If date is not found then add the collection to result
          result.push({ customer: newCollection.customer, date: collection.date });
        }
      });
    } else {
      // If customer is not found then add to result all the collections from the current object
      for (let i = 0; i < newCollection.data.length; i++) {
        result.push({ customer: newCollection.customer, date: newCollection.data[i].date });
      }
    }
  });

  return result;
}


//// EVENTS ////

filterCustomerForm.addEventListener('submit', async event => {
  event.preventDefault();
  // Create new collection instance
  collection = new Collection;
  // Delete alert messages
  alertErrors.innerHTML = '';

  const url = `/collections/create/?select-customer=${selectCustomer.value}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (response.ok) {
    // Save customer to hidden input
    selectedCustomerInput.setAttribute('value', selectCustomer.value);
    // Stores sales and installment objects
    let sales;
    let installments;
    // Get pending collections stored in indexedDB
    const storedCollections = await storedCollectionsByCustomer(selectCustomer.value) || {};

    try {
      // Parse json response
      const result = await response.json();

      // App is online
      sales = result.sales[selectCustomer.value];
      installments = result.installments[selectCustomer.value];
    } catch (err) {
      // If app is offline, then load data from indexedDB
      // Get sales and installments stored in indexedDB
      const storedSales = await db.get(selectCustomer.value, 'sales');
      const storedInstallments = await db.get(selectCustomer.value, 'installments');

      sales = storedSales.sales;
      installments = storedInstallments.installments;
    }

    // Add sales instances to collection
    sales.map(sale => {
      collection.addSale(Sale.create(sale.id, sale.date, sale.installments, sale.paid_amount, sale.pending_balance, sale.price, sale.products, installments[sale.id], storedCollections[sale.id]));
    });

    // Create a collection view and render content in the page
    let collectionView = new CollectionView(collection, document.querySelector(".collection-container"));
    collectionView.render();
  } else {
    // Empty current collection view
    collectionContainer.innerHTML = '';
    if (response.status == 500) {
      appendAlert(alertErrors, 'Error en el servidor!', 'warning');
    }
    if (response.status == 403) {
      appendAlert(alertErrors, 'No tienes los permisos necesarios para el cliente seleccionado!', 'warning');
    } else {
      appendAlert(alertErrors, 'Ha ocurrido un problema!', 'warning');
    }
  }
});


createCollectionForm.addEventListener('submit', async event => {
  event.preventDefault();

  // Get a copy of the stored collections
  // Use Promise.resolve to be sure of getting the current state of stored collections, before new collections are added
  let oldStoredCollections = null;
  Promise.resolve(db.getAll(COLLECTIONS_STORE_NAME)).then(values => {
    oldStoredCollections = values;
  });

  // Send the request by hand to check the server response and 
  // update the local database if the request was successful
  fetch(event.target.action, {
    method: 'POST',
    body: new URLSearchParams(new FormData(event.target))
  }).then(async res => {
    if (res.status != 200) {
      console.log('Error saving collection!');
      return false;
    }

    // Get collection ID from response
    const result = await res.json();
    const collectionID = result.collection_id;

    // Empty form and customer select field
    clearForm();

    // Print receipt
    const urlPrintReceipt = `/collections/print/${collectionID}`;
    window.open(urlPrintReceipt, '_blank');

    // Send pending request and update local database
    sendPendingRequests();
    synchronizeLocalDatabase();
  }).catch(async err => {
    // Empty form and customer select field
    clearForm();

    console.log('Error! Server is offline?');
    console.log(err);

    // Get a copy of the stored collections
    // At this point a new collection will have been saved to indexedDB
    const newStoredCollections = await db.getAll(COLLECTIONS_STORE_NAME);
    // Get the difference between the old and new objects containing the stored collections
    // The difference will be the recently added collection
    const storedCollectionsDiff = getStoredCollectionsDifference(oldStoredCollections, newStoredCollections);

    // If a collection was added
    if (storedCollectionsDiff.length > 0) {
      // Get customer and date to format the receipt URL
      const customer = storedCollectionsDiff[0].customer;
      const date = storedCollectionsDiff[0].date;
      // Print receipt
      const urlPrintReceipt = `/collections/print/local/${customer}/${date}`;
      window.open(urlPrintReceipt, '_blank');
    }
  });
});