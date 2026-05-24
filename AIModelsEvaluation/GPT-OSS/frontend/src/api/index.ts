import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:4000/api",
});

export const CustomerApi = {
  getAll: () => api.get("/customers"),
  get: (id: string) => api.get(`/customers/${id}`),
  create: (data: any) => api.post("/customers", data),
  update: (id: string, data: any) => api.put(`/customers/${id}`, data),
  delete: (id: string) => api.delete(`/customers/${id}`),
};

export const ProductApi = {
  getAll: () => api.get("/products"),
  get: (id: string) => api.get(`/products/${id}`),
  create: (data: any) => api.post("/products", data),
  update: (id: string, data: any) => api.put(`/products/${id}`, data),
  delete: (id: string) => api.delete(`/products/${id}`),
};

export const OrderApi = {
  getAll: () => api.get("/orders"),
  get: (id: string) => api.get(`/orders/${id}`),
  create: (data: any) => api.post("/orders", data),
  accept: (id: string) => api.put(`/orders/${id}/accept`),
  ship: (id: string) => api.put(`/orders/${id}/ship`),
  close: (id: string) => api.put(`/orders/${id}/close`),
  update: (id: string, data: any) => api.put(`/orders/${id}`, data),
  delete: (id: string) => api.delete(`/orders/${id}`),
};

export const InvoiceApi = {
  getAll: () => api.get("/invoices"),
  get: (id: string) => api.get(`/invoices/${id}`),
  createFromOrder: (orderId: string) => api.post(`/invoices/from-order/${orderId}`),
  update: (id: string, data: any) => api.put(`/invoices/${id}`, data),
  delete: (id: string) => api.delete(`/invoices/${id}`),
};

export const PaymentApi = {
  getAll: () => api.get("/payments"),
  get: (id: string) => api.get(`/payments/${id}`),
  make: (data: { invoiceId: string; amount: number; method: string }) =>
    api.post("/payments", data),
  update: (id: string, data: any) => api.put(`/payments/${id}`, data),
  delete: (id: string) => api.delete(`/payments/${id}`),
};