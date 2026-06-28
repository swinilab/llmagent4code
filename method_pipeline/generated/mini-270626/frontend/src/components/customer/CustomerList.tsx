// Customer List Component

import React from 'react';
import { Customer } from '../../types';

interface CustomerListProps {
  customers: Customer[];
  onSelectCustomer: (customer: Customer) => void;
  onDeleteCustomer: (id: string) => void;
}

export function CustomerList({ customers, onSelectCustomer, onDeleteCustomer }: CustomerListProps) {
  return (
    <div className="customer-list">
      <h2>Customer List</h2>
      {customers.length === 0 ? (
        <p>No customers found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Role</th>
              <th>Orders</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {customers.map(customer => (
              <tr key={customer.id}>
                <td>{customer.name}</td>
                <td>{customer.email}</td>
                <td>{customer.phone}</td>
                <td>{customer.role}</td>
                <td>{customer.orderHistory.length}</td>
                <td>
                  <button onClick={() => onSelectCustomer(customer)}>View</button>
                  <button onClick={() => onDeleteCustomer(customer.id)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default CustomerList;
