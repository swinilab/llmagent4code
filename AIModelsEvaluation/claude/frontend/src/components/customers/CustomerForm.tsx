import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { Customer, CreateCustomerRequest } from '../../types';
import { customerService } from '../../services/customerService';
import Button from '../common/Button';

interface CustomerFormData {
  name: string;
  email: string;
  phone: string;
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  bankingDetails: {
    accountNumber: string;
    routingNumber: string;
    bankName: string;
  };
  role: 'customer' | 'order_staff' | 'accountant';
}

const CustomerForm: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id?: string }>();
  const isEditing = !!id;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<CustomerFormData>({
    defaultValues: {
      name: '',
      email: '',
      phone: '',
      address: {
        street: '',
        city: '',
        state: '',
        zipCode: '',
        country: 'USA',
      },
      bankingDetails: {
        accountNumber: '',
        routingNumber: '',
        bankName: '',
      },
      role: 'customer',
    },
  });

  useEffect(() => {
    if (isEditing && id) {
      loadCustomer(id);
    }
  }, [isEditing, id]);

  const loadCustomer = async (customerId: string) => {
    try {
      setLoading(true);
      const response = await customerService.getCustomerById(customerId);
      if (response.success && response.data) {
        const customer = response.data;
        setValue('name', customer.name);
        setValue('email', customer.email);
        setValue('phone', customer.phone);
        setValue('address', customer.address);
        setValue('bankingDetails', customer.bankingDetails);
        setValue('role', customer.role);
      } else {
        setError(response.message || 'Failed to load customer');
      }
    } catch (err) {
      setError('An error occurred while loading the customer');
      console.error('Error loading customer:', err);
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (data: CustomerFormData) => {
    try {
      setError(null);
      setSuccess(null);

      let response;
      if (isEditing && id) {
        response = await customerService.updateCustomer({ id, ...data });
      } else {
        response = await customerService.createCustomer(data as CreateCustomerRequest);
      }

      if (response.success) {
        setSuccess(isEditing ? 'Customer updated successfully!' : 'Customer created successfully!');
        setTimeout(() => {
          navigate('/customers');
        }, 1500);
      } else {
        setError(response.message || 'Failed to save customer');
      }
    } catch (err) {
      setError('An error occurred while saving the customer');
      console.error('Error saving customer:', err);
    }
  };

  if (loading && isEditing) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white shadow sm:rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Loading customer...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white shadow sm:rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {/* Header */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900">
              {isEditing ? 'Edit Customer' : 'Create New Customer'}
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              {isEditing
                ? 'Update customer information and settings.'
                : 'Add a new customer to the system.'}
            </p>
          </div>

          {/* Error/Success Messages */}
          {error && (
            <div className="mb-4 bg-error-50 border border-error-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-error-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-error-800">{error}</p>
                </div>
              </div>
            </div>
          )}

          {success && (
            <div className="mb-4 bg-success-50 border border-success-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-success-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-success-800">{success}</p>
                </div>
              </div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Name *
                </label>
                <Controller
                  name="name"
                  control={control}
                  rules={{ required: 'Name is required' }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="text"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter customer name"
                    />
                  )}
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-error-600">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Email *
                </label>
                <Controller
                  name="email"
                  control={control}
                  rules={{
                    required: 'Email is required',
                    pattern: {
                      value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                      message: 'Invalid email address',
                    },
                  }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="email"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter email address"
                    />
                  )}
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-error-600">{errors.email.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Phone *
                </label>
                <Controller
                  name="phone"
                  control={control}
                  rules={{ required: 'Phone is required' }}
                  render={({ field }) => (
                    <input
                      {...field}
                      type="tel"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                      placeholder="Enter phone number"
                    />
                  )}
                />
                {errors.phone && (
                  <p className="mt-1 text-sm text-error-600">{errors.phone.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Role *
                </label>
                <Controller
                  name="role"
                  control={control}
                  render={({ field }) => (
                    <select
                      {...field}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                    >
                      <option value="customer">Customer</option>
                      <option value="order_staff">Order Staff</option>
                      <option value="accountant">Accountant</option>
                    </select>
                  )}
                />
              </div>
            </div>

            {/* Address */}
            <div>
              <h4 className="text-lg font-medium text-gray-900 mb-4">Address Information</h4>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">
                    Street Address *
                  </label>
                  <Controller
                    name="address.street"
                    control={control}
                    rules={{ required: 'Street address is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter street address"
                      />
                    )}
                  />
                  {errors.address?.street && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.street.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    City *
                  </label>
                  <Controller
                    name="address.city"
                    control={control}
                    rules={{ required: 'City is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter city"
                      />
                    )}
                  />
                  {errors.address?.city && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.city.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    State *
                  </label>
                  <Controller
                    name="address.state"
                    control={control}
                    rules={{ required: 'State is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter state"
                      />
                    )}
                  />
                  {errors.address?.state && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.state.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    ZIP Code *
                  </label>
                  <Controller
                    name="address.zipCode"
                    control={control}
                    rules={{ required: 'ZIP code is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter ZIP code"
                      />
                    )}
                  />
                  {errors.address?.zipCode && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.zipCode.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Country *
                  </label>
                  <Controller
                    name="address.country"
                    control={control}
                    rules={{ required: 'Country is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter country"
                      />
                    )}
                  />
                  {errors.address?.country && (
                    <p className="mt-1 text-sm text-error-600">{errors.address.country.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Banking Details */}
            <div>
              <h4 className="text-lg font-medium text-gray-900 mb-4">Banking Information</h4>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Bank Name *
                  </label>
                  <Controller
                    name="bankingDetails.bankName"
                    control={control}
                    rules={{ required: 'Bank name is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter bank name"
                      />
                    )}
                  />
                  {errors.bankingDetails?.bankName && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.bankName.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Account Number *
                  </label>
                  <Controller
                    name="bankingDetails.accountNumber"
                    control={control}
                    rules={{ required: 'Account number is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter account number"
                      />
                    )}
                  />
                  {errors.bankingDetails?.accountNumber && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.accountNumber.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Routing Number *
                  </label>
                  <Controller
                    name="bankingDetails.routingNumber"
                    control={control}
                    rules={{ required: 'Routing number is required' }}
                    render={({ field }) => (
                      <input
                        {...field}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                        placeholder="Enter routing number"
                      />
                    )}
                  />
                  {errors.bankingDetails?.routingNumber && (
                    <p className="mt-1 text-sm text-error-600">{errors.bankingDetails.routingNumber.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate('/customers')}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                loading={isSubmitting}
              >
                {isEditing ? 'Update Customer' : 'Create Customer'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CustomerForm;