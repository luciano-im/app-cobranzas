//// CONSTANTS & HELPERS ////

// Formset name
const FORMSET_NAME = "saleproduct_set";
// Regex to update form index
const formRegex = RegExp(`${FORMSET_NAME}-(\\d){1}-`, "g");


//// DOM ACCESS ////

// Container
const productFormsContainer = document.querySelector(".product-forms");
// Button to add a new product form
const addFormButton = document.querySelector(".add-form-row");
// Form to be cloned
const emptyForm = document.querySelector("#empty_form .form-row");
// Total forms number
const totalFormsInput = document.querySelector(`#id_${FORMSET_NAME}-TOTAL_FORMS`);
// Total price input
const priceInput = document.getElementById("id_price");
// Installments input
const installmentsInput = document.getElementById("id_installments");
// Installment amount input
const installmentAmountInput = document.getElementById("id_installment_amount");
// Payment detail rows
const paymentSchemeRow1 = document.getElementById("payment-scheme-row-1");
const paymentSchemeRow2 = document.getElementById("payment-scheme-row-2");
// Input fields for product price
let productPriceInputs = productFormsContainer.querySelectorAll('input[id$="price"]');


//// FUNCTIONS ////

// Manage the form deletion process
function removeForm(e) {
  e.preventDefault();

  // Get the form index and remove the form
  const indexFormToDelete = getDataFormIndex(e.target);
  const form = document.querySelector(
    `.form-row[data-form-index="${indexFormToDelete}"]`
  );
  form.remove();

  // Update total form input value
  const formIndex = document.querySelectorAll(".form-row").length - 1;
  totalFormsInput.value = formIndex;

  // Update forms index value. Django validate that the forms in the post request have a subsequent value
  // starting from 0, eg: saleproduct_set-0, saleproduct_set-1, saleproduct_set-2, etc.
  const formRow = productFormsContainer.querySelectorAll(".form-row");
  for (var i = 1; i < formRow.length; i++) {
    // Get every element which has an id, name or for attribute that includes the formset name
    const elementsToUpdateIndex = formRow[i].querySelectorAll(
      `[id*="${FORMSET_NAME}"], [name*="${FORMSET_NAME}"], [for*="${FORMSET_NAME}"]`
    );
    // Update index and data attribute
    updateFormElementsIndex(elementsToUpdateIndex, i);
    formRow[i].dataset.formIndex = i;
    // Update remove button form index attribute or delete will not work anymore
    const removeButton = formRow[i].querySelector("button");
    removeButton.dataset.formIndex = i;
    // Attach the click event listener again because after updating formRow[i].innerHTML, the DOM recreates
    // the node and the event is lost.
    removeButton.addEventListener("click", removeForm);
  }

  // Update total input value
  updateTotalPrice();
}

// Update the value of total price input
function updateTotalPrice() {
  productPriceInputs =
    productFormsContainer.querySelectorAll('input[id$="price"]');
  // Convert a NodeList to an array with Array.from so I can use map()
  // Create an array of input values and sum each value to get the total
  let prices = Array.from(productPriceInputs).map((el) => {
    return el.value ? parseFloat(el.value) : 0.0;
  });
  const total = prices.reduce((total, next) => total + next);

  priceInput.value = total;
  // Delete any payment calculation
  blankPaymentSchemeCalculation();
}

// Return the data-form-index attribute value from the first parent which has that attribute setted.
function getDataFormIndex(target) {
  if (target.dataset.formIndex) {
    return target.dataset.formIndex;
  }
  return getDataFormIndex(target.parentElement);
}

// Loop over the elements array and replace the form index in the necessary attributes
function updateFormElementsIndex(elements, index) {
  elements.forEach((element) => {
    // Get a list of element attributes
    const attributes = Array.from(element.attributes);
    attributes.forEach((attr) => {
      // Attribute name
      const name = attr.name;
      // Attribute value
      const value = String(attr.value);
      // If attribute value includes formset name, then replace index
      if (value.includes(FORMSET_NAME)) {
        element.setAttribute(
          name,
          value.replace(formRegex, `${FORMSET_NAME}-${index}-`)
        );
      }
    });
  });
}

