import { AppDataSource } from "../db";
import { Customer } from "../domain";

export class CustomerService {
  private repo = AppDataSource.getRepository(Customer);

  async getAll() {
    return this.repo.find();
  }

  async getById(id: string) {
    const cust = await this.repo.findOneBy({ id });
    if (!cust) throw new Error(`Customer ${id} not found`);
    return cust;
  }

  async create(data: Partial<Customer>) {
    const cust = this.repo.create(data);
    return this.repo.save(cust);
  }

  async update(id: string, data: Partial<Customer>) {
    await this.repo.update(id, data);
    return this.getById(id);
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { message: "Deleted" };
  }
}