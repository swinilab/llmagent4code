import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Customer } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';
import Table from '../common/Table';

interface CustomerListProps {
  role?: 'customer' | 'order_staff' | 'accountant';
  searchTerm?: string;
}

const CustomerList: React.FC<CustomerListProps> = ({ role, searchTerm }) => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCustomers();
  }, [role, searchTerm]);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      setError(null);

      let response;
      if (searchTerm) {
        response = await customerService.searchCustomers(searchTerm);
      } else if (role) {
        response = await customerService.getCustomersByRole(role);
      } else {
        response = await customerService.getAllCustomers();
      }

      if (response.success && response.data) {
        setCustomers(response.data);
      } else {
        setError(response.message || 'Failed to load customers');
      }
    } catch (err) {
      setError('An error occurred while loading customers');
      console.error('Error loading customers:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCustomer = async (customerId: string) => {
    if (!confirm('Are you sure you want to delete this customer? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await customerService.deleteCustomer(customerId);
      if (response.success) {
        setCustomers(customers.filter(c => c.id !== customerId));
      } else {
        setError(response.message || 'Failed to delete customer');
      }
    } catch (err) {
      setError('An error occurred while deleting the customer');
      console.error('Error deleting customer:', err);
    }
  };

  const columns = [
    {
      key: 'name' as keyof Customer,
      title: 'Customer',
      render: (value: string, record: Customer) => (
        <div>
          <div className="text-sm font-medium text-gray-900">{value}</div>
          <div className="text-sm text-gray-500">{record.email}</div>
        </div>
      ),
    },
    {
      key: 'phone' as keyof Customer,
      title: 'Phone',
      render: (value: string) => (
        <span className="text-sm text-gray-900">{value}</span>
      ),
    },
    {
      key: 'role' as keyof Customer,
      title: 'Role',
      render: (value: string) => (
        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
          value === 'customer' ? 'bg-blue-100 text-blue-800' :
          value === 'order_staff' ? 'bg-green-100 text-green-800' :
          'bg-purple-100 text-purple-800'
        }`}>
          {value.replace('_', ' ')}
        </span>
      ),
    },
    {
      key: 'address' as keyof Customer,
      title: 'Location',
      render: (value: Customer['address']) => (
        <div className="text-sm text-gray-900">
          <div>{value.city}, {value.state}</div>
          <div className="text-xs text-gray-500">{value.country}</div>
        </div>
      ),
    },
    {
      key: 'bankingDetails' as keyof Customer,
      title: 'Bank',
      render: (value: Customer['bankingDetails']) => (
        <div className="text-sm text-gray-900">
          <div>{value.bankName}</div>
          <div className="text-xs text-gray-500">***{value.accountNumber.slice(-4)}</div>
        </div>
      ),
    },
    {
      key: 'createdAt' as keyof Customer,
      title: 'Created',
      render: (value: string) => (
        <div className="text-sm text-gray-900">
          {new Date(value).toLocaleDateString()}
        </div>
      ),
    },
    {
      key: 'id' as keyof Customer,
      title: 'Actions',
      render: (value: string, record: Customer) => (
        <div className="flex space-x-2">
          <Link to={`/customers/${value}`}>
            <Button size="sm" variant="outline">
              View
            </Button>
          </Link>
          <Link to={`/customers/${value}/edit`}>
            <Button size="sm" variant="secondary">
              Edit
            </Button>
          </Link>
          <Button
            size="sm"
            variant="error"
            onClick={() => handleDeleteCustomer(value)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ];

  const getTitle = () => {
    if (searchTerm) return `Search Results for "${searchTerm}"`;
    if (role) return `${role.replace('_', ' ')} List`;
    return 'All Customers';
  };

  const getDescription = () => {
    if (searchTerm) return `Found ${customers.length} customer(s) matching your search.`;
    if (role) return `Showing all users with ${role.replace('_', ' ')} role.`;
    return `Total of ${customers.length} customers in the system.`;
  };

  if (error) {
    return (
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <div className="text-center">
            <div className="text-error-500 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.729-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Customers</h3>
            <p className="text-sm text-gray-500 mb-4">{error}</p>
            <Button onClick={loadCustomers} variant="primary">
              Try Again
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{getTitle()}</h2>
          <p className="mt-1 text-sm text-gray-600">{getDescription()}</p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link to="/customers/new">
            <Button variant="primary">
              Add Customer
            </Button>
          </Link>
        </div>
      </div>

      {/* Customer List */}
      <Table
        data={customers}
        columns={columns}
        loading={loading}
        emptyMessage={
          searchTerm
            ? `No customers found matching "${searchTerm}".`
            : role
            ? `No customers found with ${role.replace('_', ' ')} role.`
            : 'No customers found. Add your first customer to get started.'
        }
      />
    </div>
  );
};

export default CustomerList;