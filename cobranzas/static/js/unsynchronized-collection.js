//// IMPORTS ////

import { db, COLLECTIONS_STORE_NAME, getItem, getAllItems, getAllKeys } from "./sync.js";

//// CONSTANTS & HELPERS ////

//// DOM ACCESS ////

const unsynchronizedCollectionTable = document.querySelector('.unsynchronized-collection-table tbody');
const emptyRow = unsynchronizedCollectionTable.querySelector('.empty-row');

//// FUNCTIONS ////

const getStoredRequests = async () => {
  return await getAllItems(COLLECTIONS_STORE_NAME);
}

const getStoredRequestsKeys = async () => {
  return await getAllKeys(COLLECTIONS_STORE_NAME);
}

const createTable = async (collections, collectionsId) => {
  let numRow = 0;
  collectionsId.map((id, idx) => {
    numRow++;
    createRow(collections[idx], id, numRow);
  })
}

const createRow = async (data, id, numRow) => {
  console.log(id, data);
  // Clone the empty form and update its index
  const newRow = emptyRow.cloneNode(true);
  newRow.classList.remove('empty-row');

  const customer = await getItem(parseInt(data.customer), 'customers');
  const installments = Object.values(data.installments);
  const date = dayjs(data.date).format('DD/MM/YYYY');

  // Data for sale header
  newRow.querySelector('.id').innerText = numRow;
  newRow.querySelector('.date').innerText = date;
  newRow.querySelector('.customer').innerText = customer.name;
  newRow.querySelector('.paid-amount').innerText = calculatePaidAmount(installments);
  newRow.querySelector('.receipt-button').href = `/collections/print/local/${id}`;
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
  const storedRequestsKeys = await getStoredRequestsKeys();
  createTable(storedRequests, storedRequestsKeys);
});