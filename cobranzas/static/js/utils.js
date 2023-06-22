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

export { fetchAPI, getCookie, formatNumber };