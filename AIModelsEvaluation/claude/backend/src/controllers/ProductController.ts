import { Request, Response } from 'express';
import { ProductService } from '../services/ProductService';
import Joi from 'joi';

const productService = new ProductService();

const productValidationSchema = Joi.object({
  name: Joi.string().required().min(2).max(200),
  description: Joi.string().required().min(10),
  category: Joi.string().required(),
  price: Joi.number().positive().required(),
  stockQuantity: Joi.number().integer().min(0).required(),
  sku: Joi.string().required().min(3).max(50),
  weight: Joi.number().positive().required(),
  dimensions: Joi.object({
    length: Joi.number().positive().required(),
    width: Joi.number().positive().required(),
    height: Joi.number().positive().required(),
  }).required(),
});

export class ProductController {
  async getAllProducts(req: Request, res: Response): Promise<void> {
    try {
      const products = await productService.getAllProducts();
      res.json({
        success: true,
        data: products,
        message: 'Products retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve products',
      });
    }
  }

  async getActiveProducts(req: Request, res: Response): Promise<void> {
    try {
      const products = await productService.getActiveProducts();
      res.json({
        success: true,
        data: products,
        message: 'Active products retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve active products',
      });
    }
  }

  async getProductById(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const product = await productService.getProductById(id);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve product',
      });
    }
  }

  async getProductBySkuEndpoint(req: Request, res: Response): Promise<void> {
    try {
      const { sku } = req.params;
      const product = await productService.getProductsBySku(sku);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve product',
      });
    }
  }

  async createProduct(req: Request, res: Response): Promise<void> {
    try {
      const { error, value } = productValidationSchema.validate(req.body);
      
      if (error) {
        res.status(400).json({
          success: false,
          error: error.details[0].message,
          message: 'Validation failed',
        });
        return;
      }

      const product = await productService.createProduct(value);
      res.status(201).json({
        success: true,
        data: product,
        message: 'Product created successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to create product',
      });
    }
  }

  async updateProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const updateData = { id, ...req.body };

      const product = await productService.updateProduct(updateData);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update product',
      });
    }
  }

  async deleteProduct(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const deleted = await productService.deleteProduct(id);

      if (!deleted) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        message: 'Product deleted successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to delete product',
      });
    }
  }

  async updateProductStock(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const { quantity } = req.body;

      if (typeof quantity !== 'number') {
        res.status(400).json({
          success: false,
          message: 'Quantity must be a number',
        });
        return;
      }

      const product = await productService.updateProductStock(id, quantity);

      if (!product) {
        res.status(404).json({
          success: false,
          message: 'Product not found',
        });
        return;
      }

      res.json({
        success: true,
        data: product,
        message: 'Product stock updated successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to update product stock',
      });
    }
  }

  async searchProducts(req: Request, res: Response): Promise<void> {
    try {
      const { q } = req.query;

      if (!q || typeof q !== 'string') {
        res.status(400).json({
          success: false,
          message: 'Search query parameter "q" is required',
        });
        return;
      }

      const products = await productService.searchProducts(q);
      res.json({
        success: true,
        data: products,
        message: 'Product search completed successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to search products',
      });
    }
  }

  async getProductsByCategory(req: Request, res: Response): Promise<void> {
    try {
      const { category } = req.params;
      const products = await productService.getProductsByCategory(category);
      res.json({
        success: true,
        data: products,
        message: 'Products by category retrieved successfully',
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: (error as Error).message,
        message: 'Failed to retrieve products by category',
      });
    }
  }
}