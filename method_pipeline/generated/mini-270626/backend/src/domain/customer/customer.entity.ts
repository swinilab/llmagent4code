// Customer Entity Implementation

import { v4 as uuidv4 } from 'uuid';

export type CustomerRole = 'guest' | 'registered' | 'premium';

export interface BankingDetails {
  accountNumber: string;
  bankName: string;
  routingNumber: string;
}

export interface CustomerData {
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

export class Customer {
  public readonly id: string;
  public name: string;
  public email: string;
  public address: string;
  public phone: string;
  public bankingDetails: BankingDetails;
  public orderHistory: string[];
  public role: CustomerRole;
  public readonly createdAt: Date;
  public updatedAt: Date;

  constructor(data: Partial<CustomerData>) {
    this.id = data.id || uuidv4();
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
    if (!this.orderHistory.includes(orderId)) {
      this.orderHistory.push(orderId);
      this.updatedAt = new Date();
    }
  }

  updateRole(role: CustomerRole): void {
    this.role = role;
    this.updatedAt = new Date();
  }

  updateInfo(name: string, email: string, address: string, phone: string): void {
    this.name = name;
    this.email = email;
    this.address = address;
    this.phone = phone;
    this.updatedAt = new Date();
  }

  updateBankingDetails(details: BankingDetails): void {
    this.bankingDetails = details;
    this.updatedAt = new Date();
  }

  toJSON(): CustomerData {
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

  static fromJSON(data: CustomerData): Customer {
    return new Customer(data);
  }
}
