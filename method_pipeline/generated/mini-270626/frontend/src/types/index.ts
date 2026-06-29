// Frontend Type Definitions

export interface Customer {
  id: string;
  name: string;
  email: string;
  address: string;
  phone: string;
  bankingDetails: BankingDetails;
  orderHistory: string[];
  role: CustomerRole;
  createdAt: string;
  updatedAt: string;
}

export interface BankingDetails {
  accountNumber: string;
  bankName: string;
  routingNumber: string;
}

export type CustomerRole = 'guest' | 'registered' | 'premium';

export interface Order {
  id: string;
  customerId: string;
  customerInfo: CustomerInfo;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: OrderStatus;
  createdAt: string;
  updatedAt: string;
  invoiceReference: string;
  sessionId: string;
}

export interface CustomerInfo {
  name: string;
  email: string;
  address: string;
  phone: string;
}

export interface OrderItem {
  productId: string;
  productName: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
}

export type OrderStatus = 'pending' | 'confirmed' | 'processing' | 'shipped' | 'delivered' | 'cancelled';

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  createdAt: string;
  updatedAt: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}
