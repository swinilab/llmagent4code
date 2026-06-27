// Shared Domain Types for Order Processing System

export interface Customer {
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

export interface Order {
  id: string;
  customerId: string;
  customerInfo: CustomerInfo;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  total: number;
  status: OrderStatus;
  createdAt: Date;
  updatedAt: Date;
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
  createdAt: Date;
  updatedAt: Date;
}

export interface CreateCustomerRequest {
  name: string;
  email: string;
  address: string;
  phone: string;
  bankingDetails: BankingDetails;
}

export interface CreateOrderRequest {
  customerId: string;
  items: OrderItemRequest[];
  sessionId: string;
}

export interface OrderItemRequest {
  productId: string;
  quantity: number;
}

export interface CreateProductRequest {
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
}

export interface UpdateProductRequest {
  name?: string;
  description?: string;
  price?: number;
  stock?: number;
  category?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
