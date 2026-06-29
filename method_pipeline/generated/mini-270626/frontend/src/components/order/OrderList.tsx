// Order List Component

import React from 'react';
import { Order } from '../../types';

interface OrderListProps {
  orders: Order[];
  onSelectOrder: (order: Order) => void;
  onConfirmOrder: (id: string) => void;
  onCancelOrder: (id: string) => void;
}

export function OrderList({ orders, onSelectOrder, onConfirmOrder, onCancelOrder }: OrderListProps) {
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: '#ffc107',
      confirmed: '#28a745',
      processing: '#17a2b8',
      shipped: '#007bff',
      delivered: '#28a745',
      cancelled: '#dc3545'
    };
    return colors[status] || '#6c757d';
  };

  return (
    <div className="order-list">
      <h2>Order List</h2>
      {orders.length === 0 ? (
        <p>No orders found</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Order ID</th>
              <th>Customer</th>
              <th>Total</th>
              <th>Status</th>
              <th>Invoice</th>
              <th>Items</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {orders.map(order => (
              <tr key={order.id}>
                <td>{order.id.substring(0, 8)}...</td>
                <td>{order.customerInfo.name}</td>
                <td>${order.total.toFixed(2)}</td>
                <td>
                  <span style={{ backgroundColor: getStatusColor(order.status), padding: '2px 8px', borderRadius: '4px', color: 'white' }}>
                    {order.status}
                  </span>
                </td>
                <td>{order.invoiceReference || 'N/A'}</td>
                <td>{order.items.length}</td>
                <td>
                  <button onClick={() => onSelectOrder(order)}>View</button>
                  {order.status === 'pending' && (
                    <>
                      <button onClick={() => onConfirmOrder(order.id)}>Confirm</button>
                      <button onClick={() => onCancelOrder(order.id)}>Cancel</button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default OrderList;
