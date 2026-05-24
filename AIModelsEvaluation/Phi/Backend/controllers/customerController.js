class CustomerController {
  constructor(customerService) {
    this.customerService = customerService;
  }

  async createCustomer(req, res) {
    try {
      const customer = await this.customerService.createCustomer(req.body);
      return res.status(201).json(customer);
    } catch (error) {
      return res.status(400).json({ error: error.message });
    }
  }

  async getAllCustomers(req, res) {
    try {
      const customers = await this.customerService.getAllCustomers();
      return res.json(customers);
    } catch (error) {
      return res.status(500).json({ error: error.message });
    }
  }
}