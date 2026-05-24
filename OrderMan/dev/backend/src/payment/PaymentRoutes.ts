import express from 'express';
import PaymentController from './PaymentController';

const router = express.Router();
const controller = new PaymentController();

// ===== GET ROUTES =====

// Get all payments
router.get('/', async (req, res) => {
	try {
		const payments = await controller.getAllPayments();
		res.json(payments);
	} catch (err) {
		res.status(500).json({ error: 'Failed to get payments' });
	}
});

// Get payment by ID
router.get('/:id', async (req, res) => {
	const payment = await controller.getPayment(Number(req.params.id));
	if (payment) res.json(payment);
	else res.status(404).json({ error: 'Payment not found' });
});

// Get payments by invoice ID
router.get('/invoices/:invoiceId', async (req, res) => {
	const payments = await controller.getPaymentsByInvoices(
		Number(req.params.invoiceId)
	);
	res.json(payments);
});

// ===== POST ROUTES =====

// Create new payment
router.post('/', async (req, res) => {
	try {
		const payment = await controller.makePayment(req.body);
		res.status(201).json(payment);
	} catch (err) {
		console.error('Payment creation error:', err);
		res.status(500).json({ error: 'Failed to create payment' });
	}
});

// Accept payment by ID
router.post('/accept/:id', async (req, res) => {
	try {
		const paymentId = Number(req.params.id);
		const result = await controller.acceptPayment(paymentId);
		res.json(result);
	} catch (err) {
		res.status(500).json({ error: 'Failed to accept payment' });
	}
});

// ===== PUT ROUTES =====

// Update payment by ID
router.put('/:id', async (req, res) => {
	const payment = await controller.updatePayment(
		Number(req.params.id),
		req.body
	);
	if (payment) res.json(payment);
	else res.status(404).json({ error: 'Payment not found' });
});

// ===== DELETE ROUTES =====

// Delete payment by ID
router.delete('/:id', async (req, res) => {
	const deleted = await controller.deletePayment(Number(req.params.id));
	if (deleted) res.status(204).end();
	else res.status(404).json({ error: 'Payment not found' });
});

export default router;
