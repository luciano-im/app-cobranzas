//// IMPORTS ////

import { fetchAPI } from "./utils.js";
import { db } from "./sync.js";

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

const createSale = (sale, installments) => {
  // Clone the empty form and update its index
  const newSale = emptySale.cloneNode(true);
  newSale.classList.add('sale');
  newSale.classList.remove('empty-sale');

  newSale.querySelector('.id').innerText = sale.id;
  newSale.querySelector('.date').innerText = sale.date;
  newSale.querySelector('.installments').innerText = sale.installments;
  newSale.querySelector('.paid-amount').innerText = sale.paid_amount;
  newSale.querySelector('.pending-balance').innerText = sale.pending_balance;

  const products = newSale.querySelector('.breadcrumb');
  for (var i = 0; i < sale.products.length; i++) {
    products.innerHTML += `<li class="breadcrumb-item">${sale.products[i]}</li>`;
  }

  createInstallments(sale.id, newSale, installments.installments);
}

const createInstallments = (saleId, saleElement, installments) => {
  const tableNextInstallment = saleElement.querySelector('.next-installment tbody');
  const tablePendingInstallments = saleElement.querySelector('.pending-installments tbody');
  const collapseButtonText = saleElement.querySelector('.accordion-button span');

  if (installments['partial'].length > 0) {
    createInstallmentForm(tableNextInstallment, installments['partial']);
  }

  if (installments['next'].length > 0) {
    createInstallmentForm(tableNextInstallment, installments['next']);
  }

  if (installments['pending'].length > 0) {
    collapseButtonText.innerText = "Ver cuotas pendientes";
    createInstallmentForm(tablePendingInstallments, installments['pending']);
  } else {
    collapseButtonText.innerText = "No hay mas cuotas pendientes";
  }

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
  fetchAPI(url, 'GET', 'application/json').then((res) => {
    if (res) {
      selectedCustomerInput.setAttribute('value', selectCustomer.value);
      const sales = Object.values(res.sales[selectCustomer.value]);
      const installments = res.installments[selectCustomer.value];
      sales.forEach(item => {
        createSale(item, installments[item.id]);
      });
    } else {
      const getSales = db.transaction('sales').objectStore('sales').get(selectCustomer.value);
      const getInstallments = db.transaction('installments').objectStore('installments').get(selectCustomer.value);
      getSales.onsuccess = event_s => {
        const sales = getSales.result || null;
        getInstallments.onsuccess = event_i => {
          const installments = getInstallments.result || null;

          sales.sales.forEach(item => {
            createSale(item, installments.installments[item.id]);
          });
        }
      }
    }
  });
});