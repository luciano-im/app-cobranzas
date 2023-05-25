//// IMPORTS ////

import { fetchAPI } from "./utils.js";
import { db, COLLECTIONS_STORE_NAME, getItem, getAllItems } from "./sync.js";

//// CONSTANTS & HELPERS ////

// Keep the formsets numeration
var numForm = 0;
// Variable to keep the total amount when user checks or changes installments amount
let total = 0.0;


//// DOM ACCESS ////

// Main form
const installmentsForm = document.querySelector('.data-container form');
// Filter customer form
const filterCustomerForm = document.getElementById('filter-customer');
const selectCustomer = filterCustomerForm.querySelector('#select-customer');
// Sales container were sales (emptySale) will be inserted
const salesContainer = document.querySelector('.data-container .sales-container');
// Empty sale and formset structure to copy, replace data and insert into the DOM
const emptySale = document.querySelector('.empty-data .empty-sale');
const emptyForm = document.querySelector('.empty-data .empty-form');
// Hidden input to store the selected customer
const selectedCustomerInput = document.querySelector('.create-collection input.selected-customer');
// Total forms input (management form)
const formsetTotalForms = document.querySelector('.create-collection input[name="collection-TOTAL_FORMS"]');
// Total tag to keep the total amount
const totalTag = document.getElementById('total');


//// FUNCTIONS ////

const createSale = (sale, installments, storedInstallments) => {
  // Calculate the sum of stored installments
  let paidAmount = 0.00;
  if (storedInstallments.length > 0) {
    paidAmount = storedInstallments.reduce((accumulator, item) => {
      return accumulator + parseFloat(item.amount);
    }, 0);
  }

  // Clone the empty form and update its index
  const newSale = emptySale.cloneNode(true);
  newSale.classList.add('sale');
  newSale.classList.remove('empty-sale');

  // Data for sale header
  newSale.querySelector('.id').innerText = sale.id;
  newSale.querySelector('.date').innerText = sale.date;
  newSale.querySelector('.installments').innerText = sale.installments;
  newSale.querySelector('.paid-amount').innerText = parseFloat(sale.paid_amount) + paidAmount;
  newSale.querySelector('.pending-balance').innerText = parseFloat(sale.pending_balance) - paidAmount;
  // List of sold products
  const products = newSale.querySelector('.breadcrumb');
  for (var i = 0; i < sale.products.length; i++) {
    products.innerHTML += `<li class="breadcrumb-item">${sale.products[i]}</li>`;
  }
  // Create the installments layout
  createInstallments(sale.id, newSale, installments.installments, storedInstallments);
}

