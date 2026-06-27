// Customer Form Component

import React, { useState } from 'react';
import { apiService } from '../../services/api';
import { Customer, BankingDetails } from '../../types';

interface CustomerFormProps {
  customer?: Customer | null;
  onSuccess: () => void;
  onCancel: () => void;
}

export function CustomerForm({ customer, onSuccess, onCancel }: CustomerFormProps) {
  const [formData, setFormData] = useState({
    name: customer?.name || '',
    email: customer?.email || '',
    address: customer?.address || '',
    phone: customer?.phone || '',
    accountNumber: customer?.bankingDetails?.accountNumber || '',
    bankName: customer?.bankingDetails?.bankName || '',
    routingNumber: customer?.bankingDetails?.routingNumber || '',
    role: customer?.role || 'guest'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const bankingDetails: BankingDetails = {
        accountNumber: formData.accountNumber,
        bankName: formData.bankName,
        routingNumber: formData.routingNumber
      };

      if (customer) {
        await apiService.updateCustomer(customer.id, {
          name: formData.name,
          email: formData.email,
          address: formData.address,
          phone: formData.phone,
          bankingDetails,
          role: formData.role
        });
      } else {
        await apiService.createCustomer({
          name: formData.name,
          email: formData.email,
          address: formData.address,
          phone: formData.phone,
          bankingDetails,
          role: formData.role
        });
      }
      onSuccess();
    } catch (err) {
      setError('Failed to save customer');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="customer-form">
      <h2>{customer ? 'Edit Customer' : 'New Customer'}</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Name:</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Email:</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Address:</label>
          <input
            type="text"
            name="address"
            value={formData.address}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Phone:</label>
          <input
            type="tel"
            name="phone"
            value={formData.phone}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-group">
          <label>Role:</label>
          <select name="role" value={formData.role} onChange={handleChange}>
            <option value="guest">Guest</option>
            <option value="registered">Registered</option>
            <option value="premium">Premium</option>
          </select>
        </div>
        <h3>Banking Details</h3>
        <div className="form-group">
          <label>Account Number:</label>
          <input
            type="text"
            name="accountNumber"
            value={formData.accountNumber}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label>Bank Name:</label>
          <input
            type="text"
            name="bankName"
            value={formData.bankName}
            onChange={handleChange}
          />
        </div>
        <div className="form-group">
          <label>Routing Number:</label>
          <input
            type="text"
            name="routingNumber"
            value={formData.routingNumber}
            onChange={handleChange}
          />
        </div>
        <div className="form-actions">
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : customer ? 'Update' : 'Create'}
          </button>
          <button type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

export default CustomerForm;
