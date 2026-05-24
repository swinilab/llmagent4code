import React, { useState, useEffect } from 'react';

function App() {
  const [customers, setCustomers] = useState([]);

  useEffect(() => {
    // Fetch customers from backend API
    fetch('/customers')
      .then(response => response.json())
      .then(data => setCustomers(data));
  }, []);

  return (
    <div>
      <h1>Order Management System</h1>
      <h2>Customers</h2>
      <ul>
        {customers.map(customer => (
          <li key={customer.customer_id}>
            {customer.name} - {customer.role}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;