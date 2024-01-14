const getCookie = name => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const formatNumber = (number, decimals = 0) => {
  return number.toLocaleString("es-AR", { minimumFractionDigits: decimals });
}

const formatDate = date => {
  const dayNames = ['Dom', 'Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab'];
  const dayName = dayNames[date.getDay()];
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = String(date.getFullYear());
  const hour = String(date.getHours());
  const minute = String(date.getMinutes()).padStart(2, '0');
  return dayName + " " + day + "/" + month + "/" + year + " " + hour + ":" + minute;
}

const appendAlert = (root, message, type) => {
  const wrapper = document.createElement('div');
  wrapper.innerHTML = [
    `<div class="alert alert-${type} alert-dismissible" role="alert">`,
    `   <div>${message}</div>`,
    '   <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>',
    '</div>'
  ].join('');

  root.append(wrapper);
}

// Util function to clear selection of a dselect element
const clearDselectSelection = el => {
  dselectClear(el.nextElementSibling.querySelector('button'), 'dselect-wrapper');
}

export { getCookie, formatNumber, formatDate, appendAlert, clearDselectSelection };