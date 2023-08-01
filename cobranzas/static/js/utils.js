const fetchAPI = async (url, method, content_type, headers = {}) => {
  try {
    const response = await fetch(url, {
      method: method,
      headers: {
        "Content-Type": content_type,
        ...headers
      },
    });

    // Parse json response
    const result = await response.json();

    const status_code = response.status;
    if (status_code != 200) {
      console.log("Error in getting brand info!");
      return false;
    }

    return result;
  } catch (error) {
    console.log(error);
    return null;
  }
};

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

const formatNumber = number => {
  return number.toLocaleString("es-AR", { minimumFractionDigits: 2 });
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

export { fetchAPI, getCookie, formatNumber, formatDate };