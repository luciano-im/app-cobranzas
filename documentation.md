# Documentation

### How the app works when it's offline
There's a button to sync the app woth the server. This button has two functions:
1. Importing the data from the server to update the local database.
2. Sending the pending collections to the server.

When the device lost connection with the server, the sync button hides and a message appears to indicate that there's no internet connection (or at least the server couldn't be reached).

#### App is Online
If the app is online, each request is made agains the server. Offline features and content aren't used, unless files already cached by the ServiceWorker.

#### App is Offline
The app displays the data stored in indexedDB. Requests are processed and:
1. If it's a GET request:
  a. If the page is cached, the app respond with the cached page.
  b. If the page is not cached, the app respond with the offline page.
2. If it's a POST request:
  a. Convert request to a BLOB object and store it to indexedDB.
  b. Shows a badge to indicate the user that there requests pending to send to the server.

Once the internet connection is available again, the sync button appears and the user can press it to send the pending POST requests to the server. 
To prevent POST requests failed, it is neccessary to send a header with the CSRF token, and the blob object stored in the database must be sent as 'form-urlencoded' content:
1. Get the Django CSRF token.
2. Get the pending requests stored in indexedDB.
3. From each blob object, creates a new Response() object.
4. Then the Response is used to create a new URLSearchParams object.
5. Then update 'csrfmiddlewaretoken' attribute with the CSRF token.
6. Send the fetch request with the 'X-CSRFToken' header.