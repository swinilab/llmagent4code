// Product Routes Layer

import { Router } from 'express';
import { ProductController } from '../controller/product.controller';
import { ProductService } from '../service/product.service';

export function createProductRoutes(): Router {
  const router = Router();
  const productService = new ProductService();
  const controller = new ProductController(productService);

  router.post('/', (req, res) => controller.createProduct(req, res));
  router.get('/', (req, res) => controller.getAllProducts(req, res));
  router.get('/:id', (req, res) => controller.getProductById(req, res));
  router.get('/search', (req, res) => controller.searchProducts(req, res));
  router.get('/category/:category', (req, res) => controller.getProductsByCategory(req, res));
  router.put('/:id', (req, res) => controller.updateProduct(req, res));
  router.delete('/:id', (req, res) => controller.deleteProduct(req, res));

  return router;
}
