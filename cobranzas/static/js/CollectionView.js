'use strict';

/** @class Renders the Collection template */

export class CollectionView {
  /**
  * Creates an instance of Collection View
  *
  * @param {Collection} collection Receives an instance of Collection.
  */
  constructor(collection) {
    this.collection = collection;
  }

  /**
  * Renders each sale from the collection
  */
  render() {
    const salesContainer = document.querySelector('.data-container .sales-container');

    const sales = this.collection.getSales();

    sales.forEach(sale => {
      const saleComponent = new SaleComponent(sale);
      salesContainer.insertAdjacentHTML("beforeend", saleComponent.render());
    });
  }
}


/** @class Represents a sale */

class SaleComponent {
  /**
  * Creates the layout for a sale
  *
  * @param {Sale} sale Receives an instance of Sale.
  */
  constructor(sale) {
    this.sale = sale;
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
    const saleInstallments = new SaleInstallmentsComponent(this.sale.getBundledInstallments(), this.sale.id);

    // Generates the template
    let template = `<div class="sale">
                      <div class="sale-header">
                        <div class="sale-details">
                          <span class="badge text-bg-primary">#<span class="id">${this.sale.id}</span></span>
                          <span class="badge text-bg-primary"><span class="date">${this.sale.date}</span></span>
                          <span class="badge text-bg-primary"><span class="installments">${this.sale.installmentsQty}</span> cuotas</span>
                          <span class="badge text-bg-primary">Cobrado: $<span class="paid-amount">${this.sale.paidAmount}</span></span>
                          <span class="badge text-bg-primary">Pendiente: $<span class="pending-balance">${this.sale.pendingBalance}</span></span>
                        </div>
                      </div>
                      <div style="--bs-breadcrumb-divider: '/';" aria-label="breadcrumb" class="products-list">
                        <ol class="breadcrumb" style="font-weight: 700; font-size: 1.3rem;">
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
  */
  constructor(props, saleID) {
    this.partial = props.partial;
    this.current = props.current;
    this.next = props.next;
    this.saleID = saleID;
    this.formID = 0;
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
                          <th scope="col">Cuota</th>
                          <th scope="col">Importe Total</th>
                          <th scope="col">Importe Pagado</th>
                          <th scope="col">A Pagar</th>
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
      const saleInstalmentForm = new SaleInstallmentFormComponent(installment, this.formID)
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
  * @param {Number} formID The ID to assign to the form
  */
  constructor(props, formID) {
    this.props = props;
    this.formID = formID;
  }

  /**
  * Returns a string with the layout of the form, and with the ID already applied.
  */
  render() {
    const paidAmount = this.props.paidAmount;
    const installmentAmount = this.props.installmentAmount;
    const payment = paidAmount > 0 ? installmentAmount - paidAmount : installmentAmount;

    // <input type="hidden" name="collection-__prefix__-group" value="" id="id_collection-__prefix__-group">
    let template = `<tr>
                      <input type="hidden" name="collection-__prefix__-installment" value="${this.props.installment}" id="id_collection-__prefix__-installment">
                      <input type="hidden" name="collection-__prefix__-sale_id" value="${this.props.saleID}" id="id_collection-__prefix__-sale_id">
                      <th scope="row" class="installment">
                        <input type="checkbox" name="collection-__prefix__-checked" id="id_collection-__prefix__-checked"> <span>${this.props.installment}</span>
                      </th>
                      <td class="installment-amount">
                        <input type="number" name="collection-__prefix__-installment_amount" value="${installmentAmount}" readonly="" class="form-control-plaintext" step="any" id="id_collection-__prefix__-installment_amount">
                      </td>
                      <td class="paid-amount">
                        <input type="number" name="collection-__prefix__-paid_amount" value="${paidAmount}" readonly="" class="form-control-plaintext" step="any" id="id_collection-__prefix__-paid_amount">
                      </td>
                      <td class="amount">
                        <div id="div_id_collection-__prefix__-amount" class="mb-3">
                          <input type="number" name="collection-__prefix__-amount" class="payment-input numberinput form-control" step="any" id="id_collection-__prefix__-amount" max="${payment}" value="0.00">
                        </div>
                      </td>
                    </tr>`
      .replace(/__prefix__/g, this.formID);

    return template;
  }
}