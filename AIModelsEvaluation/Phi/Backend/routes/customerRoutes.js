const express = require('express');
const router = express.Router();
const customerService = new CustomerService(require('../Backend/models').Customer);
const customerController = new CustomerController(customerService);

router.post('/', customerController.createCustomer.bind(customerController));
router.get('/', customerController.getAllCustomers.bind(customerController));

module.exports = router;