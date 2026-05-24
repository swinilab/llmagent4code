import React from 'react';

const CustomerOverview = ({ customers }) => (
  <div>
    <h2>Customers</h2>
    <ul>
      {customers.map(customer => (
        <li key={customer.id}>{customer.name} - {customer.address}</li>
      ))}
    </ul>
  </div>
);

export default CustomerOverview;