// Customer Domain Model

export class Customer {
  id: string;
  name: string;
  email: string;
  address: string;
  phone: string;
  bankingDetails: BankingDetails;
  orderHistory: string[];
  role: CustomerRole;
  createdAt: Date;
  updatedAt: Date;

  constructor(data: Partial<Customer>) {
    this.id = data.id || '';
    this.name = data.name || '';
    this.email = data.email || '';
    this.address = data.address || '';
    this.phone = data.phone || '';
    this.bankingDetails = data.bankingDetails || { accountNumber: '', bankName: '', routingNumber: '' };
    this.orderHistory = data.orderHistory || [];
    this.role = data.role || 'guest';
    this.createdAt = data.createdAt || new Date();
    this.updatedAt = data.updatedAt || new Date();
  }

  addOrder(orderId: string): void {
    this.orderHistory.push(orderId);
    this.updatedAt = new Date();
  }

  updateRole(role: CustomerRole): void {
    this.role = role;
    this.updatedAt = new Date();
  }

  toJSON(): CustomerDTO {
    return {
      id: this.id,
      name: this.name,
      email: this.email,
      address: this.address,
      phone: this.phone,
      bankingDetails: this.bankingDetails,
      orderHistory: this.orderHistory,
      role: this.role,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt
    };
  }
}

export interface CustomerDTO {
  id: string;
  name: string;
  email: string;
  address: string;
  phone: string;
  bankingDetails: BankingDetails;
  orderHistory: string[];
  role: CustomerRole;
  createdAt: Date;
  updatedAt: Date;
}

export interface BankingDetails {
  accountNumber: string;
  bankName: string;
  routingNumber: string;
}

export type CustomerRole = 'guest' | 'registered' | 'premium';
