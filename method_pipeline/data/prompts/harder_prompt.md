## Level 3: Hard (React with README)
**Theme:** Personal Finance Tracker (Expense Manager)  
**Goal:** Test React fundamentals (hooks, components, props) along with project documentation and standard installation workflows.

### Prompt
> "Create a Personal Finance Tracker web application using **React (functional components and Hooks)** and standard project structure. The app must allow users to add income and expense transactions (with a Description, Amount, and Category dropdown). Display a dynamic summary at the top showing Total Balance, Total Income, and Total Expenses. Users must be able to delete individual transactions from the list. All transaction data must persist using a custom hook that syncs with `localStorage`. 

**Required Project Structure:**
```
/src
   /components
     Header.jsx
     Balance.jsx
     AddTransaction.jsx
     TransactionList.jsx
   /hooks
     useLocalStorage.js
   /utils
     helpers.js  (For formatting currency/date)
   App.jsx
   index.js
```
**Crucially:** You must include a **`README.md`** file at the root of the project. This file must contain explicit step-by-step instructions for installing and running the app locally (including `npm install` and `npm start` commands), a brief project overview, and a note about the tech stack used. Assume the project uses Vite or Create React App. Style the application with a financial dashboard theme (using green for income and red for expenses)."
