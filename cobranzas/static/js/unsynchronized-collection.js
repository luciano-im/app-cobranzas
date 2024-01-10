'use strict';

//// IMPORTS ////

import { db, COLLECTIONS_STORE_NAME } from "./sync.js";
import { formatNumber } from "./utils.js";

//// CONSTANTS & HELPERS ////

//// DOM ACCESS ////

const unsynchronizedCollectionTable = document.querySelector('.unsynchronized-collection-table tbody');
const emptyRow = unsynchronizedCollectionTable.querySelector('.empty-row');

//// FUNCTIONS ////

const getStoredRequests = async () => {
  return await db.getAll(COLLECTIONS_STORE_NAME);
}

const createTable = async (collectionsByCustomer) => {
  let numRow = 0;
  collectionsByCustomer.map(customerCollection => {
    customerCollection.data.map(collection => {
      numRow++;
      createRow(collection, customerCollection.customer, numRow);
    });
  })
}

const createRow = async (data, customer, numRow) => {
  // Clone the empty form and update its index
  const newRow = emptyRow.cloneNode(true);
  newRow.classList.remove('empty-row');

  const customerRecord = await db.get(parseInt(customer), 'customers');
  const date = dayjs(data.date).format('DD/MM/YYYY');
  const installments = Object.values(data.installments);
  const paidAmount = calculatePaidAmount(installments);

  // // Data for sale header
  newRow.querySelector('.id').innerText = numRow;
  newRow.querySelector('.date').innerText = date;
  newRow.querySelector('.customer').innerText = customerRecord.name;
  newRow.querySelector('.paid-amount').innerText = formatNumber(paidAmount);
  newRow.querySelector('.receipt-button').href = `/collections/print/local?customer=${customer}&timestamp=${data.date}`;
  unsynchronizedCollectionTable.appendChild(newRow);
}

const calculatePaidAmount = installments => {
  return installments.reduce((accumulator, item) => {
    return accumulator + parseFloat(item.amount);
  }, 0);
}

//// EVENTS ////

window.addEventListener('load', async () => {
  const storedRequests = await getStoredRequests();
  createTable(storedRequests);
});