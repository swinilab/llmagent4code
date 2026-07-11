// Product Domain Model

export class Product {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  createdAt: Date;
  updatedAt: Date;

  constructor(data: Partial<Product>) {
    this.id = data.id || '';
    this.name = data.name || '';
    this.description = data.description || '';
    this.price = data.price || 0;
    this.stock = data.stock || 0;
    this.category = data.category || '';
    this.createdAt = data.createdAt || new Date();
    this.updatedAt = data.updatedAt || new Date();
  }

  updateStock(quantity: number): void {
    this.stock = Math.max(0, this.stock - quantity);
    this.updatedAt = new Date();
  }

  addStock(quantity: number): void {
    this.stock += quantity;
    this.updatedAt = new Date();
  }

  updatePrice(price: number): void {
    this.price = Math.max(0, price);
    this.updatedAt = new Date();
  }

  isAvailable(quantity: number): boolean {
    return this.stock >= quantity;
  }

  toJSON(): ProductDTO {
    return {
      id: this.id,
      name: this.name,
      description: this.description,
      price: this.price,
      stock: this.stock,
      category: this.category,
      createdAt: this.createdAt,
      updatedAt: this.updatedAt
    };
  }
}

export interface ProductDTO {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  createdAt: Date;
  updatedAt: Date;
}
