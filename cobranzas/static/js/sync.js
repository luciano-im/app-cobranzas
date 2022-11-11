//// IMPORTS ////

import { fetchAPI } from "./utils.js";


//// CONSTANTS & HELPERS ////

const URL = `/collections/data/`;


//// DOM ACCESS ////

const syncButton = document.querySelector('.synchronization button');
const syncDate = document.querySelector('.synchronization .sync-date');
const syncLastUpdate = document.querySelector('.synchronization .last-sync');
const syncNotSupported = document.querySelector('.synchronization .idxdb-support');


//// EVENTS ////

syncButton.addEventListener('click', (e) => {
  // Check for indexedDB support
  if (!('indexedDB' in window)) {
    console.log("This browser doesn't support IndexedDB");
    syncNotSupported.classList.add('show');
    return;
  } else {
    syncDate.classList.add('show');
  }

  fetchAPI(URL, 'GET', 'application/json').then((res) => {
    if (res) {
      console.log(res);
    }
  });
});
