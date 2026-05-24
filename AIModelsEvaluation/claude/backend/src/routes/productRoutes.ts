import { Router } from 'express';
import { ProductController } from '../controllers/ProductController';

const router: Router = Router();
const productController = new ProductController();

// GET routes
router.get('/', productController.getAllProducts.bind(productController));
router.get('/active', productController.getActiveProducts.bind(productController));
router.get('/search', productController.searchProducts.bind(productController));
router.get('/category/:category', productController.getProductsByCategory.bind(productController));
router.get('/sku/:sku', productController.getProductBySkuEndpoint.bind(productController));
router.get('/:id', productController.getProductById.bind(productController));

// POST routes
router.post('/', productController.createProduct.bind(productController));

// PUT routes
router.put('/:id', productController.updateProduct.bind(productController));
router.put('/:id/stock', productController.updateProductStock.bind(productController));

// DELETE routes
router.delete('/:id', productController.deleteProduct.bind(productController));

export default router;