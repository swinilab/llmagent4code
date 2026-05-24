import { api } from './api';
import { Customer, CreateCustomerRequest, UpdateCustomerRequest, ApiResponse } from '../types';

export class CustomerService {
  private baseUrl = '/customers';

  async getAllCustomers(): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(this.baseUrl);
  }

  async getCustomerById(id: string): Promise<ApiResponse<Customer>> {
    return api.get<Customer>(`${this.baseUrl}/${id}`);
  }

  async getCustomersByRole(role: string): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(`${this.baseUrl}/role/${role}`);
  }

  async createCustomer(data: CreateCustomerRequest): Promise<ApiResponse<Customer>> {
    return api.post<Customer>(this.baseUrl, data);
  }

  async updateCustomer(data: UpdateCustomerRequest): Promise<ApiResponse<Customer>> {
    return api.put<Customer>(`${this.baseUrl}/${data.id}`, data);
  }

  async deleteCustomer(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }

  async searchCustomers(query: string): Promise<ApiResponse<Customer[]>> {
    return api.get<Customer[]>(`${this.baseUrl}/search`, { q: query });
  }
}

export const customerService = new CustomerService();