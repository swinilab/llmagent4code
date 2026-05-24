import express from 'express';
import { PrismaClient } from '@prisma/client';
import Customer from '../../../modules/customer/Customer';
import CustomerController from './CustomerController';

const router = express.Router();

// Initialize dummy customer and controller
const dummyCustomer = new Customer(
	1,
	'John Doe',
	'123 Main St',
	'0909999999',
	''
);
const controller = new CustomerController(dummyCustomer);

// ===== GET ROUTES =====

// Get all customers
router.get('/', async (req, res) => {
	try {
		const customerService = controller.customerService;
		const customers = await customerService.getCustomers();
		res.json(customers);
	} catch (err) {
		res.status(500).json({ error: 'Failed to get customers' });
	}
});

// Get customer by ID
router.get('/:id', async (req, res) => {
	try {
		const customerService = controller.customerService;
		const customer = await customerService.getCustomer(
			Number(req.params.id)
		);
		if (customer) {
			res.json(customer);
		} else {
			res.status(404).json({ error: 'Customer not found' });
		}
	} catch (err) {
		res.status(500).json({ error: 'Failed to get customer' });
	}
});

// Get all orders
router.get('/orders', async (req, res) => {
	try {
		const orders = await controller.getOrders();
		res.json(orders);
	} catch (err) {
		res.status(500).json({ error: 'Failed to fetch orders' });
	}
});

// ===== POST ROUTES =====

// Create new customer
router.post('/', async (req, res) => {
	try {
		const customerService = controller.customerService;
		const customer = await customerService.createCustomer(req.body);
		res.status(201).json(customer);
	} catch (err) {
		res.status(500).json({ error: 'Failed to create customer' });
	}
});

// Create new order
router.post('/orders', async (req, res) => {
	try {
		const { items, paymentMethod, customerId } = req.body;

		// Validate request data
		if (!items || !Array.isArray(items)) {
			return res.status(400).json({ error: 'Missing or invalid items' });
		}
		if (!['bank', 'card', 'cash'].includes(paymentMethod)) {
			return res
				.status(400)
				.json({ error: 'Invalid or missing payment method' });
		}

		// Use provided customer ID or default to dummy customer
		let orderController = controller;
		if (customerId) {
			try {
				// Create a customer instance for the provided ID
				const prisma = new PrismaClient();
				const customerRecord = await prisma.customer.findUnique({
					where: { id: parseInt(customerId) },
				});

				if (customerRecord) {
					const customerInstance = new Customer(
						customerRecord.id,
						customerRecord.name,
						customerRecord.address,
						customerRecord.phone,
						customerRecord.bankAccount || ''
					);
					orderController = new CustomerController(customerInstance);
				}
				await prisma.$disconnect();
			} catch (customerErr) {
				console.warn(
					'Could not find customer, using dummy customer:',
					customerErr
				);
			}
		}

		const result = await orderController.createOrder(items, paymentMethod);
		res.json(result);
	} catch (err) {
		console.error(err);
		res.status(500).json({ error: 'Failed to create order' });
	}
});

// ===== PUT ROUTES =====

// Update customer by ID
router.put('/:id', async (req, res) => {
	try {
		const customerService = controller.customerService;
		const customer = await customerService.updateCustomer(
			Number(req.params.id),
			req.body
		);
		if (customer) {
			res.json(customer);
		} else {
			res.status(404).json({ error: 'Customer not found' });
		}
	} catch (err) {
		res.status(500).json({ error: 'Failed to update customer' });
	}
});

// ===== DELETE ROUTES =====

// Delete customer by ID
router.delete('/:id', async (req, res) => {
	try {
		const customerService = controller.customerService;
		const deleted = await customerService.deleteCustomer(
			Number(req.params.id)
		);
		if (deleted) {
			res.status(204).end();
		} else {
			res.status(404).json({ error: 'Customer not found' });
		}
	} catch (err) {
		res.status(500).json({ error: 'Failed to delete customer' });
	}
});

// Delete order by ID
router.delete('/orders/:id', async (req, res) => {
	try {
		const orderId = parseInt(req.params.id);
		const result = await controller.deleteOrder(orderId);
		res.json(result);
	} catch (err) {
		res.status(500).json({ error: 'Failed to delete order' });
	}
});

export default router;