const createInstallments = (saleId, saleElement, installments, storedInstallments) => {
  // Initialize an array to store the stored installments ID
  let storedInstallmentsID = [];
  // Initialize an object to store the paid amount of each installment
  // Each installment could have more than one record or been collected partially in different collections
  // {installmentID: paidAmount, ...}
  let storedInstallmentsData = {};
  if (storedInstallments.length > 0) {
    storedInstallments.map(el => {
      const installmentID = parseInt(el.installment);
      if (!storedInstallmentsID.includes(installmentID)) {
        storedInstallmentsID.push(installmentID);
        storedInstallmentsData[installmentID] = 0;
      }
      storedInstallmentsData[installmentID] += parseFloat(el.amount);
    });
  }

  // Combine synced data with pending installments stored in indexedDB
  // I create a new object with updated installments called "installmentsResponse"

  // Get the installments container (partial, next, pending) to iterate over
  const installmentsContainers = Object.keys(installments);
  // Initialize the object
  let installmentsResponse = {};
  // Loop over the installments of each container
  installmentsContainers.map(container => {
    // Initialize an array to store the ID of partially paid installments
    let partialInstallments = [];
    installmentsResponse[container] = installments[container].filter(el => {
      // Remove cancelled installments
      if (storedInstallmentsID.includes(el.installment)) {
        if (el.installment_amount - el.paid_amount - storedInstallmentsData[el.installment] !== 0) {
          return el;
        } else {
          // Delete installment ID
          storedInstallmentsID.splice(storedInstallmentsID.indexOf(el.installment), 1);
        }
      } else {
        return el;
      }
    }).map((el, index) => {
      // Update installments paid amount
      if (storedInstallmentsID.includes(el.installment)) {
        el.paid_amount = el.paid_amount + storedInstallmentsData[el.installment];
        if (container !== 'partial') {
          partialInstallments.push(index);
        }
        // Delete installment ID
        storedInstallmentsID.splice(storedInstallmentsID.indexOf(el.installment), 1);
      }
      return el;
    });

    // Move installments to "partial" installments array
    partialInstallments.map(installmentID => {
      installmentsResponse['partial'].push(installmentsResponse[container][installmentID]);
      installmentsResponse[container].splice(installmentID, 1);
    });
  });


  // If "next" array is empty but not "pending" array, move the first installment from "pending" to "next"
  if (installmentsResponse['next'].length == 0 && installmentsResponse['pending'].length > 0) {
    installmentsResponse['next'].push(installmentsResponse['pending'][0]);
    installmentsResponse['pending'].splice(0, 1);
  }

  // Get the DOM object from each section to create the layout
  const tableNextInstallment = saleElement.querySelector('.next-installment tbody');
  const tablePendingInstallments = saleElement.querySelector('.pending-installments tbody');
  const collapseButtonText = saleElement.querySelector('.accordion-button span');

  // Fill DOM objects with the installments
  if (installmentsResponse['partial'].length > 0) {
    createInstallmentForm(tableNextInstallment, installmentsResponse['partial']);
  }

  if (installmentsResponse['next'].length > 0) {
    createInstallmentForm(tableNextInstallment, installmentsResponse['next']);
  }

  if (installmentsResponse['pending'].length > 0) {
    collapseButtonText.innerText = "Ver cuotas pendientes";
    createInstallmentForm(tablePendingInstallments, installmentsResponse['pending']);
  } else {
    collapseButtonText.innerText = "No hay mas cuotas pendientes";
  }

  // Update form ID and append form to the DOM
  saleElement.innerHTML = saleElement.innerHTML.replace(/__sale_pk__/g, saleId);
  salesContainer.appendChild(saleElement);

  // Set the total quantity of forms
  formsetTotalForms.setAttribute('value', numForm);
}

const createInstallmentForm = (parent, installments) => {
  for (var i = 0; i < installments.length; i++) {
    // Clone the empty form and update its index
    const newForm = emptyForm.cloneNode(true);
    newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, numForm);
    newForm.classList.remove('empty-form');

    // Calculate the maximum payment amount
    const paidAmount = installments[i]['paid_amount'];
    const installmentAmount = installments[i]['installment_amount'];
    const payment = paidAmount > 0 ? installmentAmount - paidAmount : installmentAmount;

    newForm.querySelector(`input[name="collection-${numForm}-installment"]`).setAttribute('value', installments[i]['installment']);
    newForm.querySelector(`input[name="collection-${numForm}-sale_id"]`).setAttribute('value', installments[i]['sale_id']);
    newForm.querySelector(`input[name="collection-${numForm}-group"]`).setAttribute('value', installments[i]['group']);
    newForm.querySelector('.installment span').innerText = installments[i]['installment'];
    newForm.querySelector('.installment-amount input').setAttribute('value', installmentAmount.toFixed(2));
    newForm.querySelector('.paid-amount input').setAttribute('value', paidAmount.toFixed(2));
    newForm.querySelector('.amount input').setAttribute('value', "0.00");
    // Set the max attribute
    newForm.querySelector('.amount input').setAttribute('max', payment);

    parent.appendChild(newForm);

    numForm++;
  }
}

const checkboxChangeEventHandler = checkbox => {
  // Get the form ID from checkbox name attribute
  const formID = checkbox.name.split('-')[1];
  // Get amount input, installment amount and paid amount values
  const paymentInput = document.getElementById(`id_collection-${formID}-amount`);
  const totalAmount = parseFloat(document.getElementById(`id_collection-${formID}-installment_amount`).value);
  const paidAmount = parseFloat(document.getElementById(`id_collection-${formID}-paid_amount`).value);

  // Preserves old value in the data attribute "data-old-value"
  paymentInput.dataset.oldValue = paymentInput.value || 0.0;

  // When checkbox change its state:
  // 1. the amount input is completed with the pending amount
  // 2. the total is updated
  if (checkbox.checked) {
    const payment = paidAmount > 0 ? totalAmount - paidAmount : totalAmount;
    paymentInput.value = payment.toFixed(2);
    updateTotal(payment);
  } else {
    updateTotal(-parseFloat(paymentInput.value));
    paymentInput.value = 0.0.toFixed(2);
  }
};

