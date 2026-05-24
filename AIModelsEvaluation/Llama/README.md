### Setup Instructions

1.  Install Node.js and npm.
2.  Create a new project directory and navigate to it.
3.  Run `npm init` to create a `package.json` file.
4.  Install required dependencies: `npm install express typescript axios`.
5.  Create a new file `server.ts` and copy the server code into it.
6.  Create a new file `index.html` and copy the HTML code into it.
7.  Create a new file `App.tsx` and copy the React code into it.
8.  Run `npx tsc` to compile the TypeScript code.
9.  Run `node server.ts` to start the server.
10. Open a web browser and navigate to `http://localhost:3000`.

### Example Use Cases

*   Create a new customer: Send a POST request to `http://localhost:3000/api/customers` with the customer data in the request body.
*   Get all customers: Send a GET request to `http://localhost:3000/api/customers`.
*   Update a customer: Send a PUT request to `http://localhost:3000/api/customers/{id}` with the updated customer data in the request body.
*   Delete a customer: Send a DELETE request to `http://localhost:3000/api/customers/{id}`.
