// Import domain models
export { default as Customer } from "../../../modules/customer/Customer";
export { default as Product } from "../../../modules/product/Product";
export { Order } from "../../../modules/order/Order";
export type { OrderItem, OrderData } from "../../../modules/order/Order";
export { Invoice } from "../../../modules/invoice/Invoice";
export type { InvoiceData } from "../../../modules/invoice/Invoice";
export { Payment } from "../../../modules/payment/Payment";
export type { PaymentData } from "../../../modules/payment/Payment";

// Additional form data types for creating new entities
export interface CustomerFormData {
  name: string;
  address: string;
  phone: string;
  bankAccount?: string;
}

export interface ProductFormData {
  name: string;
  description: string;
  price: number;
  image: string;
}

export interface OrderFormData {
  customerId: number;
  method: "bank" | "card" | "cash";
  items: Array<{
    productId?: number;
    name: string;
    quantity: number;
    price: number;
  }>;
}

export interface InvoiceFormData {
  orderId: number;
  amount: number;
  method: "bank" | "card" | "cash";
}

export interface PaymentFormData {
  invoiceId: number;
  amount: number;
  method: "bank" | "card" | "cash";
}

// Auth Types
export interface User {
  id: number;
  name: string;
  role: "customer" | "staff" | "accountant";
  email?: string;
}

// API Response Types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

// Common Types
export type PaymentMethod = "bank" | "card" | "cash";
export type OrderStatus =
  | "pending"
  | "accepted"
  | "paid"
  | "shipped"
  | "closed";
export type InvoiceStatus = "pending" | "issued" | "paid";
export type PaymentStatus = "pending" | "completed" | "failed";
export type UserRole = "customer" | "staff" | "accountant";
