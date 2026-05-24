// Order service

import { Order } from '../entities/order.entity';

class OrderService {
  private orders: Order[] = [];

  async getOrders(): Promise<Order[]> {
    return this.orders;
  }

  async createOrder(order: Order): Promise<Order> {
    this.orders.push(order);
    return order;
  }

  async updateOrder(id: number, order: Order): Promise<Order> {
    const index = this.orders.findIndex((o) => o.id === id);
    if (index !== -1) {
      this.orders[index] = order;
    }
    return order;
  }

  async deleteOrder(id: number): Promise<void> {
    this.orders = this.orders.filter((o) => o.id !== id);
  }
}

export { OrderService };