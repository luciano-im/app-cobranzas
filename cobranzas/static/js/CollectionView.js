'use strict';

import { formatNumber } from "./utils.js";

/** @class Renders the Collection template */

export class CollectionView {
  /**
  * Creates an instance of Collection View
  *
  * @param {Collection} collection Receives an instance of Collection.
  * @param {object} parent A DOM element where the collection will be displayed
  */
  constructor(collection, parent) {
    this.collection = collection;
    this.total = 0;
    this.totalTag = null;
    this.submitButton = null;
    this.fromFormID = 0;

    // UNBIND EVENTS
    // After re-rendering the after the event listeners attached to 'root-element' still exists
    // To prevent binding the events again, clone the element (cloneNode copy everything except event listeners)
    const rootElement = document.createElement('div');
    rootElement.classList.add('root-element');
    this.rootElement = rootElement.cloneNode(true);
    // Then empty the content of the parent element to delete content from previous View renders
    // and append 'root-element' to the parent container
    parent.innerHTML = '';
    parent.appendChild(this.rootElement);
  }

  /**
  * Renders each sale from the collection
  */
  render() {
    this.setFormsetTotalForms();

    const sales = this.collection.getSales();
    let salesContent = '';
    sales.forEach(sale => {
      const saleComponent = new SaleComponent(sale, this.fromFormID);
      salesContent += saleComponent.render();

      // Update fromFormID
      this.fromFormID += sale.installmentsCount();
    });

    let template = `<div class="sales-container">${salesContent}</div>
                    <div class="totals d-flex flex-column align-items-end">
                      <p class="p-0">Total: $<span id="total">0,00</span></p>
                      <input type="submit" id="submit-collection" value="Guardar" class="btn btn-primary" disabled>
                    </div>`;

    this.rootElement.innerHTML = template;

    this.totalTag = this.rootElement.querySelector('#total');
    this.submitButton = this.rootElement.querySelector('#submit-collection');

    this.bindEvents();
  }

  /**
  * Sets the value of the total forms field with the number of installments
  */
  setFormsetTotalForms() {
    document
      .querySelector('input[name="collection-TOTAL_FORMS"]')
      .setAttribute('value', this.collection.installmentsCount());
  }

  /**
  * Attach the 'change', 'click', and 'select' events to the root element
  */
  bindEvents() {
    this.rootElement.addEventListener('change', e => this._handleChangeEvent(e));
    this.rootElement.addEventListener('click', e => this._handleClickEvent(e));
    this.rootElement.addEventListener('select', e => this._handleSelectEvent(e));
  }

  /**
  * Handles 'change' event when event target is a checkbox or an input of type number
  * 
  * @param {object} event An addEventListener event object
  */
  _handleChangeEvent(event) {
    if (event.target.type == 'checkbox') {
      this._handleCheckboxChangeEvent(event.target);
    }

    if (event.target.type == 'number') {
      this._handlePaymentInputChangeEvent(event.target);
    }
  }

  /**
  * Handles 'click' event when event target is an input of type number
  * 
  * @param {object} event An addEventListener event object
  */
  _handleClickEvent(event) {
    if (event.target.type == 'number') {
      this._handlePaymentInputClickSelectEvent(event.target);
    }
  }

  /**
  * Handles 'select' event when event target is an input of type number
  * 
  * @param {object} event An addEventListener event object
  */
  _handleSelectEvent(event) {
    if (event.target.type == 'number') {
      this._handlePaymentInputClickSelectEvent(event.target);
    }
  }

  /**
  * Handles actions when a checkbox is clicked
  * 
  * @param {object} checkbox A checkbox element
  */
  _handleCheckboxChangeEvent(checkbox) {
    // Get the form ID from checkbox name attribute
    const formID = this._extractFormID(checkbox.name);
    // Get amount input, installment amount and paid amount values
    const paymentInput = this.rootElement.querySelector(`#id_collection-${formID}-amount`);
    const totalAmount = parseFloat(this.rootElement.querySelector(`#id_collection-${formID}-installment_amount`).value);
    const paidAmount = parseFloat(this.rootElement.querySelector(`#id_collection-${formID}-paid_amount`).value);

    // Preserves old value in the data attribute "data-old-value"
    paymentInput.dataset.oldValue = paymentInput.value || 0.0;

    // When checkbox change its state:
    // 1. the amount input is completed with the pending amount
    // 2. the total is updated
    if (checkbox.checked) {
      const payment = paidAmount > 0 ? totalAmount - paidAmount : totalAmount;
      paymentInput.value = payment;
      this._updateTotal(payment);
    } else {
      this._updateTotal(-parseFloat(paymentInput.value));
      paymentInput.value = 0.0;
    }
  };

