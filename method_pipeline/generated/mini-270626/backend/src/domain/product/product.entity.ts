// Product Entity Implementation

import { v4 as uuidv4 } from 'uuid';

export interface ProductData {
  id: string;
  name: string;
  description: string;
  price: number;
  stock: number;
  category: string;
  createdAt: Date;
  updatedAt: Date;
}

export class Product {
  public readonly id: string;
  public name: string;
  public description: string;
  public price: number;
  public stock: number;
  public category: string;
  public readonly createdAt: Date;
  public updatedAt: Date;

  constructor(data: Partial<ProductData>) {
    this.id = data.id || uuidv4();
    this.name = data.name || '';
    this.description = data.description || '';
    this.price = data.price || 0;
    this.stock = data.stock || 0;
    this.category = data.category || '';
    this.createdAt = data.createdAt || new Date();
    this.updatedAt = data.updatedAt || new Date();
  }

  updateStock(quantity: number): boolean {
    if (this.stock >= quantity) {
      this.stock -= quantity;
      this.updatedAt = new Date();
      return true;
    }
    return false;
  }

  addStock(quantity: number): void {
    this.stock += quantity;
    this.updatedAt = new Date();
  }

  updatePrice(price: number): void {
    this.price = Math.max(0, price);
    this.updatedAt = new Date();
  }

  updateInfo(name: string, description: string, category: string): void {
    this.name = name;
    this.description = description;
    this.category = category;
    this.updatedAt = new Date();
  }

  isAvailable(quantity: number): boolean {
    return this.stock >= quantity;
  }

  toJSON(): ProductData {
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

  static fromJSON(data: ProductData): Product {
    return new Product(data);
  }
}
