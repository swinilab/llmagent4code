// Backend server

import express, { Request, Response } from 'express';
import { CustomerService } from './services/customer.service';
import { OrderService } from './services/order.service';
import { ProductService } from './services/product.service';
import { PaymentService } from './services/payment.service';
import { InvoiceService } from './services/invoice.service';

const app = express();

// Initialize services
const customerService = new CustomerService();
const orderService = new OrderService();
const productService = new ProductService();
const paymentService = new PaymentService();
const invoiceService = new InvoiceService();

// Define API endpoints
app.get('/customers', customerService.getCustomers);
app.get('/orders', orderService.getOrders);
app.get('/products', productService.getProducts);
app.get('/payments', paymentService.getPayments);
app.get('/invoices', invoiceService.getInvoices);

// Start server
const port = 3000;
app.listen(port, () => {
  console.log(`Server started on port ${port}`);
});