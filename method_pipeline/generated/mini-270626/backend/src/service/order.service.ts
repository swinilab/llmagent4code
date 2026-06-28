// Order Service Layer

import { Order, OrderData, OrderItem, OrderStatus, CustomerInfo } from '../domain/order/order.entity';
import { MemoryRepository } from '../repository/memory-repository';
import { CustomerService } from './customer.service';
import { ProductService } from './product.service';

export class OrderService {
  private repository: MemoryRepository<OrderData>;
  private customerService: CustomerService;
  private productService: ProductService;

  constructor(customerService: CustomerService, productService: ProductService) {
    this.repository = new MemoryRepository<OrderData>();
    this.customerService = customerService;
    this.productService = productService;
  }

  async createOrder(customerId: string, customerInfo: CustomerInfo, items: OrderItem[], sessionId: string): Promise<Order> {
    const order = new Order({
      customerId,
      customerInfo,
      items,
      sessionId
    });
    order.calculateTotals();
    const saved = await this.repository.create(order.toJSON());
    return new Order(saved);
  }

  async getOrderById(id: string): Promise<Order | null> {
    const data = await this.repository.findById(id);
    return data ? new Order(data) : null;
  }

  async getAllOrders(): Promise<Order[]> {
    const data = await this.repository.findAll();
    return data.map(d => new Order(d));
  }

  async getOrdersByCustomerId(customerId: string): Promise<Order[]> {
    const orders = await this.repository.findAll();
    return orders.filter(o => o.customerId === customerId).map(d => new Order(d));
  }

  async getOrdersBySessionId(sessionId: string): Promise<Order[]> {
    const orders = await this.repository.findAll();
    return orders.filter(o => o.sessionId === sessionId).map(d => new Order(d));
  }

  async updateOrderStatus(orderId: string, status: OrderStatus): Promise<Order | null> {
    const existing = await this.repository.findById(orderId);
    if (!existing) return null;

    const order = new Order(existing);
    order.updateStatus(status);
    const updated = await this.repository.update(orderId, order.toJSON());
    return updated ? new Order(updated) : null;
  }

  async confirmOrder(orderId: string): Promise<Order | null> {
    const existing = await this.repository.findById(orderId);
    if (!existing) return null;

    const order = new Order(existing);
    order.confirm();
    
    // Update stock for each item
    for (const item of order.items) {
      await this.productService.updateStock(item.productId, item.quantity);
    }

    // Add order to customer history
    await this.customerService.addOrderToHistory(order.customerId, order.id);

    const updated = await this.repository.update(orderId, order.toJSON());
    return updated ? new Order(updated) : null;
  }

  async cancelOrder(orderId: string): Promise<Order | null> {
    const existing = await this.repository.findById(orderId);
    if (!existing) return null;

    const order = new Order(existing);
    order.cancel();

    // Restore stock for each item
    for (const item of order.items) {
      await this.productService.addStock(item.productId, item.quantity);
    }

    const updated = await this.repository.update(orderId, order.toJSON());
    return updated ? new Order(updated) : null;
  }

  async deleteOrder(id: string): Promise<boolean> {
    return this.repository.delete(id);
  }

  async updateOrderItems(orderId: string, items: OrderItem[]): Promise<Order | null> {
    const existing = await this.repository.findById(orderId);
    if (!existing) return null;

    const order = new Order(existing);
    order.items = items;
    order.calculateTotals();

    const updated = await this.repository.update(orderId, order.toJSON());
    return updated ? new Order(updated) : null;
  }
}
