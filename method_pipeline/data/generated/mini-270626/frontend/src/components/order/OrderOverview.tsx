// Order Overview Component

import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { apiService } from '../../services/api';
import { Order } from '../../types';

export function OrderOverview() {
  const { setOrders, sessionId } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getAllOrders();
      if (response.success) {
        setOrders(response.data || []);
      }
    } catch (err) {
      setError('Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  return (
    <div className="order-overview">
      <h1>Order Management</h1>
      <p>Session ID: {sessionId}</p>
      
      {loading && <p>Loading orders...</p>}
      {error && <p className="error">{error}</p>}
      
      <div className="overview-actions">
        <button onClick={loadOrders}>Refresh Orders</button>
      </div>
    </div>
  );
}

export default OrderOverview;
