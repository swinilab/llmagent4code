import Product from '../models/Product';
import { Product as IProduct, CreateProductRequest, UpdateProductRequest } from '../../../shared/domain/Product';

export class ProductService {
  async getAllProducts(): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        order: [['createdAt', 'DESC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch products: ${error}`);
    }
  }

  async getActiveProducts(): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: { isActive: true },
        order: [['name', 'ASC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch active products: ${error}`);
    }
  }

  async getProductById(id: string): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(id);
      return product ? (product.toJSON() as IProduct) : null;
    } catch (error) {
      throw new Error(`Failed to fetch product: ${error}`);
    }
  }

  async getProductsBySku(sku: string): Promise<IProduct | null> {
    try {
      const product = await Product.findOne({
        where: { sku },
      });
      return product ? (product.toJSON() as IProduct) : null;
    } catch (error) {
      throw new Error(`Failed to fetch product by SKU: ${error}`);
    }
  }

  async createProduct(productData: CreateProductRequest): Promise<IProduct> {
    try {
      const product = await Product.create(productData as any);
      return product.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to create product: ${error}`);
    }
  }

  async updateProduct(updateData: UpdateProductRequest): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(updateData.id);
      if (!product) {
        return null;
      }

      const updatedProduct = await product.update(updateData);
      return updatedProduct.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to update product: ${error}`);
    }
  }

  async deleteProduct(id: string): Promise<boolean> {
    try {
      const result = await Product.destroy({
        where: { id },
      });
      return result > 0;
    } catch (error) {
      throw new Error(`Failed to delete product: ${error}`);
    }
  }

  async updateProductStock(id: string, quantity: number): Promise<IProduct | null> {
    try {
      const product = await Product.findByPk(id);
      if (!product) {
        return null;
      }

      const updatedProduct = await product.update({
        stockQuantity: product.stockQuantity + quantity,
      });
      return updatedProduct.toJSON() as IProduct;
    } catch (error) {
      throw new Error(`Failed to update product stock: ${error}`);
    }
  }

  async searchProducts(searchTerm: string): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: {
          [require('sequelize').Op.or]: [
            { name: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { description: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { category: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
            { sku: { [require('sequelize').Op.like]: `%${searchTerm}%` } },
          ],
        },
        order: [['createdAt', 'DESC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to search products: ${error}`);
    }
  }

  async getProductsByCategory(category: string): Promise<IProduct[]> {
    try {
      const products = await Product.findAll({
        where: { category },
        order: [['name', 'ASC']],
      });
      return products.map(product => product.toJSON() as IProduct);
    } catch (error) {
      throw new Error(`Failed to fetch products by category: ${error}`);
    }
  }
}