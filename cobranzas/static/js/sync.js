//// IMPORTS ////

import { fetchAPI } from "./utils.js";


//// CONSTANTS & HELPERS ////

const URL = `/collections/data/`;


//// DOM ACCESS ////

const syncButton = document.querySelector('.synchronization button');


//// EVENTS ////

syncButton.addEventListener('click', (e) => {
  fetchAPI(URL, 'GET', 'application/json').then((res) => {
    if (res) {
      console.log(res);
    }
  });
});
