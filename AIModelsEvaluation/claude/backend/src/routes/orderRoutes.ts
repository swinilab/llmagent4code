import { Router } from 'express';
import { OrderController } from '../controllers/OrderController';

const router: Router = Router();
const orderController = new OrderController();

// GET routes
router.get('/', orderController.getAllOrders.bind(orderController));
router.get('/status/:status', orderController.getOrdersByStatus.bind(orderController));
router.get('/customer/:customerId', orderController.getOrdersByCustomerId.bind(orderController));
router.get('/:id', orderController.getOrderById.bind(orderController));

// POST routes
router.post('/', orderController.createOrder.bind(orderController));

// PUT routes
router.put('/:id', orderController.updateOrder.bind(orderController));
router.put('/:id/accept', orderController.acceptOrder.bind(orderController));
router.put('/:id/ship', orderController.shipOrder.bind(orderController));
router.put('/:id/complete', orderController.completeOrder.bind(orderController));
router.put('/:id/cancel', orderController.cancelOrder.bind(orderController));

// DELETE routes
router.delete('/:id', orderController.deleteOrder.bind(orderController));

export default router;