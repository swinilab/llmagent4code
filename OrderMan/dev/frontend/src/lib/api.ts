import axios from "axios";
import {
  Customer,
  type CustomerFormData,
  Product,
  type ProductFormData,
  Order,
  type OrderFormData,
  Invoice,
  type InvoiceFormData,
  Payment,
  type PaymentFormData,
} from "../types";

const API_BASE_URL = "http://localhost:3000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Customer API
export const customerApi = {
  getAll: () => api.get<Customer[]>("/customers"),
  getById: (id: number) => api.get<Customer>(`/customers/${id}`),
  create: (data: CustomerFormData) => api.post<Customer>("/customers", data),
  update: (id: number, data: Partial<CustomerFormData>) =>
    api.put<Customer>(`/customers/${id}`, data),
  delete: (id: number) => api.delete(`/customers/${id}`),
};

// Product API
export const productApi = {
  getAll: () => api.get<Product[]>("/products"),
  getById: (id: number) => api.get<Product>(`/products/${id}`),
  create: (data: ProductFormData) => api.post<Product>("/products", data),
  update: (id: number, data: Partial<ProductFormData>) =>
    api.put<Product>(`/products/${id}`, data),
  delete: (id: number) => api.delete(`/products/${id}`),
};

// Order API
export const orderApi = {
  getAll: () => api.get<Order[]>("/orders"),
  getById: (id: number) => api.get<Order>(`/orders/${id}`),
  getByCustomer: (customerId: number) =>
    api.get<Order[]>(`/orders/user/${customerId}`),
  create: (data: OrderFormData) => api.post<Order>("/orders", data),
  update: (id: number, data: Partial<OrderFormData>) =>
    api.put<Order>(`/orders/${id}`, data),
  delete: (id: number) => api.delete(`/orders/${id}`),
  receive: (id: number) => api.post<Order>(`/orders/${id}/receive`),
  ship: (id: number) => api.post<Order>(`/orders/${id}/ship`),
  close: (id: number) => api.post<Order>(`/orders/${id}/close`),
};

// Invoice API
export const invoiceApi = {
  getAll: () => api.get<Invoice[]>("/invoices"),
  getById: (id: number) => api.get<Invoice>(`/invoices/${id}`),
  getByOrder: (orderId: number) =>
    api.get<Invoice[]>(`/invoices/order/${orderId}`),
  create: (data: InvoiceFormData) => api.post<Invoice>("/invoices", data),
  update: (id: number, data: Partial<InvoiceFormData>) =>
    api.put<Invoice>(`/invoices/${id}`, data),
  delete: (id: number) => api.delete(`/invoices/${id}`),
  send: (orderId: number) => api.post<Invoice>(`/invoices/send/${orderId}`),
};

// Payment API
export const paymentApi = {
  getAll: () => api.get<Payment[]>("/payments"),
  getById: (id: number) => api.get<Payment>(`/payments/${id}`),
  getByInvoice: (invoiceId: number) =>
    api.get<Payment[]>(`/payments/invoices/${invoiceId}`),
  create: (data: PaymentFormData) => api.post<Payment>("/payments", data),
  update: (id: number, data: Partial<PaymentFormData>) =>
    api.put<Payment>(`/payments/${id}`, data),
  delete: (id: number) => api.delete(`/payments/${id}`),
  accept: (id: number) => api.post(`/payments/accept/${id}`),
};

// Error handling utility
export const handleApiError = (error: any): string => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return "An unexpected error occurred";
};

export default api;