  /**
  * Handles actions when the payment input changes
  * 
  * @param {object} input An input element
  */
  _handlePaymentInputChangeEvent(input) {
    // Get form ID
    const formID = this._extractFormID(input.name);

    // Get input value and remove spaces
    const inputValue = input.value.trim();

    // Check if inputValue is not null and entered value is not equal to zero
    if (inputValue && parseFloat(inputValue) !== 0.0) {
      // Check the checkbox field
      this.rootElement.querySelector(`input[name=collection-${formID}-checked]`).checked = true;
    } else {
      // Update input value to zero
      input.value = 0.00;
      // Uncheck the collection
      this.rootElement.querySelector(`input[name=collection-${formID}-checked]`).checked = false;
    }

    // The change event in amount inputs updates values and totals
    const oldValue = parseFloat(input.dataset.oldValue) || 0.0;
    const currentValue = parseFloat(input.value) || 0.0;
    const maxValue = parseFloat(input.max) || 0.0;

    // If the value entered by the user is greater than the maximum value
    // then use maxValue as the currentValue
    if (currentValue > maxValue) {
      input.value = maxValue.toFixed(2);
      this._updateTotal(maxValue - oldValue);
    } else {
      this._updateTotal(currentValue === 0.0 ? -oldValue : currentValue - oldValue);
    }
  }

  /**
  * Handles actions when the payment input content is selected
  * 
  * @param {object} input An input element
  */
  _handlePaymentInputClickSelectEvent(input) {
    // When an amount input is clicked, the "data-old-value" attribute is updated
    // The select event fires when some text has been selected
    // preserves old value
    input.dataset.oldValue = input.value;
  }

