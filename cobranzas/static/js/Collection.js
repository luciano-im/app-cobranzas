'use strict';

/** @class Represents a set of Sales */

export class Collection {
  /**
  * Creates an instance of a Collection
  *
  * @param {Array} sales Stores a list of Sale objects. It is not required to instantiate a new Collection.
  */
  constructor() {
    this.sales = [];
  }

  /**
  * Add a new sale to the list
  */
  addSale(sale) {
    this.sales.push(sale);
  }

  /**
  * Return sales array
  */
  getSales() {
    return this.sales;
  }

  /**
  * Returns the count of installments for the Collection
  */
  installmentsCount() {
    return this.sales.reduce((accumulator, sale) => {
      return accumulator + sale.installmentsCount();
    }, 0);
  }
}


/** @class Represents a Sale including a list of pending installments */

export class Sale {
  ID_ERROR = 'Sale ID can not be null';

  /**
  * Creates an instance of a Collection
  *
  * @param {Number} id The sale ID
  * @param {String} date A string representing a date
  * @param {Number} installmentsQty Quantity of sale installments
  * @param {Number} paidAmount Amount paid for the sale
  * @param {Number} pendingBalance Balance due
  * @param {Number} price Sale price
  * @param {String} remarks Sale's remarks
  * @param {Array} products List of sold products
  * @param {Array} installments List of installment objects
  */
  constructor(id, date, installmentsQty, paidAmount, pendingBalance, price, remarks, products, installments) {
    this.id = id;
    this.date = date;
    this.installmentsQty = installmentsQty;
    this.paidAmount = paidAmount;
    this.pendingBalance = pendingBalance;
    this.price = price;
    this.remarks = remarks;
    this.products = products;
    this.installments = installments;
  }

  /**
  * Validate fields and instantiate a new Sale with a list of installment objects
  *
  * @param {Number} id The sale ID
  * @param {String} date A string representing a date
  * @param {Number} installmentsQty Quantity of sale installments
  * @param {Number} paidAmount Amount paid for the sale
  * @param {Number} pendingBalance Balance due
  * @param {Number} price Sale price
  * @param {String} remarks Sale's remarks
  * @param {Array} products List of sold products
  * @param {Array} installments List of installment objects
  * @param {Object} paidInstallments List of already paid installments to merge with the content of the "installments" attribute
  */
  static create(id, date, installmentsQty, paidAmount, pendingBalance, price, remarks, products, installments, paidInstallments = {}) {
    if (id == null) {
      throw new ValidationError(this.ID_ERROR);
    }

    // Calculate amount of paidInstallments
    let amountPaidInstallments = 0.0;
    if (paidInstallments) {
      Object.keys(paidInstallments).map(installment => {
        amountPaidInstallments += parseFloat(paidInstallments[installment].amount);
      });
    }

    // Calculate sale paid amount and pending balance
    let calculatedPaidAmount = parseFloat(paidAmount) + amountPaidInstallments;
    let calculatedPendingBalance = parseFloat(pendingBalance) - amountPaidInstallments;

    // Create installments
    let saleInstallments = [];
    installments.installments.map(item => {
      // If the installment is not in paidInstallments, then create the installment instance with
      // the data from item
      if (!(item.installment in paidInstallments)) {
        saleInstallments.push(new Installment(item.pk, item.installment, item.installment_amount, item.paid_amount, item.status));
      } else {
        // If the installment is present in paidInstallments
        // Filter installment without an outstanding balance, and calculate the paid amount and status
        if (item.installment_amount - item.paid_amount - paidInstallments[item.installment].amount !== 0) {
          const calculatedInstallmentPaidAmount = item.paid_amount + paidInstallments[item.installment].amount;
          const calculatedStatus = paidInstallments[item.installment].amount > 0 ? 'PARTIAL' : item.status;
          saleInstallments.push(new Installment(item.pk, item.installment, item.installment_amount, calculatedInstallmentPaidAmount, calculatedStatus));
        }
      }
    });

    return new Sale(id, date, installmentsQty, calculatedPaidAmount, calculatedPendingBalance, price, remarks, products, saleInstallments);
  }

  /**
  * Return an object with pending installments grouped as partial, current and next.
  * Partial = Partially paid
  * Current = The next installment to be paid
  * Next = Remaining unpaid installments
  */
  getBundledInstallments() {
    let partial = [];
    let current = [];
    let next = [];

    this.installments.map(installment => {
      if (installment.status == 'PARTIAL') {
        partial.push(installment);
      } else {
        next.push(installment);
      }
    });

    // Deletes the first element from "next" and push it to "current"
    current.push(next.shift());

    return {
      partial: partial,
      current: current,
      next: next
    }
  }

  /**
  * Returns the amount of installments
  */
  installmentsCount() {
    return this.installments.length;
  }
}


/** @class Represents an Installment */

export class Installment {
  /**
  * Creates an Installment instance
  *
  * @param {Number} id The installment ID
  * @param {Number} installment The installment number for a sale
  * @param {Number} installmentAmount Installment amount
  * @param {Number} paidAmount Amount already paid for the installment
  * @param {String} status Status can be "PAID", "PENDING", "PARTIAL"
  */
  constructor(id, installment, installmentAmount, paidAmount, status) {
    this.id = id;
    this.installment = installment;
    this.installmentAmount = installmentAmount;
    this.paidAmount = paidAmount;
    this.status = status;
  }
}


/** @class Exception to return if a validation fails */

class ValidationError extends Error {
  /**
  * Instantiate a new ValidationError exception
  *
  * @param {String} message The message of the exception
  */
  constructor(message) {
    super(message)
    this.name = 'ValidationError'
  }
}