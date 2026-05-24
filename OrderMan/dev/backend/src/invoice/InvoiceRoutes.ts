import express from 'express';
import InvoiceController from './InvoiceController';

const router = express.Router();
const controller = new InvoiceController();

// ===== GET ROUTES =====

// Get all invoices
router.get('/', async (req, res) => {
	try {
		const invoices = await controller.getAllInvoices();
		res.json(invoices);
	} catch (err) {
		res.status(500).json({ error: 'Failed to get invoices' });
	}
});

// Get invoice by ID
router.get('/:id', async (req, res) => {
	const id = parseInt(req.params.id);
	const invoice = await controller.getInvoice(id);
	invoice
		? res.json(invoice)
		: res.status(404).json({ error: 'Invoice not found' });
});

// Get invoices by order ID
router.get('/order/:orderId', async (req, res) => {
	const orderId = parseInt(req.params.orderId);
	const invoices = await controller.getInvoicesByOrder(orderId);
	res.json(invoices);
});

// ===== POST ROUTES =====

// Create new invoice
router.post('/', async (req, res) => {
	try {
		const invoice = await controller.createInvoice(req.body);
		res.status(201).json(invoice);
	} catch (err) {
		res.status(500).json({ error: 'Failed to create invoice' });
	}
});

// Send invoice for order
router.post('/send/:orderId', async (req, res) => {
	try {
		const orderId = parseInt(req.params.orderId);
		const invoice = await controller.sendInvoice(orderId);
		res.status(201).json(invoice);
	} catch (err) {
		res.status(500).json({ error: 'Failed to send invoice' });
	}
});

// ===== PUT ROUTES =====

// Update invoice by ID
router.put('/:id', async (req, res) => {
	const id = parseInt(req.params.id);
	const updated = await controller.updateInvoice(id, req.body);
	updated
		? res.json(updated)
		: res.status(404).json({ error: 'Invoice not found' });
});

// ===== DELETE ROUTES =====

// Delete invoice by ID
router.delete('/:id', async (req, res) => {
	const id = parseInt(req.params.id);
	const deleted = await controller.deleteInvoice(id);
	deleted
		? res.json({ success: true })
		: res.status(404).json({ error: 'Invoice not found' });
});

export default router;
