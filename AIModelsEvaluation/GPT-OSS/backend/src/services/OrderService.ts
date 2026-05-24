import { AppDataSource } from "../db";
import { Order, OrderStatus, OrderItem } from "../domain";
import { Customer } from "../domain";
import { Product } from "../domain";

export class OrderService {
  private orderRepo = AppDataSource.getRepository(Order);
  private orderItemRepo = AppDataSource.getRepository(OrderItem);
  private customerRepo = AppDataSource.getRepository(Customer);
  private productRepo = AppDataSource.getRepository(Product);

  async create(customerId: string, items: { productId: string; quantity: number }[]) {
    const customer = await this.customerRepo.findOneBy({ id: customerId });
    if (!customer) throw new Error("Customer not found");

    let total = 0;
    const orderItems: OrderItem[] = [];

    for (const item of items) {
      const product = await this.productRepo.findOneBy({ id: item.productId });
      if (!product) throw new Error(`Product ${item.productId} not found`);
      const orderItem = this.orderItemRepo.create({
        quantity: item.quantity,
        unitPrice: product.price,
        product,
      });
      total += product.price * item.quantity;
      orderItems.push(orderItem);
    }

    const order = this.orderRepo.create({
      customer,
      items: orderItems,
      totalAmount: total,
      status: OrderStatus.NEW,
    });

    return this.orderRepo.save(order);
  }

  async accept(orderId: string) {
    const order = await this.getById(orderId);
    if (order.status !== OrderStatus.NEW) throw new Error("Only new orders can be accepted");
    order.status = OrderStatus.ACCEPTED;
    return this.orderRepo.save(order);
  }

  async ship(orderId: string) {
    const order = await this.getById(orderId);
    if (order.status !== OrderStatus.ACCEPTED) throw new Error("Only accepted orders can be shipped");
    order.status = OrderStatus.SHIPPED;
    return this.orderRepo.save(order);
  }

  async close(orderId: string) {
    const order = await this.getById(orderId);
    if (order.status !== OrderStatus.SHIPPED) throw new Error("Only shipped orders can be closed");
    order.status = OrderStatus.CLOSED;
    return this.orderRepo.save(order);
  }

  async getAll() {
    return this.orderRepo.find();
  }

  async getById(id: string) {
    const order = await this.orderRepo.findOneBy({ id });
    if (!order) throw new Error(`Order ${id} not found`);
    return order;
  }

  async update(orderId: string, data: Partial<Order>) {
    await this.orderRepo.update(orderId, data);
    return this.getById(orderId);
  }

  async delete(orderId: string) {
    await this.orderRepo.delete(orderId);
    return { message: "Deleted" };
  }
}