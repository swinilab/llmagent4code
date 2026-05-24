import { AppDataSource } from "../db";
import { Invoice, InvoiceStatus, Order } from "../domain";

export class InvoiceService {
  private repo = AppDataSource.getRepository(Invoice);

  async create(order: Order) {
    const invoice = this.repo.create({
      order,
      amount: order.totalAmount,
      billingAddress: order.customer.address,
      status: InvoiceStatus.ISSUED,
    });
    const saved = await this.repo.save(invoice);
    // Link invoice to order
    order.invoiceId = saved.id;
    await AppDataSource.getRepository(Order).save(order);
    return saved;
  }

  async getAll() {
    return this.repo.find();
  }

  async getById(id: string) {
    const inv = await this.repo.findOneBy({ id });
    if (!inv) throw new Error(`Invoice ${id} not found`);
    return inv;
  }

  async update(id: string, data: Partial<Invoice>) {
    await this.repo.update(id, data);
    return this.getById(id);
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { message: "Deleted" };
  }
}