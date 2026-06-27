// Order Routes Layer

import { Router } from 'express';
import { OrderController } from '../controller/order.controller';
import { OrderService } from '../service/order.service';
import { CustomerService } from '../service/customer.service';
import { ProductService } from '../service/product.service';

export function createOrderRoutes(): Router {
  const router = Router();
  const customerService = new CustomerService();
  const productService = new ProductService();
  const orderService = new OrderService(customerService, productService);
  const controller = new OrderController(orderService);

  router.post('/', (req, res) => controller.createOrder(req, res));
  router.get('/', (req, res) => controller.getAllOrders(req, res));
  router.get('/:id', (req, res) => controller.getOrderById(req, res));
  router.get('/customer/:customerId', (req, res) => controller.getOrdersByCustomer(req, res));
  router.put('/:id/status', (req, res) => controller.updateOrderStatus(req, res));
  router.post('/:id/confirm', (req, res) => controller.confirmOrder(req, res));
  router.post('/:id/cancel', (req, res) => controller.cancelOrder(req, res));
  router.delete('/:id', (req, res) => controller.deleteOrder(req, res));

  return router;
}
