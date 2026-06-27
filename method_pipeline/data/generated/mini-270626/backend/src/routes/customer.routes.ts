// Customer Routes Layer

import { Router } from 'express';
import { CustomerController } from '../controller/customer.controller';
import { CustomerService } from '../service/customer.service';

export function createCustomerRoutes(): Router {
  const router = Router();
  const customerService = new CustomerService();
  const controller = new CustomerController(customerService);

  router.post('/', (req, res) => controller.createCustomer(req, res));
  router.get('/', (req, res) => controller.getAllCustomers(req, res));
  router.get('/:id', (req, res) => controller.getCustomerById(req, res));
  router.put('/:id', (req, res) => controller.updateCustomer(req, res));
  router.delete('/:id', (req, res) => controller.deleteCustomer(req, res));

  return router;
}