// Delete payment scheme calculations
function blankPaymentSchemeCalculation() {
  // Empty installments and installment amount input values
  installmentsInput.value = "";
  installmentAmountInput.value = "";
  // Hide payment scheme rows
  togglePaymentSchemeRow(paymentSchemeRow1, "hidden");
  togglePaymentSchemeRow(paymentSchemeRow2, "hidden");
}

// Helper function to show or hide the rows of payment details section
function togglePaymentSchemeRow(row, action) {
  const th = row.querySelector("th");
  const td = row.querySelectorAll("td");
  if (action == "hidden") {
    th.style.visibility = "hidden";
    td[0].style.visibility = "hidden";
    td[1].style.visibility = "hidden";
  } else if (action == "visible") {
    th.style.visibility = "visible";
    td[0].style.visibility = "visible";
    td[1].style.visibility = "visible";
  }
}

// Update content of payment details section
function updatePaymentSchemeRow(row, installments, installmentAmount) {
  const th = row.querySelector("th");
  const td = row.querySelectorAll("td");
  th.innerText = installments;
  td[1].innerText = installmentAmount.toLocaleString("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}


//// EVENTS ////

// Attach change event listener to "extra" forms that come with the formset
productPriceInputs.forEach((input) => {
  input.addEventListener("change", updateTotalPrice);
});

// Manage the form add process
addFormButton.addEventListener("click", (e) => {
  e.preventDefault();

  // Clone the empty form and update its index
  const newForm = emptyForm.cloneNode(true);
  // Forms are zero-based index
  const formIndex = document.querySelectorAll(".form-row").length - 1;
  newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, formIndex);
  newForm.dataset.formIndex = formIndex;

  // Update total form input value
  totalFormsInput.value = formIndex + 1;

  // Update the index of the form to remove, and attach the click event listener to the remove button
  const removeFormButton = newForm.querySelector(".remove-form-row");
  removeFormButton.dataset.formIndex = formIndex;
  removeFormButton.addEventListener("click", removeForm);

  // Attach the change event listener to the price input field
  const unitPriceInput = newForm.querySelector('input[id$="price"]');
  unitPriceInput.addEventListener("change", updateTotalPrice);

  // Insert the form in the DOM
  productFormsContainer.appendChild(newForm);
});

// Update payment scheme on installments input value change
installmentsInput.addEventListener("change", (e) => {
  const price = parseFloat(priceInput.value);
  const installments = parseInt(installmentsInput.value);
  const installmentAmount = price / installments;
  // Update installment amount value
  installmentAmountInput.value = installmentAmount.toFixed(2);

  //Update payment scheme row 1, and hide row 2
  updatePaymentSchemeRow(paymentSchemeRow1, installments, installmentAmount);
  togglePaymentSchemeRow(paymentSchemeRow1, "visible");
  togglePaymentSchemeRow(paymentSchemeRow2, "hidden");
});

// Update payment scheme on installemnt amount input value change
installmentAmountInput.addEventListener("change", (e) => {
  const price = parseFloat(priceInput.value);
  const installmentAmount = parseFloat(installmentAmountInput.value);
  const installments = price / installmentAmount;

  // Show payment scheme row 1
  togglePaymentSchemeRow(paymentSchemeRow1, "visible");
  if (Number.isInteger(installments)) {
    // If installments is integer, update payment scheme row 1 and hide row 2
    installmentsInput.value = installments;
    updatePaymentSchemeRow(paymentSchemeRow1, installments, installmentAmount);
    togglePaymentSchemeRow(paymentSchemeRow2, "hidden");
  } else {
    // If installments is not integer calculate the amount of the last installment
    rest = installments - Math.trunc(installments);
    newQuantity = Math.trunc(installments);
    if (rest <= 0.6) {
      newQuantity--;
    }
    installmentsInput.value = newQuantity + 1;
    lastInstallmentAmount = price - newQuantity * installmentAmount;
    // Update payment scheme rows 1 and 2, and show row 2
    updatePaymentSchemeRow(paymentSchemeRow1, newQuantity, installmentAmount);
    updatePaymentSchemeRow(paymentSchemeRow2, 1, lastInstallmentAmount);
    togglePaymentSchemeRow(paymentSchemeRow2, "visible");
  }
});