const paymentInputChangeEventHandler = input => {
  // The change event in amount inputs updates values and totals
  const oldValue = parseFloat(input.dataset.oldValue) || 0.0;
  const currentValue = parseFloat(input.value) || 0.0;
  const maxValue = parseFloat(input.max) || 0.0;

  // If the value entered by the user is greater than the maximum value
  // then use maxValue as the currentValue
  if (currentValue > maxValue) {
    input.value = maxValue.toFixed(2);
    updateTotal(maxValue - oldValue);
  } else {
    updateTotal(currentValue === 0.0 ? -oldValue : currentValue - oldValue);
  }
}

const paymentInputClickEventHandler = input => {
  // When an amount input is clicked, the "data-old-value" attribute is updated
  // preserves old value
  input.dataset.oldValue = input.value;
}

const paymentInputSelectEventHandler = input => {
  // The select event fires when some text has been selected
  // preserves old value
  input.dataset.oldValue = input.value;
};

// Update the total variable and the total layout tag
const updateTotal = amount => {
  total += amount;
  totalTag.innerText = total.toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};


//// EVENTS ////

installmentsForm.addEventListener('change', (e) => {
  if (e.target.type == 'checkbox') {
    checkboxChangeEventHandler(e.target);
  }

  if (e.target.type == 'number') {
    paymentInputChangeEventHandler(e.target);
  }
});

installmentsForm.addEventListener('click', (e) => {
  if (e.target.type == 'number') {
    paymentInputClickEventHandler(e.target);
  }
});

installmentsForm.addEventListener('select', (e) => {
  if (e.target.type == 'number') {
    paymentInputSelectEventHandler(e.target);
  }
});

filterCustomerForm.addEventListener('submit', event => {
  event.preventDefault();
  // Remove data from the previous customer if it exists
  salesContainer.innerHTML = "";
  // Set total to 0
  totalTag.innerText = "0,00";
  total = 0.00;

  const url = `/collections/create/?select-customer=${selectCustomer.value}`;
  fetchAPI(url, 'GET', 'application/json').then(async (res) => {
    selectedCustomerInput.setAttribute('value', selectCustomer.value);
    if (res) {
      // App is online
      const sales = Object.values(res.sales[selectCustomer.value]);
      const installments = res.installments[selectCustomer.value];
      sales.forEach(item => {
        createSale(item, installments[item.id], []);
      });
    } else {
      // If app is offline, then load data from indexedDB
      const storedCollections = await getAllItems(COLLECTIONS_STORE_NAME);
      // Create a variable to store an array of installments for each sale
      // An object like this  {saleID: [installment, installment, installment], ...}
      let pendingCollectionsBySale = {};
      storedCollections.filter(el => {
        // Filter sales for the current customer
        return el.customer == selectCustomer.value;
      }).map(el => {
        // Get the keys from the object
        const keys = Object.keys(el.installments);
        keys.map(key => {
          // Get the sale ID
          const sale = el.installments[key].sale;
          // Check if sale already exists in pendingCollectionsBySale
          if (!pendingCollectionsBySale.hasOwnProperty(sale)) {
            pendingCollectionsBySale[sale] = [];
          }
          // Store installments in the sale ID position
          pendingCollectionsBySale[sale].push(el.installments[key]);
        });
      });

      // Get sales and installments stored in indexedDB
      const sales = await getItem(selectCustomer.value, 'sales');
      const installments = await getItem(selectCustomer.value, 'installments');
      sales.sales.forEach(item => {
        // Get installments for the current sale
        const storedInstallments = pendingCollectionsBySale[item.id] || [];
        // Create sale layout
        createSale(item, installments.installments[item.id], storedInstallments);
      });
    }
  });
});