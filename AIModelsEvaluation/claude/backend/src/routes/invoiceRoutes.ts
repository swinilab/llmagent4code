import { Router } from 'express';
import { InvoiceController } from '../controllers/InvoiceController';

const router: Router = Router();
const invoiceController = new InvoiceController();

// GET routes
router.get('/', invoiceController.getAllInvoices.bind(invoiceController));
router.get('/overdue', invoiceController.getOverdueInvoices.bind(invoiceController));
router.get('/status/:status', invoiceController.getInvoicesByStatus.bind(invoiceController));
router.get('/customer/:customerId', invoiceController.getInvoicesByCustomerId.bind(invoiceController));
router.get('/order/:orderId', invoiceController.getInvoiceByOrderId.bind(invoiceController));
router.get('/:id', invoiceController.getInvoiceById.bind(invoiceController));

// POST routes
router.post('/', invoiceController.createInvoice.bind(invoiceController));

// PUT routes
router.put('/:id', invoiceController.updateInvoice.bind(invoiceController));
router.put('/:id/pay', invoiceController.markInvoiceAsPaid.bind(invoiceController));
router.put('/:id/send', invoiceController.sendInvoice.bind(invoiceController));
router.put('/:id/cancel', invoiceController.cancelInvoice.bind(invoiceController));

// DELETE routes
router.delete('/:id', invoiceController.deleteInvoice.bind(invoiceController));

export default router;