  /**
  * Updates the total tag in the template, and manages if the submit button must be enabled
  * or disabled, based on the calculated amount.
  * 
  * @param {Number} amount Receives a number to calculate the total amount
  */
  _updateTotal(amount) {
    this.total += amount;
    if (this.total == 0) {
      this.submitButton.disabled = true;
    } else {
      this.submitButton.disabled = false;
    }
    this.totalTag.innerText = this.total.toLocaleString("es-AR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };


  /**
  * Extracts and returns the form ID
  * 
  * @param {String} text Receives a string with format xxxx-formID-xxxx
  */
  _extractFormID(text) {
    return text.split('-')[1];
  }
}


/** @class Represents a sale */

class SaleComponent {
  /**
  * Creates the layout for a sale
  *
  * @param {Sale} sale Receives an instance of Sale.
  * @param {Number} fromFormID The ID from which the installments should be numbered
  */
  constructor(sale, fromFormID) {
    this.sale = sale;
    this.fromFormID = fromFormID;
  }

  /**
  * Renders each sale from the collection
  */
  render() {
    // Sold products
    let saleProducts = '';
    for (var i = 0; i < this.sale.products.length; i++) {
      saleProducts += `<li class="breadcrumb-item">${this.sale.products[i]}</li>`;
    }

    // Sale installments
    const saleInstallments = new SaleInstallmentsComponent(this.sale.getBundledInstallments(), this.sale.id, this.fromFormID);

    // Generates the template
    let template = `<div class="sale">
                      <div class="sale-header">
                        <div class="sale-details">
                          <span class="badge text-bg-primary">#<span class="id">${this.sale.id}</span></span>
                          <span class="badge text-bg-primary"><span class="date">${this.sale.date}</span></span>
                          <span class="badge text-bg-primary"><span class="installments">${this.sale.installmentsQty}</span> cuotas</span>
                          <span class="badge text-bg-primary">Cobrado: $<span class="paid-amount">${formatNumber(this.sale.paidAmount)}</span></span>
                          <span class="badge text-bg-primary">Saldo: $<span class="pending-balance">${formatNumber(this.sale.pendingBalance)}</span></span>
                        </div>
                        <p class="remarks text-secondary mt-2 fst-italic">${this.sale.remarks}</p>
                      </div>
                      <div style="--bs-breadcrumb-divider: '/';" aria-label="breadcrumb" class="products-list">
                        <ol class="breadcrumb">
                          ${saleProducts}
                        </ol>
                      </div>
                      ${saleInstallments.render()}
                    </div>`;

    return template;
  }
}


/** @class Generates the template layout of the installments of a sale */

class SaleInstallmentsComponent {
  /**
  * Generates the layout for the installments
  *
  * @param {object} props Receives the result returned by the method getBundledInstallments() of a sale object
  * @param {Number} saleID The ID of the current sale
  * @param {Number} fromFormID The ID from which the installments should be numbered
  */
  constructor(props, saleID, fromFormID) {
    this.partial = props.partial;
    this.current = props.current;
    this.next = props.next;
    this.saleID = saleID;
    this.formID = fromFormID;
  }

  /**
  * Renders tables with installments elements
  */
  render() {
    let partialAndCurrentInstallments = this.createInstallmentsLayout([...this.partial, ...this.current]);
    let nextInstallments = this.createInstallmentsLayout(this.next);
    const accordionCollapseButtonText = this.next.length > 0 ? "Ver cuotas pendientes" : "No hay mas cuotas pendientes";

    let template = `<table class="table table-hover next-installment">
                      <thead class="table-light">
                        <tr>
                          <th scope="col" class="col-2">Cuota</th>
                          <th scope="col" class="col-3">Importe</th>
                          <th scope="col" class="col-3">Pago</th>
                          <th scope="col" class="col-4">A Pagar</th>
                        </tr>
                      </thead>
                      <tbody class="next-installment-tbody">
                        ${partialAndCurrentInstallments}
                      </tbody>
                    </table>
                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse"
                      data-bs-target="#flush-collapse-${this.saleID}" aria-expanded="false" aria-controls="flush-collapse-${this.saleID}">
                      <span class="button-text">${accordionCollapseButtonText}</span>
                    </button>
                    <div id="flush-collapse-${this.saleID}" class="accordion-collapse collapse" aria-labelledby="flush-heading-${this.saleID}" data-bs-parent="#installments">
                      <table class="table table-hover pending-installments">
                        <tbody>
                          ${nextInstallments}
                        </tbody>
                      </table>
                    </div>`;

    return template;
  }

  /**
  * Returns the layout for the set of installments received
  * 
  * @param {Array} installments An array of installment objects
  */
  createInstallmentsLayout(installments) {
    let layout = '';
    installments.map(installment => {
      const saleInstalmentForm = new SaleInstallmentFormComponent(installment, this.saleID, this.formID)
      layout += saleInstalmentForm.render();
      this.formID++;
    });

    return layout;
  }
}


/** @class Generates the form layout for an installment */

class SaleInstallmentFormComponent {
  /**
  * Creates an instance of the sale installment form class 
  *
  * @param {Installment} props An instance of the Installment class
  * @param {Number} saleID The ID of the current sale
  * @param {Number} formID The ID to assign to the form
  */
  constructor(props, saleID, formID) {
    this.props = props;
    this.saleID = saleID;
    this.formID = formID;
  }

  /**
  * Returns a string with the layout of the form, and with the ID already applied.
  */
  render() {
    const paidAmount = this.props.paidAmount;
    const installmentAmount = this.props.installmentAmount;
    const payment = paidAmount > 0 ? installmentAmount - paidAmount : installmentAmount;

    let template = `<tr>
                      <input type="hidden" name="collection-__prefix__-installment" value="${this.props.installment}" id="id_collection-__prefix__-installment">
                      <input type="hidden" name="collection-__prefix__-sale_id" value="${this.saleID}" id="id_collection-__prefix__-sale_id">
                      <th scope="row" class="installment col-2">
                        <input type="checkbox" name="collection-__prefix__-checked" id="id_collection-__prefix__-checked"> <span>${this.props.installment}</span>
                      </th>
                      <td class="installment-amount col-3">
                        <input type="number" name="collection-__prefix__-installment_amount" value="${installmentAmount}" readonly="" class="form-control-plaintext" step="any" id="id_collection-__prefix__-installment_amount" tabindex="-1">
                      </td>
                      <td class="paid-amount col-3">
                        <input type="number" name="collection-__prefix__-paid_amount" value="${paidAmount}" readonly="" class="form-control-plaintext" step="any" id="id_collection-__prefix__-paid_amount" tabindex="-1">
                      </td>
                      <td class="amount col-4">
                        <div id="div_id_collection-__prefix__-amount" class="mb-3">
                          <input type="number" name="collection-__prefix__-amount" class="payment-input numberinput form-control" step="any" id="id_collection-__prefix__-amount" max="${payment}" value="0.00">
                        </div>
                      </td>
                    </tr>`
      .replace(/__prefix__/g, `${this.formID}`);

    return template;
  }
}