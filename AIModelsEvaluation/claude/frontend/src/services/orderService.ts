import { api } from './api';
import { Order, CreateOrderRequest, UpdateOrderRequest, ApiResponse } from '../types';

export class OrderService {
  private baseUrl = '/orders';

  async getAllOrders(): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(this.baseUrl);
  }

  async getOrderById(id: string): Promise<ApiResponse<Order>> {
    return api.get<Order>(`${this.baseUrl}/${id}`);
  }

  async getOrdersByCustomerId(customerId: string): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(`${this.baseUrl}/customer/${customerId}`);
  }

  async getOrdersByStatus(status: string): Promise<ApiResponse<Order[]>> {
    return api.get<Order[]>(`${this.baseUrl}/status/${status}`);
  }

  async createOrder(data: CreateOrderRequest): Promise<ApiResponse<Order>> {
    return api.post<Order>(this.baseUrl, data);
  }

  async updateOrder(data: UpdateOrderRequest): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${data.id}`, data);
  }

  async acceptOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/accept`);
  }

  async shipOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/ship`);
  }

  async completeOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/complete`);
  }

  async cancelOrder(id: string): Promise<ApiResponse<Order>> {
    return api.put<Order>(`${this.baseUrl}/${id}/cancel`);
  }

  async deleteOrder(id: string): Promise<ApiResponse<void>> {
    return api.delete<void>(`${this.baseUrl}/${id}`);
  }
}

export const orderService = new OrderService();