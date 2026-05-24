export interface Customer {
  id: string;
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
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateCustomerRequest {
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

export interface UpdateCustomerRequest extends Partial<CreateCustomerRequest> {
  id: string;
}