//// IMPORTS ////

import { formatNumber } from "./utils.js";
import { IndexedDB } from './IndexedDB.js';

//// CONSTANTS & HELPERS ////

// TODO: Load this settings from the same source as Sync.js
// Import db from sync.js doesn't work because sync.js isn't being used so db throw errors because is closed
// *** REPLICATED FROM SYNC.JS ***
let db;
const COLLECTIONS_STORE_NAME = 'collections';
const stores = [
  { name: 'sales', options: { keyPath: 'customer' } },
  { name: 'installments', options: { keyPath: 'customer' } },
  { name: 'customers', options: { keyPath: 'pk' } },
  { name: COLLECTIONS_STORE_NAME, options: { keyPath: 'customer' } }
];

const city = {
  ARR: 'Arrecifes',
  SAR: 'Capitan Sarmiento',
  SAL: 'Salto'
};

let total = 0.0;

//// DOM ACCESS ////

const receiptDate = document.querySelector('.receipt-header .date');
const receiptHour = document.querySelector('.receipt-header .hour');
// const receiptID = document.querySelector('.receipt-header .id');
const customerName = document.querySelector('.customer .customer-name');
const customerCity = document.querySelector('.customer .city');
const customerTel = document.querySelector('.customer .telephone');
const detailInstallments = document.querySelector('.installments');
const totalTag = document.querySelector('.total-value');

//// FUNCTIONS ////

const getLocalCollectionID = () => {
  // split the pathname by slash character, remove empty strings and get the last two elements
  // [customerID, collectionTimestamp]
  const urlParams = new URLSearchParams(window.location.search);
  return [urlParams.get('customer'), urlParams.get('timestamp')];
}

const getStoredRequest = async customer => {
  return await db.get(customer, COLLECTIONS_STORE_NAME);
}

// const getStoredRequestsKeys = async () => {
//   return await getAllKeys(COLLECTIONS_STORE_NAME);
// }

// const createTable = async (collections, collectionsId) => {
//   let numRow = 0;
//   collectionsId.map((id, idx) => {
//     numRow++;
//     createRow(collections[idx], id, numRow);
//   })
// }

// const createRow = async (data, id, numRow) => {
//   // Clone the empty form and update its index
//   const newRow = emptyRow.cloneNode(true);
//   newRow.classList.remove('empty-row');

//   const customer = await getItem(parseInt(data.customer), 'customers');
//   const installments = Object.values(data.installments);
//   const date = dayjs(data.date).format('DD/MM/YYYY');
//   const paidAmount = calculatePaidAmount(installments);

//   // Data for sale header
//   newRow.querySelector('.id').innerText = numRow;
//   newRow.querySelector('.date').innerText = date;
//   newRow.querySelector('.customer').innerText = customer.name;
//   newRow.querySelector('.paid-amount').innerText = formatNumber(paidAmount);
//   newRow.querySelector('.receipt-button').href = `/collections/print/local/${id}`;
//   unsynchronizedCollectionTable.appendChild(newRow);
// }

// const calculatePaidAmount = installments => {
//   return installments.reduce((accumulator, item) => {
//     return accumulator + parseFloat(item.amount);
//   }, 0);
// }

//// EVENTS ////

window.addEventListener('DOMContentLoaded', async () => {
  const collectionID = getLocalCollectionID();
  const customer = collectionID[0];
  const timestamp = collectionID[1];

  // Open indexedDB database
  db = await IndexedDB.create('cobranzas', 1, stores);
  await db.open();

  const collections = await getStoredRequest(customer);
  const collection = collections.data.filter(c => c.date == timestamp)[0];

  if (collection) {
    const customerData = await db.get(parseInt(customer), 'customers');
    // Update header
    const date = dayjs(collection.date).format('DD/MM/YYYY');
    const hour = dayjs(collection.date).format('HH:MM');
    receiptDate.innerText = date;
    receiptHour.innerText = hour;
    customerName.innerText = customerData.name
    customerCity.innerText = `${customerData.address} - ${city[customerData.city]}`;
    customerTel.innerText = customerData.telephone;

    // CUOTAS
    const salesID = [];
    // Creates an array of sales ID without repeated items
    Object.keys(collection.installments).map(key => {
      const id = key.split('-')[0];
      if (!salesID.includes(id)) {
        salesID.push(parseInt(id));
      }
    });


    let pendingBalance = {};
    Object.values(collection.installments).map(installment => {
      if (!pendingBalance.hasOwnProperty(installment.sale)) {
        pendingBalance[installment.sale] = 0;
      }
      pendingBalance[installment.sale] += parseFloat(installment.amount);
    });

    const salesRecords = await db.get(customer, 'sales');

    let sales = {};
    salesRecords.sales.map(sale => {
      if (salesID.includes(sale.id)) {
        sales[sale.id] = {
          installments: sale.installments,
          date: sale.date,
          products: sale.products,
          pendingBalance: parseFloat(sale.pending_balance) - pendingBalance[sale.id]
        }
      }
    });

    let template = '<h3>Detalle de Cuotas</h3>';

    Object.values(collection.installments).map(installment => {
      let products = '';
      sales[installment.sale].products.map(p => {
        products += `<li>${p}</li>`;
      });

      template += `<p class="line"><span></span></p>
                  <table class="installment-detail">
                    <tr>
                      <td>Importe:</td>
                      <td><b>$${formatNumber(parseFloat(installment.amount))}</b></td>
                    </tr>
                    <tr>
                      <td>Cuota:</td>
                      <td>${installment.installment} de ${sales[installment.sale].installments}</td>
                    </tr>
                    <tr>
                      <td>Venta:</td>
                      <td>#${installment.sale}</td>
                    </tr>
                    <tr>
                      <td>Fecha de Venta:</td>
                      <td>${dayjs(sales[installment.sale].date).format('DD/MM/YYYY')}</td>
                    </tr>
                    <tr>
                      <td colspan="2">${products}</td>
                    </tr>
                    <tr>
                      <td>Saldo:</td>
                      <td>$${formatNumber(sales[installment.sale].pendingBalance)}</td>
                    </tr>
                  </table>`;

      total += parseFloat(installment.amount);
    });

    detailInstallments.innerHTML = template;

    // TOTAL
    totalTag.innerText = `$${formatNumber(total)}`;
  }
});