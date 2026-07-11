// Product Service Layer

import { Product, ProductData } from '../domain/product/product.entity';
import { MemoryRepository } from '../repository/memory-repository';

export class ProductService {
  private repository: MemoryRepository<ProductData>;

  constructor() {
    this.repository = new MemoryRepository<ProductData>();
    this.initializeDefaultProducts();
  }

  private async initializeDefaultProducts(): Promise<void> {
    const defaultProducts: ProductData[] = [
      {
        id: 'prod-001',
        name: 'Wireless Mouse',
        description: 'Ergonomic wireless mouse with USB receiver',
        price: 29.99,
        stock: 100,
        category: 'Electronics',
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'prod-002',
        name: 'Mechanical Keyboard',
        description: 'RGB mechanical keyboard with Cherry MX switches',
        price: 89.99,
        stock: 50,
        category: 'Electronics',
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'prod-003',
        name: 'USB-C Hub',
        description: '7-in-1 USB-C hub with HDMI and card reader',
        price: 49.99,
        stock: 75,
        category: 'Electronics',
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'prod-004',
        name: 'Monitor Stand',
        description: 'Adjustable aluminum monitor stand',
        price: 39.99,
        stock: 60,
        category: 'Accessories',
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 'prod-005',
        name: 'Webcam HD',
        description: '1080p HD webcam with built-in microphone',
        price: 59.99,
        stock: 40,
        category: 'Electronics',
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    for (const product of defaultProducts) {
      await this.repository.create(product);
    }
  }

  async createProduct(name: string, description: string, price: number, stock: number, category: string): Promise<Product> {
    const product = new Product({ name, description, price, stock, category });
    const saved = await this.repository.create(product.toJSON());
    return new Product(saved);
  }

  async getProductById(id: string): Promise<Product | null> {
    const data = await this.repository.findById(id);
    return data ? new Product(data) : null;
  }

  async getAllProducts(): Promise<Product[]> {
    const data = await this.repository.findAll();
    return data.map(d => new Product(d));
  }

  async updateProduct(id: string, updates: Partial<{ name: string; description: string; price: number; stock: number; category: string }>): Promise<Product | null> {
    const existing = await this.repository.findById(id);
    if (!existing) return null;

    const product = new Product(existing);
    if (updates.name !== undefined) product.name = updates.name;
    if (updates.description !== undefined) product.description = updates.description;
    if (updates.price !== undefined) product.updatePrice(updates.price);
    if (updates.stock !== undefined) product.stock = updates.stock;
    if (updates.category !== undefined) product.category = updates.category;

    const updated = await this.repository.update(id, product.toJSON());
    return updated ? new Product(updated) : null;
  }

  async deleteProduct(id: string): Promise<boolean> {
    return this.repository.delete(id);
  }

  async updateStock(productId: string, quantity: number): Promise<Product | null> {
    const existing = await this.repository.findById(productId);
    if (!existing) return null;

    const product = new Product(existing);
    product.updateStock(quantity);
    const updated = await this.repository.update(productId, product.toJSON());
    return updated ? new Product(updated) : null;
  }

  async addStock(productId: string, quantity: number): Promise<Product | null> {
    const existing = await this.repository.findById(productId);
    if (!existing) return null;

    const product = new Product(existing);
    product.addStock(quantity);
    const updated = await this.repository.update(productId, product.toJSON());
    return updated ? new Product(updated) : null;
  }

  async getProductsByCategory(category: string): Promise<Product[]> {
    const products = await this.repository.findAll();
    return products.filter(p => p.category === category).map(d => new Product(d));
  }

  async searchProducts(query: string): Promise<Product[]> {
    const products = await this.repository.findAll();
    const lowerQuery = query.toLowerCase();
    return products.filter(p => 
      p.name.toLowerCase().includes(lowerQuery) || 
      p.description.toLowerCase().includes(lowerQuery)
    ).map(d => new Product(d));
  }
}
