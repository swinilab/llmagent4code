// Product Controller Layer

import { Request, Response } from 'express';
import { ProductService } from '../service/product.service';

export class ProductController {
  private productService: ProductService;

  constructor(productService: ProductService) {
    this.productService = productService;
  }

  async createProduct(req: Request, res: Response): Promise<void> {
    try {
      const { name, description, price, stock, category } = req.body;

      if (!name || !price) {
        res.status(400).json({
          success: false,
          error: 'Missing required fields: name, price'
        });
        return;
      }

      const product = await this.productService.createProduct(
        name,
        description || '',
        price,
        stock || 0,
        category || 'General'
      );

      res.status(201).json({
        success: true,
        data: product.toJSON(),
        message: 'Product created successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to create product',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getProductById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const product = await this.productService.getProductById(id);

      if (!product) {
        res.status(404).json({
          success: false,
          error: 'Product not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: product.toJSON()
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get product',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getAllProducts(req: Request, res: Response): Promise<void> {
    try {
      const products = await this.productService.getAllProducts();

      res.status(200).json({
        success: true,
        data: products.map(p => p.toJSON()),
        total: products.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get products',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async updateProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updates = req.body;

      const product = await this.productService.updateProduct(id, updates);

      if (!product) {
        res.status(404).json({
          success: false,
          error: 'Product not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        data: product.toJSON(),
        message: 'Product updated successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to update product',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async deleteProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await this.productService.deleteProduct(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          error: 'Product not found'
        });
        return;
      }

      res.status(200).json({
        success: true,
        message: 'Product deleted successfully'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to delete product',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async searchProducts(req: Request, res: Response): Promise<void> {
    try {
      const { query } = req.query;

      if (!query) {
        res.status(400).json({
          success: false,
          error: 'Search query is required'
        });
        return;
      }

      const products = await this.productService.searchProducts(query as string);

      res.status(200).json({
        success: true,
        data: products.map(p => p.toJSON()),
        total: products.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to search products',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }

  async getProductsByCategory(req: Request, res: Response): Promise<void> {
    try {
      const { category } = req.params;
      const products = await this.productService.getProductsByCategory(category);

      res.status(200).json({
        success: true,
        data: products.map(p => p.toJSON()),
        total: products.length
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: 'Failed to get products by category',
        message: error instanceof Error ? error.message : 'Unknown error'
      });
    }
  }
}
