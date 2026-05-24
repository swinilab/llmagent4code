import express from 'express';
import ProductController from './ProductController';

const router = express.Router();
const controller = new ProductController();

// ===== GET ROUTES =====

// Get all products
router.get('/', async (req, res) => {
	try {
		const products = await controller.fetchProducts();
		res.json(products);
	} catch (err) {
		res.status(500).json({ error: 'Failed to fetch products' });
	}
});

// Get product by ID
router.get('/:id', async (req, res) => {
	try {
		const product = await controller.fetchProductDetails(
			Number(req.params.id)
		);
		if (!product) return res.status(404).json({ error: 'Not found' });
		res.json(product);
	} catch (err) {
		res.status(500).json({ error: 'Failed to fetch product' });
	}
});

// ===== POST ROUTES =====

// Create new product
router.post('/', async (req, res) => {
	try {
		const product = await controller.createProduct(req.body);
		res.status(201).json(product);
	} catch (err) {
		res.status(500).json({ error: 'Failed to create product' });
	}
});

// ===== PUT ROUTES =====

// Update product by ID
router.put('/:id', async (req, res) => {
	try {
		const updated = await controller.updateProduct(
			Number(req.params.id),
			req.body
		);
		if (!updated)
			return res.status(404).json({ error: 'Product not found' });
		res.json(updated);
	} catch (err) {
		res.status(500).json({ error: 'Failed to update product' });
	}
});

// ===== DELETE ROUTES =====

// Delete product by ID
router.delete('/:id', async (req, res) => {
	try {
		const deleted = await controller.deleteProduct(Number(req.params.id));
		if (deleted) {
			res.status(204).end();
		} else {
			res.status(404).json({ error: 'Product not found' });
		}
	} catch (err) {
		res.status(500).json({ error: 'Failed to delete product' });
	}
});

export default router;
