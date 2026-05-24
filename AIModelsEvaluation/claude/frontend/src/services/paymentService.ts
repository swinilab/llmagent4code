import { api } from './api';
import { Payment, CreatePaymentRequest, UpdatePaymentRequest, ApiResponse } from '../types';

export class PaymentService {
  private baseUrl = '/payments';

  async getAllPayments(): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(this.baseUrl);
  }

  async getPaymentById(id: string): Promise<ApiResponse<Payment>> {
    return api.get<Payment>(`${this.baseUrl}/${id}`);
  }

  async getPaymentsByCustomerId(customerId: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getPaymentsByInvoiceId(invoiceId: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/invoice/${invoiceId}`);
  }

  async getPaymentsByStatus(status: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/status/${status}`);
  }

  async getPaymentsByDateRange(startDate: string, endDate: string): Promise<ApiResponse<Payment[]>> {
    return api.get<Payment[]>(`${this.baseUrl}/date-range`, { startDate, endDate });
  }

  async getPaymentSummary(customerId?: string): Promise<ApiResponse<any>> {
    return api.get<any>(`${this.baseUrl}/summary`, customerId ? { customerId } : undefined);
  }

  async createPayment(data: CreatePaymentRequest): Promise<ApiResponse<Payment>> {
    return api.post<Payment>(this.baseUrl, data);
  }

  async updatePayment(data: UpdatePaymentRequest): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${data.id}`, data);
  }

  async processPayment(id: string): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${id}/process`);
  }

  async cancelPayment(id: string): Promise<ApiResponse<Payment>> {
    return api.put<Payment>(`${this.baseUrl}/${id}/cancel`);
  }

  async deletePayment(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const paymentService = new PaymentService();