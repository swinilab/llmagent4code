// API Service Layer

import axios, { AxiosInstance } from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  // Customer API calls
  async createCustomer(data: {
    name: string;
    email: string;
    address: string;
    phone: string;
    bankingDetails: { accountNumber: string; bankName: string; routingNumber: string };
    role?: string;
  }) {
    const response = await this.client.post('/customers', data);
    return response.data;
  }

  async getCustomer(id: string) {
    const response = await this.client.get(`/customers/${id}`);
    return response.data;
  }

  async getAllCustomers() {
    const response = await this.client.get('/customers');
    return response.data;
  }

  async updateCustomer(id: string, data: Partial<any>) {
    const response = await this.client.put(`/customers/${id}`, data);
    return response.data;
  }

  async deleteCustomer(id: string) {
    const response = await this.client.delete(`/customers/${id}`);
    return response.data;
  }

  // Order API calls
  async createOrder(data: {
    customerId: string;
    customerInfo: { name: string; email: string; address: string; phone: string };
    items: { productId: string; productName: string; quantity: number; unitPrice: number }[];
    sessionId: string;
  }) {
    const response = await this.client.post('/orders', data);
    return response.data;
  }

  async getOrder(id: string) {
    const response = await this.client.get(`/orders/${id}`);
    return response.data;
  }

  async getAllOrders() {
    const response = await this.client.get('/orders');
    return response.data;
  }

  async getOrdersByCustomer(customerId: string) {
    const response = await this.client.get(`/orders/customer/${customerId}`);
    return response.data;
  }

  async updateOrderStatus(id: string, status: string) {
    const response = await this.client.put(`/orders/${id}/status`, { status });
    return response.data;
  }

  async confirmOrder(id: string) {
    const response = await this.client.post(`/orders/${id}/confirm`);
    return response.data;
  }

  async cancelOrder(id: string) {
    const response = await this.client.post(`/orders/${id}/cancel`);
    return response.data;
  }

  async deleteOrder(id: string) {
    const response = await this.client.delete(`/orders/${id}`);
    return response.data;
  }

  // Product API calls
  async getAllProducts() {
    const response = await this.client.get('/products');
    return response.data;
  }

  async getProduct(id: string) {
    const response = await this.client.get(`/products/${id}`);
    return response.data;
  }

  async searchProducts(query: string) {
    const response = await this.client.get('/products/search', { params: { query } });
    return response.data;
  }

  async getProductsByCategory(category: string) {
    const response = await this.client.get(`/products/category/${category}`);
    return response.data;
  }

  async createProduct(data: {
    name: string;
    description: string;
    price: number;
    stock: number;
    category: string;
  }) {
    const response = await this.client.post('/products', data);
    return response.data;
  }

  async updateProduct(id: string, data: Partial<any>) {
    const response = await this.client.put(`/products/${id}`, data);
    return response.data;
  }

  async deleteProduct(id: string) {
    const response = await this.client.delete(`/products/${id}`);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
