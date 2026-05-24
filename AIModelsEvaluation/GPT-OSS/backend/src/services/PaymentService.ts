import { AppDataSource } from "../db";
import { Payment, PaymentMethod, PaymentStatus } from "../domain";
import { Invoice } from "../domain";

export class PaymentService {
  private repo = AppDataSource.getRepository(Payment);
  private invoiceRepo = AppDataSource.getRepository(Invoice);

  async makePayment(invoiceId: string, amount: number, method: PaymentMethod) {
    const invoice = await this.invoiceRepo.findOneBy({ id: invoiceId });
    if (!invoice) throw new Error(`Invoice ${invoiceId} not found`);

    const payment = this.repo.create({
      invoice,
      amount,
      method,
      status: PaymentStatus.COMPLETED,
    });

    const saved = await this.repo.save(payment);

    // Update invoice status if fully paid
    const totalPaid = await this.repo
      .createQueryBuilder("payment")
      .where("payment.invoiceId = :id", { id: invoiceId })
      .andWhere("payment.status = :status", { status: PaymentStatus.COMPLETED })
      .select("SUM(payment.amount)", "sum")
      .getRawOne();

    const paidAmount = parseFloat(totalPaid?.sum ?? "0");
    if (paidAmount >= invoice.amount) {
      invoice.status = InvoiceStatus.PAID;
      await this.invoiceRepo.save(invoice);
    }

    return saved;
  }

  async getAll() {
    return this.repo.find();
  }

  async getById(id: string) {
    const pay = await this.repo.findOneBy({ id });
    if (!pay) throw new Error(`Payment ${id} not found`);
    return pay;
  }

  async update(id: string, data: Partial<Payment>) {
    await this.repo.update(id, data);
    return this.getById(id);
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { message: "Deleted" };
  }
}