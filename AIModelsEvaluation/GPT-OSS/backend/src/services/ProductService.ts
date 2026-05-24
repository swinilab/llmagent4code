import { AppDataSource } from "../db";
import { Product } from "../domain";

export class ProductService {
  private repo = AppDataSource.getRepository(Product);

  async getAll() {
    return this.repo.find();
  }

  async getById(id: string) {
    const prod = await this.repo.findOneBy({ id });
    if (!prod) throw new Error(`Product ${id} not found`);
    return prod;
  }

  async create(data: Partial<Product>) {
    const prod = this.repo.create(data);
    return this.repo.save(prod);
  }

  async update(id: string, data: Partial<Product>) {
    await this.repo.update(id, data);
    return this.getById(id);
  }

  async delete(id: string) {
    await this.repo.delete(id);
    return { message: "Deleted" };
  }
}