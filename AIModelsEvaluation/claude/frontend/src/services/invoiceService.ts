import { api } from './api';
import { Invoice, CreateInvoiceRequest, UpdateInvoiceRequest, ApiResponse } from '../types';

export class InvoiceService {
  private baseUrl = '/invoices';

  async getAllInvoices(): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(this.baseUrl);
  }

  async getInvoiceById(id: string): Promise<ApiResponse<Invoice>> {
    return api.get<Invoice>(`${this.baseUrl}/${id}`);
  }

  async getInvoicesByCustomerId(customerId: string): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getInvoicesByStatus(status: string): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/status/${status}`);
  }

  async getInvoiceByOrderId(orderId: string): Promise<ApiResponse<Invoice>> {
    return api.get<Invoice>(`${this.baseUrl}/order/${orderId}`);
  }

  async getOverdueInvoices(): Promise<ApiResponse<Invoice[]>> {
    return api.get<Invoice[]>(`${this.baseUrl}/overdue`);
  }

  async createInvoice(data: CreateInvoiceRequest): Promise<ApiResponse<Invoice>> {
    return api.post<Invoice>(this.baseUrl, data);
  }

  async updateInvoice(data: UpdateInvoiceRequest): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${data.id}`, data);
  }

  async markInvoiceAsPaid(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/pay`);
  }

  async sendInvoice(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/send`);
  }

  async cancelInvoice(id: string): Promise<ApiResponse<Invoice>> {
    return api.put<Invoice>(`${this.baseUrl}/${id}/cancel`);
  }

  async deleteInvoice(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const invoiceService = new InvoiceService();