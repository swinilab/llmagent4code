import { Router } from 'express';
import { PaymentController } from '../controllers/PaymentController';

const router: Router = Router();
const paymentController = new PaymentController();

// GET routes
router.get('/', paymentController.getAllPayments.bind(paymentController));
router.get('/summary', paymentController.getPaymentSummary.bind(paymentController));
router.get('/date-range', paymentController.getPaymentsByDateRange.bind(paymentController));
router.get('/status/:status', paymentController.getPaymentsByStatus.bind(paymentController));
router.get('/customer/:customerId', paymentController.getPaymentsByCustomerId.bind(paymentController));
router.get('/invoice/:invoiceId', paymentController.getPaymentsByInvoiceId.bind(paymentController));
router.get('/:id', paymentController.getPaymentById.bind(paymentController));

// POST routes
router.post('/', paymentController.createPayment.bind(paymentController));

// PUT routes
router.put('/:id', paymentController.updatePayment.bind(paymentController));
router.put('/:id/process', paymentController.processPayment.bind(paymentController));
router.put('/:id/cancel', paymentController.cancelPayment.bind(paymentController));

// DELETE routes
router.delete('/:id', paymentController.deletePayment.bind(paymentController));

export default router;