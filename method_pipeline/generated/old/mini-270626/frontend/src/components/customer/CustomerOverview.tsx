// Customer Overview Component

import React, { useEffect, useState } from 'react';
import { useApp } from '../../context/AppContext';
import { apiService } from '../../services/api';
import { Customer } from '../../types';

export function CustomerOverview() {
  const { setCustomers, setCurrentCustomer, sessionId } = useApp();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadCustomers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiService.getAllCustomers();
      if (response.success) {
        setCustomers(response.data || []);
      }
    } catch (err) {
      setError('Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, []);

  return (
    <div className="customer-overview">
      <h1>Customer Management</h1>
      <p>Session ID: {sessionId}</p>
      
      {loading && <p>Loading customers...</p>}
      {error && <p className="error">{error}</p>}
      
      <div className="overview-actions">
        <button onClick={loadCustomers}>Refresh Customers</button>
      </div>
    </div>
  );
}

export default CustomerOverview;
