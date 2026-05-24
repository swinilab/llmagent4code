import { Router } from 'express';
import { CustomerController } from '../controllers/CustomerController';

const router: Router = Router();
const customerController = new CustomerController();

// GET routes
router.get('/', customerController.getAllCustomers.bind(customerController));
router.get('/search', customerController.searchCustomers.bind(customerController));
router.get('/role/:role', customerController.getCustomersByRole.bind(customerController));
router.get('/:id', customerController.getCustomerById.bind(customerController));

// POST routes
router.post('/', customerController.createCustomer.bind(customerController));

// PUT routes
router.put('/:id', customerController.updateCustomer.bind(customerController));

// DELETE routes
router.delete('/:id', customerController.deleteCustomer.bind(customerController));

export default router;