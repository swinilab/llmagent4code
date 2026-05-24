import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Customer } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';
import Table from '../common/Table';

const CustomerOverview: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      setLoading(true);
      const response = await customerService.getAllCustomers();
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

  const columns = [
    {
      key: 'name' as keyof Customer,
      title: 'Name',
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
      title: 'Address',
      render: (value: Customer['address']) => (
        <div className="text-sm text-gray-900">
          {value.city}, {value.state}
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
  ];

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
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage customer information and view customer details.
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link to="/customers/new">
            <Button variant="primary">
              Add New Customer
            </Button>
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">👥</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Total Customers
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'customer').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">👨‍💼</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Order Staff
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'order_staff').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl">📊</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    Accountants
                  </dt>
                  <dd className="text-lg font-medium text-gray-900">
                    {customers.filter(c => c.role === 'accountant').length}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Customer Table */}
      <Table
        data={customers}
        columns={columns}
        loading={loading}
        emptyMessage="No customers found. Add your first customer to get started."
        onRowClick={(customer) => {
          // Navigate to customer details
          window.location.href = `/customers/${customer.id}`;
        }}
      />
    </div>
  );
};

export default CustomerOverview;